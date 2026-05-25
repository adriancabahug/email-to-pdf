from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.config_manager import ConfigManager
    from src.email_formatter import EmailFormatter
    from src.email_searcher import EmailSearcher
    from src.file_manager import FileManager
    from src.license_validator import LicenseValidator
    from src.outlook_session_manager import OutlookSessionManager
    from src.pdf_generator import PDFGenerator, AsyncPDFGenerator
    from src.processed_directors_store import ProcessedDirectorsStore
    from src.progress_manager import ProgressManager
    from src.cache_manager import EmailMetadataCache
    from src.advisor_domain_matcher import AdvisorDomainMatcher
    from src.search_rule_engine import SearchRuleEngine
    from src.deduplication import CrossMailboxDeduplicator
    from src.advisor_pdf_grouping import AdvisorPDFGroupingEngine


@dataclass
class Dependencies:
    session_manager: Optional["OutlookSessionManager"] = None
    email_searcher: Optional["EmailSearcher"] = None
    email_formatter: Optional["EmailFormatter"] = None
    pdf_generator: Optional["PDFGenerator"] = None
    async_pdf_generator: Optional["AsyncPDFGenerator"] = None
    file_manager: Optional["FileManager"] = None
    config_manager: Optional["ConfigManager"] = None
    processed_store: Optional["ProcessedDirectorsStore"] = None
    progress_manager: Optional["ProgressManager"] = None
    license_validator: Optional["LicenseValidator"] = None
    cache: Optional["EmailMetadataCache"] = None


class CompositionRoot:
    LICENSE_API_URL = "https://email-to-pdf-license.email-to-pdf-license.workers.dev/validate"

    def __init__(self, output_base: Path) -> None:
        self._output_base = output_base

    def build(self) -> Dependencies:
        from src.config_manager import ConfigManager
        from src.email_formatter import EmailFormatter
        from src.email_searcher import EmailSearcher
        from src.file_manager import FileManager
        from src.license_validator import LicenseValidator
        from src.outlook_session_manager import OutlookSessionManager
        from src.pdf_generator import PDFGenerator, AsyncPDFGenerator
        from src.processed_directors_store import ProcessedDirectorsStore
        from src.progress_manager import ProgressManager
        from src.cache_manager import EmailMetadataCache

        cfg = ConfigManager.load()
        appdata = cfg.appdata_dir()
        pdf_gen = PDFGenerator()
        async_pdf_gen = AsyncPDFGenerator()
        session_mgr = OutlookSessionManager()
        email_fmt = EmailFormatter(config_manager=cfg)

        # Initialize SQLite cache
        cache_path = appdata / "email_cache.db"
        cache = None
        try:
            cache = EmailMetadataCache(cache_path)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Cache init failed: %s", exc)

        return Dependencies(
            session_manager=session_mgr,
            email_searcher=EmailSearcher(
                session_manager=session_mgr,
                processed_store=None,
                config_manager=cfg,
                cache=cache,
            ),
            email_formatter=email_fmt,
            pdf_generator=pdf_gen,
            async_pdf_generator=async_pdf_gen,
            file_manager=FileManager(
                output_base=self._output_base,
                pdf_generator=pdf_gen,
                email_formatter=email_fmt,
            ),
            config_manager=cfg,
            processed_store=ProcessedDirectorsStore(
                storage_path=appdata / "processed_directors.json"
            ),
            progress_manager=ProgressManager(config_manager=cfg),
            license_validator=LicenseValidator(
                api_url=self.LICENSE_API_URL,
                storage_path=appdata / "license.json",
            ),
            cache=cache,
        )

    @staticmethod
    def build_pipeline_components():
        """Shared factory for pipeline components used by both
        MainOrchestrator and AsyncPipelineOrchestrator."""
        from src.advisor_domain_matcher import AdvisorDomainMatcher
        from src.search_rule_engine import SearchRuleEngine
        from src.deduplication import CrossMailboxDeduplicator
        from src.advisor_pdf_grouping import AdvisorPDFGroupingEngine

        advisor_matcher = AdvisorDomainMatcher()
        search_engine = SearchRuleEngine(advisor_matcher)
        deduplicator = CrossMailboxDeduplicator()
        pdf_grouper = AdvisorPDFGroupingEngine(search_engine)
        return advisor_matcher, search_engine, deduplicator, pdf_grouper
