"""
Unified CLI boundary. Replaces three shallow modules:
- execution_mode.py (argparse wrapper)
- stdin_guard.py (isatty check)
- input_handler.py (Rich prompt wrapper)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional

from rich.prompt import Confirm, Prompt


class ExecutionMode(Enum):
    BATCH = auto()
    INTERACTIVE = auto()


@dataclass(frozen=True)
class SMSFEntry:
    smsf: str
    search_terms: List[str]
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class ExecutionContext:
    mode: ExecutionMode
    smsf_entries: List[SMSFEntry]
    output_dir: Path
    verbose: bool = False


class CLI:
    """
    Single entry point for argument parsing, TTY detection,
    interactive prompting, and batch file loading.
    """

    # ------------------------------------------------------------------ #
    # Argument parsing (absorbed from execution_mode.py)
    # ------------------------------------------------------------------ #
    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="email-to-pdf",
            description="Export director emails to PDF",
        )
        parser.add_argument(
            "--batch",
            metavar="FILE",
            help="Path to CSV/JSON batch file (switches to batch mode)",
        )
        parser.add_argument(
            "--output",
            "-o",
            default=".",
            help="Output directory for PDFs [default: current directory]",
        )
        parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Enable verbose logging",
        )
        return parser

    @classmethod
    def resolve(cls, args: Optional[List[str]] = None) -> ExecutionContext:
        parser = cls.build_parser()
        ns = parser.parse_args(args)

        output_dir = Path(ns.output).expanduser().resolve()

        if ns.batch:
            smsf_entries = cls._load_batch_file(Path(ns.batch))
            return ExecutionContext(
                mode=ExecutionMode.BATCH,
                smsf_entries=smsf_entries,
                output_dir=output_dir,
                verbose=ns.verbose,
            )

        if not cls._stdin_available():
            parser.error("Interactive mode requires an interactive terminal (TTY)")

        return ExecutionContext(
            mode=ExecutionMode.INTERACTIVE,
            smsf_entries=[],
            output_dir=output_dir,
            verbose=ns.verbose,
        )

    # ------------------------------------------------------------------ #
    # Stdin guard (absorbed from stdin_guard.py)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _stdin_available() -> bool:
        try:
            return sys.stdin.isatty()
        except (AttributeError, OSError):
            return False

    @staticmethod
    def require_stdin(operation: str) -> None:
        if not CLI._stdin_available():
            raise RuntimeError(f"{operation} requires an interactive terminal")

    # ------------------------------------------------------------------ #
    # Interactive input (absorbed from input_handler.py)
    # ------------------------------------------------------------------ #
    @staticmethod
    def validate_director_input(first: str, last: str) -> bool:
        return bool(first and last and first.strip() and last.strip())

    def get_director_input(self) -> Dict[str, str]:
        first = Prompt.ask("Director first name")
        last = Prompt.ask("Director last name")
        if not self.validate_director_input(first, last):
            raise ValueError("First and last names are required")
        smsf = Prompt.ask("SMSF identifier (optional)", default="")
        return {
            "first": first.strip(),
            "last": last.strip(),
            "smsf": smsf.strip(),
        }

    def prompt_continue(self) -> bool:
        return Confirm.ask("Process another SMSF?", default=True)

    @staticmethod
    def _get_current_year_date_range() -> tuple[Optional[datetime], Optional[datetime]]:
        """Return (None, None) for 'all time' search."""
        return None, None

    @staticmethod
    def _parse_keywords(input_str: str) -> List[str]:
        if not input_str.strip():
            return []
        terms = []
        for line in input_str.split('\n'):
            line = line.strip()
            if not line:
                continue
            if ',' in line:
                for part in line.split(','):
                    part = part.strip()
                    if part:
                        terms.append(part.lower())
            else:
                terms.append(line.lower())
        return terms

    def get_smsf_input(self) -> Dict[str, any]:
        smsf_name = Prompt.ask("SMSF name")
        if not smsf_name or not smsf_name.strip():
            raise ValueError("SMSF name is required")

        keywords_input = Prompt.ask(
            "Emails/keywords (comma-separated or one per line, blank to finish)",
            default=""
        )

        search_terms = self._parse_keywords(keywords_input)
        if not search_terms:
            raise ValueError("At least one keyword is required")

        date_choice = Prompt.ask(
            "Date range: [1] All time (default), [2] This year, [3] Custom range",
            default="1"
        )

        if date_choice == "2":
            now = datetime.now()
            start_date = datetime(now.year, 1, 1)
            end_date = datetime(now.year, 12, 31, 23, 59, 59)
        elif date_choice == "3":
            start_str = Prompt.ask("Start date (YYYY-MM-DD)")
            end_str = Prompt.ask("End date (YYYY-MM-DD)")
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_str, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD")
        else:
            start_date, end_date = self._get_current_year_date_range()

        return {
            "smsf": smsf_name.strip(),
            "search_terms": search_terms,
            "start_date": start_date,
            "end_date": end_date,
        }

    # ------------------------------------------------------------------ #
    # Batch file loading
    # ------------------------------------------------------------------ #
    @staticmethod
    def _load_batch_file(path: Path) -> List[SMSFEntry]:
        if not path.exists():
            raise FileNotFoundError(f"Batch file not found: {path}")
        suffix = path.suffix.lower()
        if suffix == ".json":
            return CLI._load_json(path)
        if suffix in (".csv", ".tsv"):
            return CLI._load_csv(path)
        raise ValueError(f"Unsupported batch format: {suffix}")

    @staticmethod
    def _parse_search_terms(terms_str: str) -> List[str]:
        if not terms_str:
            return []
        terms = []
        for term in terms_str.split(';'):
            term = term.strip()
            if term:
                terms.append(term.lower())
        return terms

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str.strip(), "%Y-%m-%d")
        except ValueError:
            return None

    @staticmethod
    def _load_json(path: Path) -> List[SMSFEntry]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw = [raw]

        entries = []
        current_year_start, current_year_end = CLI._get_current_year_date_range()

        for item in raw:
            smsf = str(item.get("smsf", item.get("id", "")))
            if not smsf:
                continue

            terms_str = item.get("search_terms", "")
            search_terms = CLI._parse_search_terms(terms_str)
            if not search_terms:
                continue

            start_date = CLI._parse_date(item.get("start_date")) or current_year_start
            end_date = CLI._parse_date(item.get("end_date")) or current_year_end

            entries.append(SMSFEntry(
                smsf=smsf,
                search_terms=search_terms,
                start_date=start_date,
                end_date=end_date,
            ))
        return entries

    @staticmethod
    def _load_csv(path: Path) -> List[SMSFEntry]:
        entries = []
        current_year_start, current_year_end = CLI._get_current_year_date_range()

        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                smsf = row.get("smsf", row.get("id", ""))
                if not smsf:
                    continue

                terms_str = row.get("search_terms", "")
                search_terms = CLI._parse_search_terms(terms_str)
                if not search_terms:
                    continue

                start_date = CLI._parse_date(row.get("start_date")) or current_year_start
                end_date = CLI._parse_date(row.get("end_date")) or current_year_end

                entries.append(SMSFEntry(
                    smsf=smsf,
                    search_terms=search_terms,
                    start_date=start_date,
                    end_date=end_date,
                ))
        return entries