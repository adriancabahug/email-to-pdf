"""
Tests for Batch Processor.
"""

import json
from datetime import datetime
from pathlib import Path
import tempfile

import pytest

from src.batch_processor import BatchProcessor, BatchResult, BatchLoadError


class TestBatchLoading:
    def test_load_from_json_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "smsfs": [
                    {
                        "smsf_name": "Test Fund 1",
                        "director_names": ["Director 1"],
                        "director_emails": ["dir1@test.com"],
                        "advisor_domains": ["advisor1.com"],
                        "timeframe": "current_year"
                    },
                    {
                        "smsf_name": "Test Fund 2",
                        "director_names": ["Director 2"],
                        "director_emails": [],
                        "advisor_domains": [],
                    }
                ]
            }, f)
            path = Path(f.name)

        try:
            processor = BatchProcessor()
            contexts = processor.load_batch_input(path)

            assert len(contexts) == 2
            assert contexts[0].smsf_name == "Test Fund 1"
            assert contexts[1].smsf_name == "Test Fund 2"
        finally:
            path.unlink(missing_ok=True)

    def test_load_empty_smsfs_list(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"smsfs": []}, f)
            path = Path(f.name)

        try:
            processor = BatchProcessor()
            contexts = processor.load_batch_input(path)

            assert len(contexts) == 0
        finally:
            path.unlink(missing_ok=True)

    def test_load_missing_file_raises(self):
        processor = BatchProcessor()

        with pytest.raises(BatchLoadError):
            processor.load_batch_input(Path("nonexistent.json"))

    def test_load_invalid_json_raises(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json")
            path = Path(f.name)

        try:
            processor = BatchProcessor()
            with pytest.raises(BatchLoadError):
                processor.load_batch_input(path)
        finally:
            path.unlink(missing_ok=True)

    def test_load_missing_smsfs_key_raises(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"other": "data"}, f)
            path = Path(f.name)

        try:
            processor = BatchProcessor()
            with pytest.raises(BatchLoadError):
                processor.load_batch_input(path)
        finally:
            path.unlink(missing_ok=True)


class TestBatchResult:
    def test_batch_result_initializes_correctly(self):
        result = BatchResult(
            total=5,
            succeeded=3,
            failed=2,
            pdfs_generated=[Path("a.pdf"), Path("b.pdf")],
            errors=["error1", "error2"]
        )

        assert result.total == 5
        assert result.succeeded == 3
        assert result.failed == 2
        assert len(result.pdfs_generated) == 2
        assert len(result.errors) == 2

    def test_batch_result_str_representation(self):
        result = BatchResult(
            total=5,
            succeeded=3,
            failed=2,
            pdfs_generated=[],
            errors=["error1"]
        )

        result_str = str(result)
        assert "5" in result_str
        assert "3" in result_str
        assert "2" in result_str


class TestBatchProcessing:
    def test_process_batch_empty_list(self):
        processor = BatchProcessor()
        result = processor.process_batch([])

        assert result.total == 0
        assert result.succeeded == 0
        assert result.failed == 0

    def test_process_batch_continues_on_failure(self):
        from src.smsf_context import SMSFContext

        processor = BatchProcessor()

        contexts = [
            SMSFContext(
                smsf_name="Fund 1",
                director_names=["Dir"],
                director_emails=["dir@test.com"],
                advisor_domains=["test.com"],
            ),
            SMSFContext(
                smsf_name="Fund 2",
                director_names=["Dir"],
                director_emails=["dir@test.com"],
                advisor_domains=["test.com"],
            ),
        ]

        result = processor.process_batch(contexts)

        assert result.total == 2