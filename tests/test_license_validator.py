"""
Tests for LicenseValidator with injectable HTTP client.
No network calls. No file system leaks.
"""

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from src.license_validator import LicenseValidator


class FakeResponse:
    def __init__(self, payload: Dict[str, Any], status: int = 200):
        self._payload = payload
        self.status_code = status

    def json(self) -> Dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttp:
    def __init__(self, response: FakeResponse):
        self._response = response
        self.calls: list = []

    def post(self, url: str, **kwargs) -> FakeResponse:
        self.calls.append((url, kwargs))
        return self._response


@pytest.fixture
def storage(tmp_path: Path) -> Path:
    return tmp_path / "license.json"


@pytest.fixture
def validator(storage: Path) -> LicenseValidator:
    return LicenseValidator(
        api_url="https://test.example/validate",
        storage_path=storage,
    )


class TestValidateKey:
    def test_success(self, storage: Path):
        http = FakeHttp(FakeResponse({"valid": True, "tier": "pro"}))
        v = LicenseValidator("https://test.example/validate", storage, http_client=http)
        result = v.validate_key("KEY-123")

        assert result["valid"] is True
        assert http.calls[0][0] == "https://test.example/validate"
        assert http.calls[0][1]["json"] == {"key": "KEY-123"}

    def test_http_error(self, storage: Path):
        http = FakeHttp(FakeResponse({}, status=500))
        v = LicenseValidator("https://test.example/validate", storage, http_client=http)
        with pytest.raises(RuntimeError):
            v.validate_key("BAD-KEY")

    def test_timeout_passed_through(self, storage: Path):
        http = FakeHttp(FakeResponse({"valid": True}))
        v = LicenseValidator("https://test.example/validate", storage, http_client=http)
        v.validate_key("KEY")
        assert http.calls[0][1]["timeout"] == (5, 10)


class TestStorage:
    def test_get_stored_key_missing_file(self, validator: LicenseValidator):
        assert validator.get_stored_key() is None

    def test_get_stored_key_valid(self, validator: LicenseValidator, storage: Path):
        storage.write_text(json.dumps({"license_key": "SECRET"}))
        assert validator.get_stored_key() == "SECRET"

    def test_get_stored_key_malformed_json(self, validator: LicenseValidator, storage: Path):
        storage.write_text("not json")
        assert validator.get_stored_key() is None

    def test_store_key_atomic(self, validator: LicenseValidator, storage: Path):
        validator.store_key("NEW-KEY")
        assert json.loads(storage.read_text()) == {"license_key": "NEW-KEY"}
        assert not storage.with_suffix(".tmp").exists()


class TestPromptAndValidate:
    def test_uses_stored_key_when_valid(self, storage: Path, monkeypatch):
        storage.write_text(json.dumps({"license_key": "STORED"}))
        http = FakeHttp(FakeResponse({"valid": True}))
        v = LicenseValidator("https://test.example/validate", storage, http_client=http)

        result = v.prompt_and_validate()
        assert result == "STORED"

    def test_prompts_on_invalid_stored_key(self, storage: Path, monkeypatch):
        storage.write_text(json.dumps({"license_key": "OLD"}))
        http = FakeHttp(FakeResponse({"valid": False}))
        v = LicenseValidator("https://test.example/validate", storage, http_client=http)

        prompts = iter(["FRESH-KEY"])
        monkeypatch.setattr("src.license_validator.Prompt.ask", lambda msg, **kw: next(prompts))

        http._response = FakeResponse({"valid": True})
        result = v.prompt_and_validate()
        assert result == "FRESH-KEY"
        assert v.get_stored_key() == "FRESH-KEY"