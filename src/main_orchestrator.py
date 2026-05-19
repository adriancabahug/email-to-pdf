"""
Orchestrates the end-to-end email-to-PDF pipeline.
Uses PDFSession context manager to guarantee browser lifecycle.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.config_manager import ConfigManager
from src.outlook_session_manager import OutlookSessionManager
from src.email_searcher import EmailSearcher
from src.processed_directors_store import ProcessedDirectorsStore
from src.email_formatter import EmailFormatter
from src.file_manager import FileManager
from src.license_validator import LicenseValidator
from src.progress_manager import ProgressManager
from src.pdf_generator import PDFGenerator, PDFSession
from src.cli import CLI, ExecutionContext, ExecutionMode, SMSFEntry
from src.exceptions import LicenseInputUnavailableError, OutlookUnavailableError
from src.dependencies import Dependencies, CompositionRoot


LICENSE_SERVER_URL = "https://email-to-pdf-license.email-to-pdf-license.workers.dev/validate"


def _get_default_output_base() -> Path:
    default_docs = Path(os.environ.get("USERPROFILE", ".")) / "Documents"
    return default_docs / "EmailPDFs"


@dataclass(frozen=True)
class SMSFContext:
    smsf: str
    search_terms: list
    start_date: any
    end_date: any
    mode: str
    skip_if_processed: bool = True


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

    # ------------------------------------------------------------------ #
    # Entry point
    # ------------------------------------------------------------------ #
    def run(self) -> int:
        license_key = self._license.prompt_and_validate()
        if not license_key:
            self._progress.error("SYSTEM", "License validation failed")
            return 1

        self._print_banner()

        try:
            with PDFSession(self._deps.pdf_generator) as pdf:
                self._pdf = pdf
                if self._context.mode == ExecutionMode.BATCH:
                    return self._run_batch()
                return self._run_interactive()
        except RuntimeError as exc:
            self._progress.error("SYSTEM", f"PDF engine failed: {exc}")
            return 1
        finally:
            self._cleanup()

    # ------------------------------------------------------------------ #
    # Mode runners
    # ------------------------------------------------------------------ #
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
            ctx = SMSFContext(
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

            ctx = SMSFContext(
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

    # ------------------------------------------------------------------ #
    # Unified pipeline
    # ------------------------------------------------------------------ #
    def _process_smsf(self, ctx: SMSFContext) -> int:
        try:
            if ctx.skip_if_processed and self._store.is_processed(ctx.smsf):
                self._progress.skip(ctx.smsf, "Already processed")
                return 0

            self._progress.start(ctx.smsf)

            emails = self._searcher.search(ctx.search_terms, ctx.start_date, ctx.end_date)
            if not emails:
                self._progress.warning(ctx.smsf, "No emails matched criteria")
                self._store.mark_processed(ctx.smsf)
                return 0

            html = self._email_formatter.format_multiple_emails(emails)
            path = self._file_mgr.save_pdf(html, ctx.smsf)

            if not path:
                self._progress.error(ctx.smsf, "PDF generation failed — SMSF not marked processed")
                return 1

            self._store.mark_processed(ctx.smsf)
            self._progress.complete(ctx.smsf, str(path))
            return 0

        except OutlookUnavailableError:
            self._session.disconnect()
            raise
        except Exception as exc:
            self._progress.error(ctx.smsf, str(exc))
            return 1

    def _connect_to_outlook(self) -> bool:
        self._session = self._deps.session_manager
        success = self._session.connect()

        if success and self._session.is_connected():
            if self._deps.email_searcher:
                self._searcher = self._deps.email_searcher
            else:
                self._searcher = EmailSearcher(
                    session_manager=self._session,
                    processed_store=self._deps.processed_store,
                    config_manager=self._config
                )
            self._connected = True
            self._progress.print_info("Connected to Outlook successfully.")
            return True

        return False

    def _cleanup(self) -> None:
        if self._connected and self._session:
            self._session.disconnect()
            self._progress.print_info("Outlook connection closed.")

    def _print_banner(self) -> None:
        self._progress._console.print("\n" + "=" * 60)
        self._progress._console.print("[bold cyan]EMAIL TO PDF AUTOMATION TOOL[/bold cyan]")
        self._progress._console.print("=" * 60 + "\n")


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
