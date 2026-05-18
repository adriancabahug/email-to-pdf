"""
Flattened contact data. Replaces the 66-line ContactRegistry class
with module-level constants and a pure function.
"""

from __future__ import annotations

from typing import FrozenSet

# ---------------------------------------------------------------------- #
# Data
# ---------------------------------------------------------------------- #
INTERNAL_CONTACTS: FrozenSet[str] = frozenset({
    "alice.smith@company.com",
    "bob.jones@company.com",
    "charlie.brown@company.com",
})

EXTERNAL_CONTACTS: FrozenSet[str] = frozenset({
    "external.audit@partner-firm.com",
    "legal@lawfirm.example",
})

VENTAS_CONTACTS: FrozenSet[str] = frozenset({
    "sales@ventas.example",
    "support@ventas.example",
})

_ALL_APPROVED = INTERNAL_CONTACTS | EXTERNAL_CONTACTS | VENTAS_CONTACTS


# ---------------------------------------------------------------------- #
# Pure function
# ---------------------------------------------------------------------- #
def is_approved_contact(name_or_email: str) -> bool:
    """
    Case-insensitive substring or exact match against approved lists.
    """
    needle = name_or_email.lower().strip()
    if not needle:
        return False
    return any(
        needle == entry.lower() or needle in entry.lower()
        for entry in _ALL_APPROVED
    )