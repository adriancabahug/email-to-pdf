"""
Tests for flattened contacts module (pure function + constants).
"""

from src.contacts import (
    EXTERNAL_CONTACTS,
    INTERNAL_CONTACTS,
    VENTAS_CONTACTS,
    is_approved_contact,
)


class TestIsApprovedContact:
    def test_exact_email_match(self):
        assert is_approved_contact("alice.smith@company.com") is True

    def test_case_insensitive(self):
        assert is_approved_contact("ALICE.SMITH@COMPANY.COM") is True

    def test_substring_match(self):
        assert is_approved_contact("smith@company") is True

    def test_unapproved(self):
        assert is_approved_contact("hacker@evil.com") is False

    def test_empty_string(self):
        assert is_approved_contact("") is False
        assert is_approved_contact("   ") is False

    def test_ventas_included(self):
        assert is_approved_contact("sales@ventas.example") is True


class TestConstants:
    def test_no_overlap_between_sets(self):
        assert not (INTERNAL_CONTACTS & EXTERNAL_CONTACTS)
        assert not (INTERNAL_CONTACTS & VENTAS_CONTACTS)
        assert not (EXTERNAL_CONTACTS & VENTAS_CONTACTS)