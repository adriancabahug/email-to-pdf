import pytest


class TestExceptions:
    def test_stdin_unavailable_error_inherits_runtime_error(self):
        from src.exceptions import StdinUnavailableError
        assert issubclass(StdinUnavailableError, RuntimeError)

    def test_stdin_unavailable_error_is_importable(self):
        from src.exceptions import StdinUnavailableError
        exc = StdinUnavailableError("test message")
        assert exc is not None

    def test_license_input_unavailable_error_inherits_runtime_error(self):
        from src.exceptions import LicenseInputUnavailableError
        assert issubclass(LicenseInputUnavailableError, RuntimeError)

    def test_license_input_unavailable_error_is_importable(self):
        from src.exceptions import LicenseInputUnavailableError
        exc = LicenseInputUnavailableError("test message")
        assert exc is not None