"""
Orchestrates the end-to-end email-to-PDF pipeline.
Uses PDFSession context manager to guarantee browser lifecycle.
Includes SQLite cache integration and optimized body-scan avoidance.

Provides AsyncPipelineOrchestrator for async producer-consumer pipeline
that interleaves Outlook COM fetching with async Playwright PDF rendering.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from src.config_manager import ConfigManager
from src.outlook_session_manager import OutlookSessionManager
from src.email_searcher import EmailSearcher, ExtractedEmail
from src.processed_directors_store import ProcessedDirectorsStore
from src.email_formatter import EmailFormatter
from src.file_manager import FileManager
from src.license_validator import LicenseValidator
from src.progress_manager import ProgressManager
from src.pdf_generator import PDFGenerator, PDFSession, AsyncPDFGenerator
from src.cli import CLI, ExecutionContext, ExecutionMode, SMSFEntry
from src.exceptions import LicenseInputUnavailableError, OutlookUnavailableError
from src.dependencies import Dependencies, CompositionRoot
from src.performance import get_tracker
from src.smsf_context import SMSFContext as NewSMSFContext
from src.advisor_domain_matcher import AdvisorDomainMatcher
from src.search_rule_engine import SearchRuleEngine, RelevanceLevel
from src.deduplication import CrossMailboxDeduplicator
from src.advisor_pdf_grouping import AdvisorPDFGroupingEngine
from src.cache_manager import EmailMetadataCache
from src.folder_strategies import FastFolderStrategy

logger = logging.getLogger(__name__)

LICENSE_SERVER_URL = "https://email-to-pdf-license.email-to-pdf-license.workers.dev/validate"


def _get_default_output_base() -> Path:
    default_docs = Path(os.environ.get("USERPROFILE", ".")) / "Documents"
    return default_docs / "EmailPDFs"


@dataclass(frozen=True)
class SMSFSpec:
    smsf: str
    search_terms: list
    start_date: any
    end_date: any
    mode: str
    skip_if_processed: bool = True


@dataclass
class PDFJob:
    """A single PDF rendering unit pushed through the async pipeline."""
    group_name: str
    emails: List[ExtractedEmail]
    smsf_name: str


class MainOrchestrator:
    def __init__(
        self,
        context: Optional[ExecutionContext] = None,
        output_base: Optional[Path] = None,
        deps: Optional[Dependencies] = None,
    ) -> None:
        self._context = context or CLI.resolve([])
        self._output_base = output_base or _get_default_output_base()
        if isinstance(self._output_base, Path):
            self._output_base = self._output_base.expanduser().resolve()
        self._deps = deps or CompositionRoot(self._output_base).build()
        self._cli = CLI()

        self._config: ConfigManager = self._deps.config_manager
        self._progress: ProgressManager = self._deps.progress_manager
        self._email_formatter: EmailFormatter = self._deps.email_formatter
        self._pdf: Optional[PDFGenerator] = None
        self._file_mgr: FileManager = self._deps.file_manager
        self._license: LicenseValidator = self._deps.license_validator
        self._store: ProcessedDirectorsStore = self._deps.processed_store

        self._session: Optional[OutlookSessionManager] = None
        self._searcher: Optional[EmailSearcher] = None
        self._connected = False
        self._advisor_matcher: Optional[AdvisorDomainMatcher] = None
        self._search_engine: Optional[SearchRuleEngine] = None
        self._deduplicator: Optional[CrossMailboxDeduplicator] = None
        self._pdf_grouper: Optional[AdvisorPDFGroupingEngine] = None
        self._cache: Optional[EmailMetadataCache] = None

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def run(self) -> int:
        logger.info("Starting email-to-pdf orchestrator")
        license_key = self._license.prompt_and_validate()
        if not license_key:
            self._progress.error("SYSTEM", "License validation failed")
            logger.error("License validation failed")
            return 1

        self._print_banner()

        try:
            with PDFSession(self._deps.pdf_generator) as pdf:
                self._pdf = pdf
                if self._context.mode == ExecutionMode.BATCH:
                    result = self._run_batch()
                    logger.info("Batch processing completed with %d failures", result)
                    return result
                result = self._run_interactive()
                logger.info("Interactive session completed with %d failures", result)
                return result
        except RuntimeError as exc:
            logger.error("PDF engine failed: %s", exc)
            self._progress.error("SYSTEM", f"PDF engine failed: {exc}")
            return 1
        finally:
            self._cleanup()

    # ------------------------------------------------------------------
    # Mode runners
    # ------------------------------------------------------------------
    def _run_batch(self) -> int:
        smsf_entries = self._context.smsf_entries
        if not smsf_entries:
            self._progress.print_warn("No SMSF entries configured for batch mode.")
            return 0

        if not self._connect_to_outlook():
            self._progress.error("B", "Could not connect to Outlook. Ensure Outlook is open.")
            return 1

        failed = 0
        for entry in smsf_entries:
            ctx = SMSFSpec(
                smsf=entry.smsf,
                search_terms=entry.search_terms,
                start_date=entry.start_date,
                end_date=entry.end_date,
                mode="batch",
                skip_if_processed=True,
            )
            failed += self._process_smsf(ctx)

        return failed

    def _run_interactive(self) -> int:
        if not self._connect_to_outlook():
            self._progress.error("B", "Could not connect to Outlook. Ensure Outlook is open.")
            return 1

        failed = 0

        while True:
            try:
                user_input = self._cli.get_smsf_input()
            except ValueError as e:
                self._progress.print_warn(str(e))
                continue

            ctx = SMSFSpec(
                smsf=user_input["smsf"],
                search_terms=user_input["search_terms"],
                start_date=user_input["start_date"],
                end_date=user_input["end_date"],
                mode="interactive",
                skip_if_processed=False,
            )
            failed += self._process_smsf(ctx)

            if not self._cli.prompt_continue():
                break

        return failed

    # ------------------------------------------------------------------
    # Unified pipeline
    # ------------------------------------------------------------------
    def _process_smsf(self, ctx: SMSFSpec) -> int:
        tracker = get_tracker()
        try:
            if ctx.skip_if_processed and self._store.is_processed(ctx.smsf):
                self._progress.skip(ctx.smsf, "Already processed")
                return 0

            folder_count = 0
            if self._session and self._session.is_connected():
                with tracker.track("folder_scan"):
                    try:
                        strategy = FastFolderStrategy()
                        for _ in self._searcher._iter_folders(strategy):
                            folder_count += 1
                    except Exception:
                        pass

            self._progress.start(ctx.smsf, folder_count=folder_count)

            all_terms = [ctx.smsf] + ctx.search_terms

            def on_event(event):
                self._progress.display_search_event(event)

            with tracker.track("email_search"):
                emails = self._searcher.search(
                    all_terms,
                    ctx.start_date,
                    ctx.end_date,
                    on_event=on_event,
                )

            from src.email_searcher import SearchEvent
            self._progress.display_search_event(
                SearchEvent(type="complete", total=len(emails))
            )

            self._progress.stop()

            if not emails:
                self._progress.warning(ctx.smsf, "No emails matched criteria")
                self._store.mark_processed(ctx.smsf)
                return 0

            # ------------------------------------------------------------------
            # OPTIMIZED: Determine if body was already scanned by email_searcher
            # This avoids double body extraction in search_rule_engine
            # ------------------------------------------------------------------
            had_body_scan = any(len(t) >= 5 for t in all_terms)

            if self._search_engine and self._advisor_matcher:
                director_emails = [t for t in ctx.search_terms if "@" in t]
                director_names = [t for t in ctx.search_terms if "@" not in t]
                new_smsf_ctx = NewSMSFContext(
                    smsf_name=ctx.smsf,
                    director_names=director_names,
                    director_emails=director_emails,
                    advisor_domains=list(self._advisor_matcher._domain_to_org.keys()),
                )

                # Pass body_already_scanned flag to avoid double body fetch
                relevant_emails = [
                    e for e in emails
                    if self._search_engine.is_relevant(
                        e, new_smsf_ctx, body_already_scanned=had_body_scan
                    ) != RelevanceLevel.NONE
                ]
                emails = relevant_emails

            if not emails:
                self._progress.warning(ctx.smsf, "No relevant advisor emails found")
                self._store.mark_processed(ctx.smsf)
                return 0

            with tracker.track("deduplication"):
                if self._deduplicator:
                    emails = self._deduplicator.deduplicate(emails)

            if self._pdf_grouper and self._advisor_matcher and self._search_engine:
                director_emails = [t for t in ctx.search_terms if "@" in t]
                director_names = [t for t in ctx.search_terms if "@" not in t]
                new_smsf_ctx = NewSMSFContext(
                    smsf_name=ctx.smsf,
                    director_names=director_names,
                    director_emails=director_emails,
                    advisor_domains=list(self._advisor_matcher._domain_to_org.keys()),
                )
                groups = self._pdf_grouper.group_emails(
                    emails, new_smsf_ctx, self._advisor_matcher
                )

                if groups:
                    for group_name, group_emails in groups.items():
                        with tracker.track("email_formatting"):
                            html = self._email_formatter.format_multiple_emails(
                                group_emails
                            )

                        with tracker.track("pdf_generation"):
                            filename = f"{group_name}.pdf"
                            path = self._file_mgr.save_pdf(
                                html, filename.replace(".pdf", "")
                            )

                        if path:
                            self._progress.complete(group_name, str(path))
                    self._store.mark_processed(ctx.smsf)
                    return 0

            with tracker.track("email_formatting"):
                html = self._email_formatter.format_multiple_emails(emails)

            with tracker.track("pdf_generation"):
                path = self._file_mgr.save_pdf(html, ctx.smsf)

            if not path:
                self._progress.error(
                    ctx.smsf, "PDF generation failed - SMSF not marked processed"
                )
                return 1

            self._store.mark_processed(ctx.smsf)
            self._progress.complete(ctx.smsf, str(path))
            return 0

        except OutlookUnavailableError:
            self._session.disconnect()
            raise
        except Exception as exc:
            logger.exception("SMSF processing failed: %s", ctx.smsf)
            self._progress.error(ctx.smsf, str(exc))
            return 1
    def _connect_to_outlook(self) -> bool:
        self._session = self._deps.session_manager
        success = self._session.connect()

        if success and self._session.is_connected():
            # Initialize cache
            self._cache = self._deps.cache

            if self._cache:
                self._progress.print_info("SQLite cache initialized")
            else:
                self._progress.print_warn("Cache unavailable - running live Outlook mode")

            if self._deps.email_searcher:
                self._searcher = self._deps.email_searcher
            else:
                self._searcher = EmailSearcher(
                    session_manager=self._session,
                    processed_store=self._deps.processed_store,
                    config_manager=self._config,
                    cache=self._cache,
                )
            (self._advisor_matcher,
             self._search_engine,
             self._deduplicator,
             self._pdf_grouper) = CompositionRoot.build_pipeline_components()
            self._connected = True
            self._progress.print_info("Connected to Outlook successfully.")
            return True

        return False

    def _cleanup(self) -> None:
        if self._cache:
            try:
                self._cache.close()
            except Exception as exc:
                logger.debug("Cache close warning: %s", exc)
        if self._connected and self._session:
            self._session.disconnect()
            self._progress.print_info("Outlook connection closed.")

    def _print_banner(self) -> None:
        self._progress._console.print("\n" + "=" * 60)
        self._progress._console.print("[bold cyan]EMAIL TO PDF AUTOMATION TOOL[/bold cyan]")
        self._progress._console.print("=" * 60 + "\n")


class AsyncPipelineOrchestrator:
    """
    Async producer-consumer pipeline that interleaves Outlook COM fetching
    (producer, sync) with async Playwright PDF rendering (consumer).

    Because win32com must stay on the main thread but Playwright is naturally
    async, we wrap the pipeline in an asyncio event loop. The producer yields
    when pushing to the queue, allowing the consumer to render PDFs concurrently.

    Queue maxsize=50 provides backpressure — prevents memory ballooning
    when the consumer is slower than the producer.
    """

    def __init__(
        self,
        deps: Dependencies,
        output_base: Path,
    ) -> None:
        self._deps = deps
        self._output_base = output_base
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=50)
        self._failed_count = 0
        self._progress = deps.progress_manager

        self._searcher: Optional[EmailSearcher] = None
        self._session: Optional[OutlookSessionManager] = None
        self._advisor_matcher: Optional[AdvisorDomainMatcher] = None
        self._search_engine: Optional[SearchRuleEngine] = None
        self._deduplicator: Optional[CrossMailboxDeduplicator] = None
        self._pdf_grouper: Optional[AdvisorPDFGroupingEngine] = None
        self._store: Optional[ProcessedDirectorsStore] = None

    # ------------------------------------------------------------------
    # Entry point (call via asyncio.run)
    # ------------------------------------------------------------------
    async def run(self, smsf_ctxs: List[SMSFSpec]) -> int:
        if not smsf_ctxs:
            return 0

        pdf_gen = AsyncPDFGenerator()
        if not await pdf_gen.start():
            self._progress.error("SYSTEM", "Failed to start async PDF engine")
            return 1

        try:
            await asyncio.gather(
                self._producer(smsf_ctxs),
                self._consumer(pdf_gen),
            )
            return self._failed_count
        except OutlookUnavailableError:
            raise
        except Exception as exc:
            logger.exception("Async pipeline failed: %s", exc)
            return 1
        finally:
            await pdf_gen.stop()

    # ------------------------------------------------------------------
    # Producer: sync COM on main thread, yields at queue.put
    # ------------------------------------------------------------------
    async def _producer(self, smsf_ctxs: List[SMSFSpec]) -> None:
        for ctx in smsf_ctxs:
            try:
                if ctx.skip_if_processed and self._store and self._store.is_processed(ctx.smsf):
                    self._progress.skip(ctx.smsf, "Already processed")
                    continue

                all_terms = [ctx.smsf] + ctx.search_terms
                had_body_scan = any(len(t) >= 5 for t in all_terms)

                self._progress.start(ctx.smsf)
                emails = self._searcher.search(
                    all_terms, ctx.start_date, ctx.end_date,
                    on_event=lambda e: self._progress.display_search_event(e),
                )
                self._progress.stop()

                if not emails:
                    self._progress.warning(ctx.smsf, "No emails matched criteria")
                    if self._store:
                        self._store.mark_processed(ctx.smsf)
                    continue

                # Score relevance
                if self._search_engine and self._advisor_matcher:
                    director_emails = [t for t in ctx.search_terms if "@" in t]
                    director_names = [t for t in ctx.search_terms if "@" not in t]
                    new_ctx = NewSMSFContext(
                        smsf_name=ctx.smsf,
                        director_names=director_names,
                        director_emails=director_emails,
                        advisor_domains=list(self._advisor_matcher._domain_to_org.keys()),
                    )
                    emails = [
                        e for e in emails
                        if self._search_engine.is_relevant(
                            e, new_ctx, body_already_scanned=had_body_scan
                        ) != RelevanceLevel.NONE
                    ]

                if not emails:
                    self._progress.warning(ctx.smsf, "No relevant advisor emails found")
                    if self._store:
                        self._store.mark_processed(ctx.smsf)
                    continue

                # Deduplicate
                if self._deduplicator:
                    emails = self._deduplicator.deduplicate(emails)

                # Group by advisor
                groups = None
                if self._pdf_grouper and self._advisor_matcher and self._search_engine:
                    director_emails = [t for t in ctx.search_terms if "@" in t]
                    director_names = [t for t in ctx.search_terms if "@" not in t]
                    new_ctx = NewSMSFContext(
                        smsf_name=ctx.smsf,
                        director_names=director_names,
                        director_emails=director_emails,
                        advisor_domains=list(self._advisor_matcher._domain_to_org.keys()),
                    )
                    groups = self._pdf_grouper.group_emails(
                        emails, new_ctx, self._advisor_matcher
                    )

                if groups:
                    for group_name, group_emails in groups.items():
                        await self._queue.put(PDFJob(
                            group_name=group_name,
                            emails=group_emails,
                            smsf_name=ctx.smsf,
                        ))
                else:
                    # No advisor grouping — single fallback PDF
                    await self._queue.put(PDFJob(
                        group_name=ctx.smsf,
                        emails=emails,
                        smsf_name=ctx.smsf,
                    ))

                if self._store:
                    self._store.mark_processed(ctx.smsf)

            except OutlookUnavailableError:
                raise
            except Exception as exc:
                logger.exception("Producer failed for SMSF %s: %s", ctx.smsf, exc)
                self._progress.error(ctx.smsf, str(exc))
                self._failed_count += 1

        await self._queue.put(None)  # Poison pill signals consumer to stop

    # ------------------------------------------------------------------
    # Consumer: async Playwright, pulls jobs from queue
    # ------------------------------------------------------------------
    async def _consumer(self, pdf_gen: AsyncPDFGenerator) -> None:
        while True:
            job = await self._queue.get()
            if job is None:
                self._queue.task_done()
                break

            try:
                html = self._deps.email_formatter.format_multiple_emails(job.emails)
                folder = self._output_base / job.smsf_name
                folder.mkdir(parents=True, exist_ok=True)
                filename = f"{job.group_name}.pdf"
                path = folder / filename
                success = await pdf_gen.generate_pdf(html, path)
                if success:
                    self._progress.complete(job.group_name, str(path))
                else:
                    logger.error("PDF generation failed for %s", job.group_name)
                    self._failed_count += 1
            except Exception as exc:
                logger.exception("Consumer failed for %s: %s", job.group_name, exc)
                self._failed_count += 1
            finally:
                self._queue.task_done()

    # ------------------------------------------------------------------
    # Initialize Outlook searcher and pipeline components
    # ------------------------------------------------------------------
    def connect(self) -> bool:
        session = self._deps.session_manager
        if not session or not session.connect() or not session.is_connected():
            return False

        self._session = session
        self._searcher = self._deps.email_searcher or EmailSearcher(
            session_manager=session,
            processed_store=self._deps.processed_store,
            config_manager=self._deps.config_manager,
            cache=self._deps.cache,
        )
        self._store = self._deps.processed_store
        (self._advisor_matcher,
         self._search_engine,
         self._deduplicator,
         self._pdf_grouper) = CompositionRoot.build_pipeline_components()
        return True


async def async_main(exec_context: ExecutionContext) -> int:
    """
    Async entry point. Validates license, connects to Outlook,
    and runs the async producer-consumer pipeline.
    """
    try:
        output_base = exec_context.output_dir or _get_default_output_base()
        deps = CompositionRoot(output_base).build()

        license_key = deps.license_validator.prompt_and_validate()
        if not license_key:
            sys.stderr.write("ERROR: License validation failed\n")
            sys.stderr.flush()
            return 1

        orchestrator = AsyncPipelineOrchestrator(deps, output_base)

        if not orchestrator.connect():
            sys.stderr.write("ERROR: Could not connect to Outlook. Ensure Outlook is open.\n")
            sys.stderr.flush()
            return 1

        if exec_context.mode == ExecutionMode.BATCH:
            smsf_ctxs = [
                SMSFSpec(
                    smsf=e.smsf,
                    search_terms=e.search_terms,
                    start_date=e.start_date,
                    end_date=e.end_date,
                    mode="batch",
                    skip_if_processed=True,
                )
                for e in (exec_context.smsf_entries or [])
            ]
        else:
            cli = CLI()
            smsf_ctxs = []
            while True:
                try:
                    user_input = cli.get_smsf_input()
                except ValueError as e:
                    sys.stderr.write(f"ERROR: {e}\n")
                    continue
                smsf_ctxs.append(SMSFSpec(
                    smsf=user_input["smsf"],
                    search_terms=user_input["search_terms"],
                    start_date=user_input["start_date"],
                    end_date=user_input["end_date"],
                    mode="interactive",
                    skip_if_processed=False,
                ))
                if not cli.prompt_continue():
                    break

        result = await orchestrator.run(smsf_ctxs)
        return result

    except LicenseInputUnavailableError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.stderr.flush()
        return 1
    except OutlookUnavailableError as e:
        sys.stderr.write(f"ERROR: Outlook connection lost: {e}\n")
        sys.stderr.flush()
        return 1
    except Exception as exc:
        logger.exception("Fatal error in async pipeline: %s", exc)
        return 1


def main(argv: Optional[list] = None) -> int:
    exec_context = CLI.resolve(argv)

    try:
        orchestrator = MainOrchestrator(context=exec_context)
        return orchestrator.run()
    except LicenseInputUnavailableError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.stderr.flush()
        return 1
    except OutlookUnavailableError as e:
        sys.stderr.write(f"ERROR: Outlook connection lost: {e}\n")
        sys.stderr.flush()
        return 1


if __name__ == "__main__":
    sys.exit(main())
