"""Custom exceptions for the Email to PDF application."""


class StdinUnavailableError(RuntimeError):
    """Raised when an interactive operation is attempted outside a terminal.

    This is the architectural guardrail for stdin boundaries. Any module that
    violates stdin availability constraints will surface this error.
    """


class LicenseInputUnavailableError(RuntimeError):
    """Raised when license key entry is required but cannot proceed.

    This is a terminal licensing failure in batch mode where a license key
    is needed but stdin is not available and no key is stored. The orchestrator
    handles this by exiting cleanly with a message. This exception explicitly
    prohibits silent fallback patterns.
    """


class OutlookUnavailableError(RuntimeError):
    """Outlook COM boundary failure requiring reconnection or user intervention."""