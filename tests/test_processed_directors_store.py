"""
Tests for decoupled ProcessedDirectorsStore (Path-based constructor).
"""

from pathlib import Path

import pytest

from src.processed_directors_store import ProcessedDirectorsStore


@pytest.fixture
def store(tmp_path: Path) -> ProcessedDirectorsStore:
    return ProcessedDirectorsStore(storage_path=tmp_path / "processed.json")


class TestIsProcessed:
    def test_empty_store(self, store: ProcessedDirectorsStore):
        assert not store.is_processed("Alice Smith")

    def test_exact_match(self, store: ProcessedDirectorsStore):
        store.mark_processed("Alice Smith")
        assert store.is_processed("Alice Smith")

    def test_case_insensitive(self, store: ProcessedDirectorsStore):
        store.mark_processed("Alice Smith")
        assert store.is_processed("alice smith")
        assert store.is_processed("ALICE SMITH")

    def test_whitespace_stripping(self, store: ProcessedDirectorsStore):
        store.mark_processed("Alice Smith")
        assert store.is_processed("  Alice Smith  ")


class TestPersistence:
    def test_mark_processed_creates_file(self, store: ProcessedDirectorsStore, tmp_path: Path):
        store.mark_processed("Bob")
        assert (tmp_path / "processed.json").exists()

    def test_load_recovers_state(self, tmp_path: Path):
        path = tmp_path / "processed.json"
        path.write_text('["alice smith"]')
        store = ProcessedDirectorsStore(path)
        assert store.is_processed("Alice Smith")

    def test_reset_clears_and_deletes(self, store: ProcessedDirectorsStore, tmp_path: Path):
        store.mark_processed("Bob")
        store.reset()
        assert not store.is_processed("Bob")
        assert not (tmp_path / "processed.json").exists()


class TestAtomicWrite:
    def test_no_temp_file_left_behind(self, store: ProcessedDirectorsStore, tmp_path: Path):
        store.mark_processed("Charlie")
        assert not (tmp_path / "processed.tmp").exists()