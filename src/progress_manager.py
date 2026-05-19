"""ProgressManager - Rich CLI abstraction for operator-facing output."""

import sys
import time
from typing import TYPE_CHECKING, Optional, List, Dict, Any
if TYPE_CHECKING:
    from src.email_searcher import SearchEvent
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.tree import Tree

from src.config_manager import ConfigManager


class ProgressManager:
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self._config = config_manager
        self._console = Console()
        self._verbose = False
        self._live: Optional[Live] = None
        self._progress: Optional[Progress] = None
        self._task: Optional[Any] = None
        self._start_time: Optional[float] = None
        self._current_activity = ""
        self._accounts_scanned = 0
        self._folders_scanned = 0
        self._emails_found = 0
        self._matches_found = 0
        self._pdfs_generated = 0
        self._failures = 0
        self._retry_attempt = 0
        self._max_retries = 3

        if config_manager:
            self._verbose = config_manager.get("logging.verbose_console", False)

    def set_verbose(self, enabled: bool) -> None:
        self._verbose = enabled

    def start(self, identifier: str, folder_count: Optional[int] = None) -> None:
        self._start_time = time.time()
        self._accounts_scanned = 0
        self._folders_scanned = 0
        self._emails_found = 0
        self._matches_found = 0
        self._pdfs_generated = 0
        self._failures = 0

        if folder_count is not None and sys.stdout.isatty():
            self._progress = Progress(
                BarColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=self._console,
            )
            self._progress.start()
            self._task = self._progress.add_task(f"Searching {identifier}...", total=folder_count)
        else:
            self._progress = None
            self._task = None

        self._console.print(f"\n[bold blue]Processing:[/bold blue] {identifier}")

    def update_activity(self, folder_name: str, emails_found: int = 0, matches_found: int = 0) -> None:
        self._current_activity = folder_name
        self._emails_found += emails_found
        self._matches_found += matches_found
        self._folders_scanned += 1

        if self._progress and self._task is not None:
            self._progress.update(self._task, description=f"Searching {folder_name}")
            self._progress.advance(self._task)

        elapsed = self._elapsed()
        status = f"[cyan]{folder_name}[/cyan]"
        stats = f"Emails: {self._emails_found} | Matches: {self._matches_found} | Elapsed: {elapsed}s"
        self._console.print(f"  {status}  {stats}")

    def increment_account(self) -> None:
        self._accounts_scanned += 1

    def show_retry(self, attempt: int, max_attempts: int, delay_remaining: float) -> None:
        self._retry_attempt = attempt
        self._max_retries = max_attempts
        self._console.print(f"  [yellow]RPC unavailable — retry {attempt}/{max_attempts} in {delay_remaining:.1f}s[/yellow]")

    def show_outlook_restart(self, event_type: str) -> None:
        if event_type == "launch":
            self._console.print(f"  [yellow]Outlook not running — launching...[/yellow]")
        elif event_type == "terminate":
            self._console.print(f"  [yellow]Outlook unresponsive — terminating and restarting...[/yellow]")
        elif event_type == "reconnect":
            self._console.print(f"  [green]Outlook reconnected successfully[/green]")

    def show_error(self, category: str, message: str, action: Optional[str] = None) -> None:
        panel = Panel(
            f"[bold]Category {category}[/bold]\n{message}"
            + (f"\n\n[bold]Action:[/bold] {action}" if action else ""),
            title="[bold red]Error[/bold red]",
            border_style="red"
        )
        self._console.print(panel)

    def show_category_d_error(self, message: str) -> None:
        self._console.print(f"\n[bold red]OUTLOOK REQUIRES USER INTERVENTION[/bold red]")
        self._console.print(f"  {message}")
        self._console.print("  Please sign in to Outlook manually and restart the application.\n")

    def show_completion_summary(
        self,
        total_processed: int,
        pdfs_generated: int,
        failures: int,
        skipped: int = 0
    ) -> None:
        table = Table(title="Run Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Total Processed", str(total_processed))
        table.add_row("PDFs Generated", str(pdfs_generated))
        table.add_row("Skipped (already processed)", str(skipped))
        table.add_row("Failures", str(failures))
        table.add_row("Elapsed Time", f"{self._elapsed():.1f}s")

        self._console.print(table)

    def print_info(self, message: str) -> None:
        self._console.print(f"  [green]INFO:[/green] {message}")

    def print_warn(self, message: str) -> None:
        self._console.print(f"  [yellow]WARN:[/yellow] {message}")

    def print_verbose(self, message: str) -> None:
        if self._verbose:
            self._console.print(f"  [dim]DEBUG:[/dim] {message}")

    def _elapsed(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def stop(self) -> None:
        """Stop the progress bar and clean up."""
        if self._progress:
            self._progress.stop()
            self._progress = None
            self._task = None

    def display_search_event(self, event: "SearchEvent") -> None:
        """Display real-time search progress events."""
        import sys
        if not sys.stdout.isatty():
            return

        if event.type == 'account':
            self._console.print(
                f"\n[bold cyan]Account:[/bold cyan] {event.account} | "
                f"[bold]{event.total or 0:,}[/bold] total items"
            )
        elif event.type == 'folder':
            self._console.print(
                f"  [dim]Scanning {event.folder}... "
                f"({event.total or 0:,} items)[/dim]"
            )
        elif event.type == 'match':
            self._console.print(f"    [green]✓[/green] [bold]{event.subject}[/bold]")
            self._console.print(
                f"      [dim]From:[/dim] {event.sender} | "
                f"[dim]{event.date}[/dim]"
            )
        elif event.type == 'complete':
            self._console.print(
                f"\n[bold green]Found {event.total or 0} matching emails[/bold green]"
            )

    # ------------------------------------------------------------------ #
    # Aliases for the API expected by MainOrchestrator
    # ------------------------------------------------------------------ #
    def error(self, identifier: str, message: str) -> None:
        self.show_error(category=identifier, message=message)

    def warning(self, identifier: str, message: str) -> None:
        self.print_warn(f"{identifier}: {message}")

    def complete(self, identifier: str, path: str) -> None:
        self.print_info(f"Completed {identifier} → {path}")

    def skip(self, identifier: str, reason: str) -> None:
        self.print_warn(f"Skipped {identifier}: {reason}")
