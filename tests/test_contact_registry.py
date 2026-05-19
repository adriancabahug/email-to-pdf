import pytest
from src.contacts import (
    INTERNAL_CONTACTS,
    EXTERNAL_CONTACTS,
    VENTAS_CONTACTS,
    is_approved_contact,
)


class TestContactConstants:
    def test_internal_contacts_has_3_entries(self):
        assert len(INTERNAL_CONTACTS) == 3
        assert "alice.smith@company.com" in INTERNAL_CONTACTS
        assert "bob.jones@company.com" in INTERNAL_CONTACTS
        assert "charlie.brown@company.com" in INTERNAL_CONTACTS

    def test_external_contacts_has_2_entries(self):
        assert len(EXTERNAL_CONTACTS) == 2
        assert "external.audit@partner-firm.com" in EXTERNAL_CONTACTS
        assert "legal@lawfirm.example" in EXTERNAL_CONTACTS

    def test_ventas_contacts_has_2_entries(self):
        assert len(VENTAS_CONTACTS) == 2
        assert "sales@ventas.example" in VENTAS_CONTACTS
        assert "support@ventas.example" in VENTAS_CONTACTS


class TestIsApprovedContact:
    def test_returns_true_for_internal_contact(self):
        assert is_approved_contact("alice.smith@company.com") is True
        assert is_approved_contact("bob.jones@company.com") is True

    def test_returns_true_for_external_contact(self):
        assert is_approved_contact("external.audit@partner-firm.com") is True
        assert is_approved_contact("legal@lawfirm.example") is True

    def test_returns_true_for_ventas_contact(self):
        assert is_approved_contact("sales@ventas.example") is True
        assert is_approved_contact("support@ventas.example") is True

    def test_returns_false_for_non_approved(self):
        assert is_approved_contact("Random Person") is False
        assert is_approved_contact("Unknown Corp") is False

    def test_case_insensitive(self):
        assert is_approved_contact("ALICE.SMITH@COMPANY.COM") is True
        assert is_approved_contact("alice.smith@company.com") is True

    def test_substring_match(self):
        assert is_approved_contact("alice.smith") is True
        assert is_approved_contact("external.audit") is True

    def test_empty_string_returns_false(self):
        assert is_approved_contact("") is False

    def test_whitespace_only_returns_false(self):
        assert is_approved_contact("   ") is False