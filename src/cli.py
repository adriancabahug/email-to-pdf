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
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional

from rich.prompt import Confirm, Prompt


class ExecutionMode(Enum):
    BATCH = auto()
    INTERACTIVE = auto()


@dataclass(frozen=True)
class ExecutionContext:
    mode: ExecutionMode
    directors: List[Dict[str, str]]
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
            directors = cls._load_batch_file(Path(ns.batch))
            return ExecutionContext(
                mode=ExecutionMode.BATCH,
                directors=directors,
                output_dir=output_dir,
                verbose=ns.verbose,
            )

        if not cls._stdin_available():
            parser.error("Interactive mode requires an interactive terminal (TTY)")

        return ExecutionContext(
            mode=ExecutionMode.INTERACTIVE,
            directors=[],
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
        return Confirm.ask("Process another director?", default=True)

    # ------------------------------------------------------------------ #
    # Batch file loading
    # ------------------------------------------------------------------ #
    @staticmethod
    def _load_batch_file(path: Path) -> List[Dict[str, str]]:
        if not path.exists():
            raise FileNotFoundError(f"Batch file not found: {path}")
        suffix = path.suffix.lower()
        if suffix == ".json":
            return CLI._load_json(path)
        if suffix in (".csv", ".tsv"):
            return CLI._load_csv(path)
        raise ValueError(f"Unsupported batch format: {suffix}")

    @staticmethod
    def _load_json(path: Path) -> List[Dict[str, str]]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw = [raw]
        return [
            {
                "first": str(item.get("first", item.get("first_name", ""))),
                "last": str(item.get("last", item.get("last_name", ""))),
                "smsf": str(item.get("smsf", item.get("id", ""))),
            }
            for item in raw
        ]

    @staticmethod
    def _load_csv(path: Path) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rows.append(
                    {
                        "first": row.get("first", row.get("first_name", "")),
                        "last": row.get("last", row.get("last_name", "")),
                        "smsf": row.get("smsf", row.get("id", "")),
                    }
                )
        return rows