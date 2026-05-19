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
    from src.pdf_generator import PDFGenerator
    from src.processed_directors_store import ProcessedDirectorsStore
    from src.progress_manager import ProgressManager


@dataclass
class Dependencies:
    session_manager: Optional["OutlookSessionManager"] = None
    email_searcher: Optional["EmailSearcher"] = None
    email_formatter: Optional["EmailFormatter"] = None
    pdf_generator: Optional["PDFGenerator"] = None
    file_manager: Optional["FileManager"] = None
    config_manager: Optional["ConfigManager"] = None
    processed_store: Optional["ProcessedDirectorsStore"] = None
    progress_manager: Optional["ProgressManager"] = None
    license_validator: Optional["LicenseValidator"] = None


class CompositionRoot:
    LICENSE_API_URL = "https://email-to-pdf-license.email-to-pdf-license.workers.dev/validate"

    def __init__(self, output_base: Path) -> None:
        self._output_base = output_base

    def build(self) -> Dependencies:
        from src.config_manager import ConfigManager
        from src.contacts import is_approved_contact
        from src.email_formatter import EmailFormatter
        from src.email_searcher import EmailSearcher
        from src.file_manager import FileManager
        from src.license_validator import LicenseValidator
        from src.outlook_session_manager import OutlookSessionManager
        from src.pdf_generator import PDFGenerator
        from src.processed_directors_store import ProcessedDirectorsStore
        from src.progress_manager import ProgressManager

        cfg = ConfigManager.load()
        appdata = cfg.appdata_dir()
        pdf_gen = PDFGenerator()
        session_mgr = OutlookSessionManager()

        return Dependencies(
            session_manager=session_mgr,
            email_searcher=EmailSearcher(
                session_manager=session_mgr,
                processed_store=None,
                config_manager=cfg,
            ),
            email_formatter=EmailFormatter(config_manager=cfg),
            pdf_generator=pdf_gen,
            file_manager=FileManager(
                output_base=self._output_base,
                pdf_generator=pdf_gen,
                email_formatter=EmailFormatter(config_manager=cfg),
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
        )
