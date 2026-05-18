"""ProgressManager - Rich CLI abstraction for operator-facing output."""

import time
from typing import Optional, List, Dict, Any
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

    def start(self, director_name: str) -> None:
        self._start_time = time.time()
        self._accounts_scanned = 0
        self._folders_scanned = 0
        self._emails_found = 0
        self._matches_found = 0
        self._pdfs_generated = 0
        self._failures = 0
        self._console.print(f"\n[bold blue]Processing:[/bold blue] {director_name}")

    def update_activity(self, folder_name: str, emails_found: int = 0, matches_found: int = 0) -> None:
        self._current_activity = folder_name
        self._emails_found += emails_found
        self._matches_found += matches_found
        self._folders_scanned += 1

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