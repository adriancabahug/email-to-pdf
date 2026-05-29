"""
AsyncOrchestrator — High-performance single-threaded non-blocking pipeline
that interleaves Outlook COM email enumeration with async Playwright PDF rendering.

Uses a producer-consumer pattern with a bounded asyncio.Queue for backpressure.
Raw COM MailItem objects are eagerly evaluated into a lightweight frozen dataclass
so COM RPC locks are dropped immediately, allowing the producer to keep iterating
while the consumer scores, formats, and renders PDFs concurrently.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from src.dependencies import Dependencies
from src.smsf_context import SMSFContext
from src.search_rule_engine import SearchRuleEngine, RelevanceLevel
from src.advisor_domain_matcher import AdvisorDomainMatcher
from src.deduplication import CrossMailboxDeduplicator
from src.advisor_pdf_grouping import AdvisorPDFGroupingEngine
from src.folder_strategies import FastFolderStrategy

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class InMemoryEmail:
    """Lightweight frozen dataclass that eagerly captures COM MailItem properties.

    Instantiated by the producer immediately after enumeration so the COM RPC
    lock on the MailItem is released. Downstream consumer code reads these
    fields without any cross-process COM overhead.
    """
    subject: str = ""
    entry_id: str = ""
    html_body: str = ""
    body: str = ""
    received_time: Optional[datetime] = None
    sent_on: Optional[datetime] = None
    sender_name: str = ""
    sender_email: str = ""
    to_recipients: str = ""
    cc_recipients: str = ""
    bcc_recipients: str = ""
    smsf_name: str = ""


class AsyncOrchestrator:
    """Single-threaded async producer-consumer pipeline.

    The producer enumerates COM mail items via native ``for msg in items:``
    iteration (never ``Item(i)`` indexing), eagerly extracts every property
    through ``getattr`` with safe defaults, and pushes lightweight
    ``InMemoryEmail`` payloads into a bounded asyncio queue.

    The consumer pulls payloads, scores relevance, formats HTML, and renders
    each PDF through an already-connected Playwright page.

    Backpressure (queue maxsize=50) keeps memory flat when the consumer is
    slower than the producer, and an ``await asyncio.sleep(0.001)`` after
    every queue push prevents COM RPC blocking from starving the Playwright
    event-loop communication.
    """

    def __init__(
        self,
        deps: Dependencies,
        playwright_page: Any,
    ) -> None:
        self._deps = deps
        self._page = playwright_page
        self._queue: asyncio.Queue[Optional[InMemoryEmail]] = asyncio.Queue(maxsize=50)
        self._failed_count = 0
        self._progress = deps.progress_manager

        self._advisor_matcher: Optional[AdvisorDomainMatcher] = None
        self._search_engine: Optional[SearchRuleEngine] = None
        self._deduplicator: Optional[CrossMailboxDeduplicator] = None
        self._pdf_grouper: Optional[AdvisorPDFGroupingEngine] = None

    async def run(
        self,
        smsf_specs: List[Any],
        output_base: Path,
    ) -> int:
        """Launch producer and consumer concurrently.

        Args:
            smsf_specs: Iterable of SMSFSpec (or equivalent) objects, each
                carrying ``smsf``, ``search_terms``, ``start_date``,
                ``end_date``, ``mode``, and ``skip_if_processed``.
            output_base: Root directory under which SMSF PDF folders are created.

        Returns:
            0 on success, 1 if any fatal error occurred.
        """
        if not smsf_specs:
            return 0

        self._init_pipeline_components()

        try:
            await asyncio.gather(
                self._producer(smsf_specs),
                self._consumer(output_base),
            )
            return 0
        except Exception as exc:
            logger.exception("Async pipeline failed: %s", exc)
            return 1

    # ------------------------------------------------------------------
    # Producer
    # ------------------------------------------------------------------
    async def _producer(self, smsf_specs: List[Any]) -> None:
        """Enumerate COM folders, evaluate items into InMemoryEmail, push to queue.

        *Never* calls ``len(items)`` or ``items.Item(i)`` — uses the native
        ``for msg in items:`` COM iterator which works across both raw COM
        collections and standard Python array fallbacks.
        """
        session = self._deps.session_manager
        if not session or not session.is_connected():
            logger.error("Outlook session not connected — producer cannot start")
            self._progress.error("PRODUCER", "Outlook session not connected")
            self._failed_count = len(smsf_specs)
            await self._queue.put(None)
            return

        for spec in smsf_specs:
            try:
                store = self._deps.processed_store
                if store and spec.skip_if_processed and store.is_processed(
                    spec.smsf
                ):
                    self._progress.skip(spec.smsf, "Already processed")
                    continue

                self._progress.start(spec.smsf)
                logger.info(
                    "Producer scanning for SMSF %s | terms=%s",
                    spec.smsf, getattr(spec, "search_terms", []),
                )

                strategy = FastFolderStrategy()
                yielded_any = False
                search_terms = [
                    t.lower().strip()
                    for t in getattr(spec, "search_terms", [])
                    if t and t.strip()
                ]
                all_terms = [spec.smsf.lower()] + search_terms

                for folder in self._iter_folders(session, strategy):
                    folder_name = getattr(folder, "Name", "Unknown")
                    items = getattr(folder, "Items", None)
                    if items is None:
                        continue

                    try:
                        items = items.Restrict(self._build_date_filter(
                            spec.start_date, spec.end_date
                        ))
                    except Exception:
                        pass

                    # --------------------------------------------------
                    # CRITICAL: Native COM iteration — no len(), no Item(i)
                    # --------------------------------------------------
                    for msg in items:
                        try:
                            msg_class = getattr(msg, "Class", None)
                            if msg_class != 43:
                                continue

                            entry_id = getattr(msg, "EntryID", None)
                            if not entry_id:
                                continue

                            subject = str(getattr(msg, "Subject", "") or "")
                            sender = str(getattr(msg, "SenderName", "") or "")
                            sender_email = str(
                                getattr(msg, "SenderEmailAddress", "") or ""
                            )
                            to_field = str(getattr(msg, "To", "") or "")
                            cc_field = str(getattr(msg, "CC", "") or "")

                            # Quick metadata check — discard obvious non-matches
                            text_blob = " ".join([
                                subject, sender, sender_email,
                                to_field, cc_field,
                            ]).lower()

                            if not any(term in text_blob for term in all_terms):
                                continue

                            email = self._extract_com_item(msg, spec.smsf)

                            await self._queue.put(email)

                            # --------------------------------------------------
                            # CRITICAL: Yield control so Playwright can consume
                            # --------------------------------------------------
                            await asyncio.sleep(0.001)

                            yielded_any = True

                        except Exception as exc:
                            logger.debug(
                                "Skipping item in %s: %s", folder_name, exc
                            )
                            continue

                if yielded_any:
                    self._progress.stop()

            except Exception as exc:
                logger.exception("Producer failed for SMSF %s", spec.smsf)
                self._progress.error(spec.smsf, str(exc))
                self._failed_count += 1

        await self._queue.put(None)

    # ------------------------------------------------------------------
    # Consumer
    # ------------------------------------------------------------------
    async def _consumer(self, output_base: Path) -> None:
        """Pull InMemoryEmail payloads, score, format, and render PDFs.

        Uses the Playwright page passed at construction time to stream HTML
        directly into Chromium's memory (zero disk I/O for the HTML), then
        prints to a PDF file on disk.

        Consumer groups incoming emails by ``smsf_name`` so that all emails
        belonging to the same SMSF are rendered into a single PDF.
        """
        groups: dict[str, List[InMemoryEmail]] = {}

        while True:
            email = await self._queue.get()

            if email is None:
                for smsf_name, group in groups.items():
                    await self._render_group(smsf_name, group, output_base)
                self._queue.task_done()
                break

            groups.setdefault(email.smsf_name, []).append(email)
            self._queue.task_done()

    async def _render_group(
        self,
        smsf_name: str,
        emails: List[InMemoryEmail],
        output_base: Path,
    ) -> None:
        """Score relevance, format as HTML, and render a single PDF for a group."""
        if not emails:
            return

        try:
            relevant = self._filter_relevant(emails)
            if not relevant:
                return

            deduped = self._deduplicate(relevant)
            if not deduped:
                return

            grouped = self._group_by_advisor(deduped)
            if grouped:
                for group_name, group_emails in grouped.items():
                    await self._format_and_render(
                        group_name, group_emails, output_base, smsf_name
                    )
            else:
                await self._format_and_render(
                    smsf_name, deduped, output_base, smsf_name
                )

        except Exception as exc:
            logger.exception("Consumer render group failed for %s", smsf_name)
            self._progress.error(smsf_name, str(exc))
            self._failed_count += 1

    async def _format_and_render(
        self,
        group_name: str,
        emails: List[InMemoryEmail],
        output_base: Path,
        smsf_name: str,
    ) -> None:
        """Format emails to HTML and render PDF via Playwright page."""
        try:
            html = self._deps.email_formatter.format_multiple_emails(emails)

            folder_path = output_base / smsf_name
            folder_path.mkdir(parents=True, exist_ok=True)
            pdf_path = folder_path / f"{self._sanitise_filename(group_name)}.pdf"

            await self._page.set_content(html, wait_until="networkidle")
            await self._page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                margin={
                    "top": "20mm",
                    "bottom": "20mm",
                    "left": "15mm",
                    "right": "15mm",
                },
            )

            self._progress.complete(group_name, str(pdf_path))
            logger.info("PDF written: %s", pdf_path)

        except Exception as exc:
            logger.exception("Format/render failed for %s", group_name)
            self._progress.error(group_name, str(exc))
            self._failed_count += 1

    # ------------------------------------------------------------------
    # Score relevance
    # ------------------------------------------------------------------
    def _filter_relevant(self, emails: List[InMemoryEmail]) -> List[InMemoryEmail]:
        """Run SearchRuleEngine.is_relevant over the group, keep STRONG/MEDIUM."""
        if not self._search_engine or not self._advisor_matcher:
            return emails

        ctx = SMSFContext(
            smsf_name="",
            director_names=[],
            director_emails=[],
            advisor_domains=list(self._advisor_matcher._domain_to_org.keys()),
        )

        return [
            e
            for e in emails
            if self._search_engine.is_relevant(e, ctx, body_already_scanned=False)
            != RelevanceLevel.NONE
        ]

    def _deduplicate(
        self, emails: List[InMemoryEmail]
    ) -> List[InMemoryEmail]:
        """Run CrossMailboxDeduplicator over the group."""
        if not self._deduplicator:
            return emails
        try:
            return self._deduplicator.deduplicate(emails)
        except Exception as exc:
            logger.debug("Dedup failed: %s", exc)
            return emails

    def _group_by_advisor(
        self, emails: List[InMemoryEmail]
    ) -> Optional[dict[str, List[InMemoryEmail]]]:
        """Group by advisor organisation if grouping engine is available."""
        if not self._pdf_grouper or not self._advisor_matcher:
            return None

        ctx = SMSFContext(
            smsf_name="",
            director_names=[],
            director_emails=[],
            advisor_domains=list(self._advisor_matcher._domain_to_org.keys()),
        )
        try:
            return self._pdf_grouper.group_emails(emails, ctx, self._advisor_matcher)
        except Exception as exc:
            logger.debug("Advisor grouping failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # COM extractor
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_com_item(msg: Any, smsf_name: str = "") -> InMemoryEmail:
        """Defensively extract COM MailItem properties into InMemoryEmail.

        Uses ``getattr`` with safe defaults for every field so that atypical
        items (meeting receipts, non-delivery reports, etc.) never crash
        the pipeline.
        """
        return InMemoryEmail(
            subject=str(getattr(msg, "Subject", "") or ""),
            entry_id=str(getattr(msg, "EntryID", "") or ""),
            html_body=str(getattr(msg, "HTMLBody", "") or ""),
            body=str(getattr(msg, "Body", "") or ""),
            received_time=getattr(msg, "ReceivedTime", None),
            sent_on=getattr(msg, "SentOn", None),
            sender_name=str(getattr(msg, "SenderName", "") or ""),
            sender_email=str(getattr(msg, "SenderEmailAddress", "") or ""),
            to_recipients=str(getattr(msg, "To", "") or ""),
            cc_recipients=str(getattr(msg, "CC", "") or ""),
            bcc_recipients=str(getattr(msg, "BCC", "") or ""),
            smsf_name=smsf_name,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _iter_folders(self, session: Any, strategy: FastFolderStrategy):
        """Walk Outlook folders using a strategy filter.

        Yields folder objects where ``strategy(folder_name)`` returns True.
        """
        accounts = session.get_all_accounts()
        for account in accounts:
            name = getattr(account, "Name", "") or ""
            if strategy(name):
                yield account
            try:
                yield from self._walk_folders(account.Folders, strategy)
            except Exception:
                continue

    def _walk_folders(self, parent: Any, strategy: FastFolderStrategy):
        """Recursively walk sub-folders."""
        try:
            for folder in parent:
                name = getattr(folder, "Name", "") or ""
                if strategy(name):
                    yield folder
                try:
                    yield from self._walk_folders(folder.Folders, strategy)
                except Exception:
                    continue
        except Exception:
            return

    @staticmethod
    def _build_date_filter(start_date: Any, end_date: Any) -> str:
        """Build a DASL date-range filter string."""
        if not start_date:
            start_date = datetime(1970, 1, 1)
        if not end_date:
            end_date = datetime(9999, 12, 31, 23, 59, 59)

        def _escape(val: datetime) -> str:
            return val.strftime("%m/%d/%Y %I:%M %p")

        return (
            f"[ReceivedTime] >= '{_escape(start_date)}' AND "
            f"[ReceivedTime] <= '{_escape(end_date)}'"
        )

    @staticmethod
    def _sanitise_filename(raw: str) -> str:
        """Strip characters unsafe for file names."""
        clean = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in raw)
        return clean.strip().strip("._") or "email"

    # ------------------------------------------------------------------
    # Dependency wiring
    # ------------------------------------------------------------------
    def _init_pipeline_components(self) -> None:
        """Build pipeline components from shared factory."""
        from src.dependencies import CompositionRoot

        (
            self._advisor_matcher,
            self._search_engine,
            self._deduplicator,
            self._pdf_grouper,
        ) = CompositionRoot.build_pipeline_components()
