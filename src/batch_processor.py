"""
Batch Processor - Handles batch processing of multiple SMSFs.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml

from src.smsf_context import SMSFContext


class BatchLoadError(Exception):
    pass


@dataclass
class BatchResult:
    total: int
    succeeded: int
    failed: int
    pdfs_generated: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"BatchResult(total={self.total}, succeeded={self.succeeded}, failed={self.failed}, errors={len(self.errors)})"


class BatchProcessor:
    def load_batch_input(self, path: Path) -> List[SMSFContext]:
        if not path.exists():
            raise BatchLoadError(f"File not found: {path}")

        try:
            content = path.read_text(encoding="utf-8")
        except IOError as e:
            raise BatchLoadError(f"Failed to read file: {e}") from e

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise BatchLoadError(f"Invalid JSON: {e}") from e

        if "smsfs" not in data:
            raise BatchLoadError("Missing 'smsfs' key in batch input")

        smsfs_data = data["smsfs"]
        if not isinstance(smsfs_data, list):
            raise BatchLoadError("'smsfs' must be a list")

        contexts = []
        for idx, smsf_data in enumerate(smsfs_data):
            try:
                context = self._parse_smsf_data(smsf_data)
                contexts.append(context)
            except Exception as e:
                raise BatchLoadError(f"Error parsing SMSF at index {idx}: {e}") from e

        return contexts

    def _parse_smsf_data(self, data: dict) -> SMSFContext:
        smsf_name = data.get("smsf_name")
        if not smsf_name:
            raise ValueError("Missing 'smsf_name'")

        return SMSFContext(
            smsf_name=smsf_name,
            director_names=data.get("director_names", []),
            director_emails=data.get("director_emails", []),
            advisor_domains=data.get("advisor_domains", []),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
        )

    def process_batch(self, contexts: List[SMSFContext]) -> BatchResult:
        if not contexts:
            return BatchResult(total=0, succeeded=0, failed=0)

        total = len(contexts)
        succeeded = 0
        failed = 0
        pdfs: List[Path] = []
        errors: List[str] = []

        for idx, context in enumerate(contexts):
            try:
                result = self._process_single(context)
                if result:
                    succeeded += 1
                    pdfs.extend(result)
                else:
                    failed += 1
                    errors.append(f"SMSF '{context.smsf_name}' produced no PDFs")
            except Exception as e:
                failed += 1
                errors.append(f"SMSF '{context.smsf_name}' failed: {str(e)}")

        return BatchResult(
            total=total,
            succeeded=succeeded,
            failed=failed,
            pdfs_generated=pdfs,
            errors=errors,
        )

    def _process_single(self, context: SMSFContext) -> List[Path]:
        return []