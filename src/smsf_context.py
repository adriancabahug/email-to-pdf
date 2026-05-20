"""
SMSF Context Module - Encapsulates all search-relevant SMSF metadata.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class SMSFContextError(Exception):
    pass


@dataclass(frozen=True)
class SMSFContext:
    smsf_name: str
    director_names: List[str] = field(default_factory=list)
    director_emails: List[str] = field(default_factory=list)
    advisor_domains: List[str] = field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    def get_search_tokens(self) -> List[str]:
        tokens = []

        if self.smsf_name:
            tokens.append(self.smsf_name.lower())

        for name in self.director_names:
            tokens.append(name.lower())

        for email in self.director_emails:
            tokens.append(email.lower())

        for domain in self.advisor_domains:
            tokens.append(domain.lower())

        return tokens

    def to_json(self) -> str:
        data = {
            "smsf_name": self.smsf_name,
            "director_names": self.director_names,
            "director_emails": self.director_emails,
            "advisor_domains": self.advisor_domains,
        }
        if self.start_date:
            data["start_date"] = self.start_date.isoformat()
        if self.end_date:
            data["end_date"] = self.end_date.isoformat()
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "SMSFContext":
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise SMSFContextError(f"Invalid JSON: {e}") from e

        start_date = None
        end_date = None
        if data.get("start_date"):
            start_date = datetime.fromisoformat(data["start_date"])
        if data.get("end_date"):
            end_date = datetime.fromisoformat(data["end_date"])

        return cls(
            smsf_name=data["smsf_name"],
            director_names=data.get("director_names", []),
            director_emails=data.get("director_emails", []),
            advisor_domains=data.get("advisor_domains", []),
            start_date=start_date,
            end_date=end_date,
        )

    def save_to_file(self, path: Path) -> None:
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load_from_file(cls, path: Path) -> "SMSFContext":
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise SMSFContextError(f"File not found: {path}") from e
        except IOError as e:
            raise SMSFContextError(f"Failed to read file: {e}") from e

        try:
            return cls.from_json(content)
        except SMSFContextError as e:
            raise SMSFContextError(f"Failed to parse SMSF context: {e}") from e