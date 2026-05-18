"""
Orchestrates the end-to-end email-to-PDF pipeline.
Uses PDFSession context manager to guarantee browser lifecycle.
"""

from __future__ import annotations

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
from src.cli import CLI, ExecutionContext, ExecutionMode
from src.exceptions import LicenseInputUnavailableError
from src.dependencies import Dependencies, CompositionRoot


LICENSE_SERVER_URL = "https://email-to-pdf-license.email-to-pdf-license.workers.dev/validate"


@dataclass(frozen=True)
class DirectorContext:
    first_name: str
    last_name: str
    smsf: str
    mode: str
    skip_if_processed: bool = True


class OutlookUnavailableError(Exception):
    """Outlook COM boundary failure requiring reconnection."""


class MainOrchestrator:
    def __init__(
        self,
        context: Optional[ExecutionContext] = None,
        output_base: Optional[Path] = None,
        deps: Optional[Dependencies] = None,
    ) -> None:
        self._context = context or CLI.resolve([])
        self._output_base = output_base or Path(r"C:\Users\admin\Documents\EmailPDFs")
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
        directors = self._context.directors
        if not directors:
            directors = self._config.get("directors", [])
        if not directors:
            self._progress.print_warn("No directors configured for batch mode.")
            return 0

        if not self._connect_to_outlook():
            self._progress.error("B", "Could not connect to Outlook. Ensure Outlook is open.")
            return 1

        failed = 0
        for director in directors:
            ctx = DirectorContext(
                first_name=director.get("first", director.get("first_name", "")),
                last_name=director.get("last", director.get("last_name", "")),
                smsf=director.get("smsf", ""),
                mode="batch",
                skip_if_processed=True,
            )
            failed += self._process_director(ctx)

        return failed

    def _run_interactive(self) -> int:
        if not self._connect_to_outlook():
            self._progress.error("B", "Could not connect to Outlook. Ensure Outlook is open.")
            return 1

        failed = 0

        while True:
            try:
                user_input = self._cli.get_director_input()
            except ValueError:
                self._progress.print_warn("First name and last name are required.")
                continue

            ctx = DirectorContext(
                first_name=user_input["first"],
                last_name=user_input["last"],
                smsf=user_input.get("smsf", ""),
                mode="interactive",
                skip_if_processed=False,
            )
            failed += self._process_director(ctx)

            if not self._cli.prompt_continue():
                break

        return failed

    # ------------------------------------------------------------------ #
    # Unified pipeline
    # ------------------------------------------------------------------ #
    def _process_director(self, ctx: DirectorContext) -> int:
        try:
            if ctx.skip_if_processed and self._store.is_processed(ctx.smsf):
                self._progress.skip(ctx.smsf, "Already processed")
                return 0

            full_name = f"{ctx.first_name} {ctx.last_name}"
            self._progress.start(full_name)

            email = self._session.discover_email_from_name(ctx.first_name, ctx.last_name)
            if not email:
                self._progress.error(ctx.smsf, "No Outlook identity found")
                return 1

            emails = self._searcher.search(email)
            if not emails:
                self._progress.warning(ctx.smsf, "No emails matched criteria")
                self._store.mark_processed(ctx.smsf)
                return 0

            html = self._email_formatter.format_multiple_emails(emails)
            path = self._file_mgr.save_pdf(html, ctx.first_name, ctx.last_name, ctx.smsf)

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
