"""
Tests for SMSF Context Module.
"""

import json
from datetime import datetime
from pathlib import Path
import tempfile

import pytest

from src.smsf_context import SMSFContext, SMSFContextError


class TestSMSFContextCreation:
    def test_create_with_required_fields(self):
        ctx = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John Smith", "Jane Doe"],
            director_emails=["john@aura.com.au"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        assert ctx.smsf_name == "Aura Super"
        assert ctx.director_names == ["John Smith", "Jane Doe"]
        assert ctx.director_emails == ["john@aura.com.au"]
        assert ctx.advisor_domains == ["ventasadvisory.com.au"]

    def test_create_with_timeframe(self):
        ctx = SMSFContext(
            smsf_name="Beta Super",
            director_names=["Alice"],
            director_emails=[],
            advisor_domains=["exceedia.com.au"],
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 12, 31),
        )
        assert ctx.start_date == datetime(2026, 1, 1)
        assert ctx.end_date == datetime(2026, 12, 31)


class TestNormalizedTokens:
    def test_generates_search_tokens(self):
        ctx = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John Smith"],
            director_emails=["john@smith.com"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        tokens = ctx.get_search_tokens()
        assert "aura super" in tokens
        assert "john smith" in tokens
        assert "john@smith.com" in tokens
        assert "ventasadvisory.com.au" in tokens

    def test_tokens_are_lowercased(self):
        ctx = SMSFContext(
            smsf_name="My Super Fund",
            director_names=["Test User"],
            director_emails=[],
            advisor_domains=["Example.com"],
        )
        tokens = ctx.get_search_tokens()
        for token in tokens:
            assert token.islower()


class TestImmutability:
    def test_context_is_frozen(self):
        ctx = SMSFContext(
            smsf_name="Test Fund",
            director_names=["Director"],
            director_emails=[],
            advisor_domains=["domain.com"],
        )
        with pytest.raises(AttributeError):
            ctx.smsf_name = "New Name"


class TestJSONSerialization:
    def test_to_json(self):
        ctx = SMSFContext(
            smsf_name="Aura Super",
            director_names=["John Smith"],
            director_emails=["john@aura.com.au"],
            advisor_domains=["ventasadvisory.com.au"],
        )
        json_str = ctx.to_json()
        data = json.loads(json_str)
        assert data["smsf_name"] == "Aura Super"
        assert data["director_names"] == ["John Smith"]

    def test_from_json(self):
        json_str = '{"smsf_name": "Beta Super", "director_names": ["Alice"], "director_emails": [], "advisor_domains": ["test.com"]}'
        ctx = SMSFContext.from_json(json_str)
        assert ctx.smsf_name == "Beta Super"
        assert ctx.director_names == ["Alice"]

    def test_roundtrip_preserves_data(self):
        original = SMSFContext(
            smsf_name="Gamma Fund",
            director_names=["Director One", "Director Two"],
            director_emails=["one@fund.com", "two@fund.com"],
            advisor_domains=["advisor1.com", "advisor2.com"],
        )
        restored = SMSFContext.from_json(original.to_json())
        assert restored.smsf_name == original.smsf_name
        assert restored.director_names == original.director_names


class TestFileOperations:
    def test_save_to_file(self):
        ctx = SMSFContext(
            smsf_name="Test Fund",
            director_names=["Dir"],
            director_emails=[],
            advisor_domains=["test.com"],
        )
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = Path(f.name)
        try:
            ctx.save_to_file(path)
            assert path.exists()
            loaded = SMSFContext.load_from_file(path)
            assert loaded.smsf_name == "Test Fund"
        finally:
            path.unlink(missing_ok=True)

    def test_load_invalid_file_raises(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json")
            path = Path(f.name)
        try:
            with pytest.raises(SMSFContextError):
                SMSFContext.load_from_file(path)
        finally:
            path.unlink(missing_ok=True)