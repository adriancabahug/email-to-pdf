import pytest
from src.contacts import (
    INTERNAL_CONTACTS,
    EXTERNAL_CONTACTS,
    VENTAS_CONTACTS,
    is_approved_contact,
)


class TestContactConstants:
    def test_internal_contacts_has_4_entries(self):
        assert len(INTERNAL_CONTACTS) == 4
        assert "Tanesha" in INTERNAL_CONTACTS
        assert "Alyssa" in INTERNAL_CONTACTS
        assert "Grace" in INTERNAL_CONTACTS
        assert "Rachel" in INTERNAL_CONTACTS

    def test_external_contacts_has_6_entries(self):
        assert len(EXTERNAL_CONTACTS) == 6
        assert "ShapeSuper" in EXTERNAL_CONTACTS
        assert "Exceedia" in EXTERNAL_CONTACTS
        assert "CAAA Brisbane" in EXTERNAL_CONTACTS
        assert "Clear Accounting" in EXTERNAL_CONTACTS
        assert "New Wave Law" in EXTERNAL_CONTACTS
        assert "Earlypay" in EXTERNAL_CONTACTS

    def test_ventas_contacts_has_9_entries(self):
        assert len(VENTAS_CONTACTS) == 9
        assert "Steven" in VENTAS_CONTACTS
        assert "Joel" in VENTAS_CONTACTS
        assert "Stefan" in VENTAS_CONTACTS
        assert "Jess" in VENTAS_CONTACTS
        assert "Katy" in VENTAS_CONTACTS
        assert "Patrick" in VENTAS_CONTACTS
        assert "Roland" in VENTAS_CONTACTS
        assert "Kirsty" in VENTAS_CONTACTS
        assert "property@ventasadvisory.com.au" in VENTAS_CONTACTS


class TestIsApprovedContact:
    def test_returns_true_for_internal_contact(self):
        assert is_approved_contact("Tanesha") is True
        assert is_approved_contact("Grace") is True

    def test_returns_true_for_external_contact(self):
        assert is_approved_contact("ShapeSuper") is True
        assert is_approved_contact("Clear Accounting") is True

    def test_returns_true_for_ventas_contact(self):
        assert is_approved_contact("Steven") is True
        assert is_approved_contact("property@ventasadvisory.com.au") is True

    def test_returns_false_for_non_approved(self):
        assert is_approved_contact("Random Person") is False
        assert is_approved_contact("Unknown Corp") is False

    def test_case_insensitive(self):
        assert is_approved_contact("TANESHA") is True
        assert is_approved_contact("tanesha") is True

    def test_substring_match(self):
        assert is_approved_contact("Tanesha Smith") is True
        assert is_approved_contact("ShapeSuper Pty Ltd") is True

    def test_empty_string_returns_false(self):
        assert is_approved_contact("") is False

    def test_whitespace_only_returns_false(self):
        assert is_approved_contact("   ") is False