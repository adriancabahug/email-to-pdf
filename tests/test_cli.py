"""
Tests for unified CLI module (merged StdinGuard + ExecutionMode + InputHandler).
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.cli import CLI, ExecutionContext, ExecutionMode


class TestArgumentParsing:
    def test_batch_mode_from_csv(self, tmp_path: Path):
        csv_file = tmp_path / "dirs.csv"
        csv_file.write_text("smsf,search_terms\nAura Super,term1\n")

        ctx = CLI.resolve(["--batch", str(csv_file)])
        assert ctx.mode == ExecutionMode.BATCH
        assert len(ctx.smsf_entries) == 1
        assert ctx.smsf_entries[0].smsf == "Aura Super"

    def test_interactive_mode_requires_tty(self, monkeypatch):
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        with pytest.raises(SystemExit):
            CLI.resolve([])

    def test_output_dir_default(self, tmp_path: Path):
        csv_file = tmp_path / "x.csv"
        csv_file.write_text("smsf,search_terms\nAura Super,term1\n")
        ctx = CLI.resolve(["--batch", str(csv_file)])
        assert ctx.output_dir is None

    def test_verbose_flag(self, tmp_path: Path):
        csv_file = tmp_path / "x.csv"
        csv_file.write_text("first,last,smsf\nX,Y,Z\n")
        ctx = CLI.resolve(["--batch", str(csv_file), "--verbose"])
        assert ctx.verbose is True


class TestStdinGuard:
    def test_stdin_available_true(self, monkeypatch):
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        assert CLI._stdin_available() is True

    def test_require_stdin_raises_when_not_tty(self, monkeypatch):
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        with pytest.raises(RuntimeError, match="requires an interactive terminal"):
            CLI.require_stdin("test operation")


class TestInputValidation:
    def test_validate_director_input(self):
        assert CLI.validate_director_input("Alice", "Smith") is True
        assert CLI.validate_director_input("", "Smith") is False
        assert CLI.validate_director_input("  ", "Smith") is False

    def test_get_director_input(self, monkeypatch):
        prompts = iter(["Alice", "Smith", "SMSF-001"])
        monkeypatch.setattr("src.cli.Prompt.ask", lambda msg, default="": next(prompts))
        result = CLI().get_director_input()
        assert result == {"first": "Alice", "last": "Smith", "smsf": "SMSF-001"}

    def test_get_director_input_rejects_empty(self, monkeypatch):
        prompts = iter(["", "Smith"])  # first empty, but validation catches before second ask
        monkeypatch.setattr("src.cli.Prompt.ask", lambda msg, default="": next(prompts))
        with pytest.raises(ValueError, match="required"):
            CLI().get_director_input()

    def test_get_smsf_input_multiline_keywords(self, monkeypatch):
        prompts = iter([
            "Aura Super",  # SMSF name
            "andy.studt74@gmail.com\nannaderdowski@uahoo.com\nventas",  # multiline keywords
            "1",  # date range: this year
        ])
        monkeypatch.setattr("src.cli.Prompt.ask", lambda msg, default="": next(prompts))
        result = CLI().get_smsf_input()
        assert result["smsf"] == "Aura Super"
        assert result["search_terms"] == ["andy.studt74@gmail.com", "annaderdowski@uahoo.com", "ventas"]

    def test_get_smsf_input_comma_separated_keywords(self, monkeypatch):
        prompts = iter([
            "Aura Super",
            "andy.studt74@gmail.com,annaderdowski@uahoo.com,ventas",
            "1",
        ])
        monkeypatch.setattr("src.cli.Prompt.ask", lambda msg, default="": next(prompts))
        result = CLI().get_smsf_input()
        assert result["smsf"] == "Aura Super"
        assert result["search_terms"] == ["andy.studt74@gmail.com", "annaderdowski@uahoo.com", "ventas"]

    def test_get_smsf_input_custom_date_range(self, monkeypatch):
        prompts = iter([
            "Aura Super",
            "keyword1",
            "3",  # custom date range
            "2025-01-01",  # start date
            "2025-06-30",  # end date
        ])
        monkeypatch.setattr("src.cli.Prompt.ask", lambda msg, default="": next(prompts))
        result = CLI().get_smsf_input()
        assert result["smsf"] == "Aura Super"
        assert result["search_terms"] == ["keyword1"]
        assert result["start_date"].strftime("%Y-%m-%d") == "2025-01-01"
        assert result["end_date"].strftime("%Y-%m-%d") == "2025-06-30"

    def test_get_smsf_input_rejects_empty_smsf_name(self, monkeypatch):
        prompts = iter(["", "keyword1", "1"])
        monkeypatch.setattr("src.cli.Prompt.ask", lambda msg, default="": next(prompts))
        with pytest.raises(ValueError, match="SMSF name is required"):
            CLI().get_smsf_input()

    def test_get_smsf_input_rejects_empty_keywords(self, monkeypatch):
        prompts = iter(["Aura Super", "", "1"])  # blank keywords
        monkeypatch.setattr("src.cli.Prompt.ask", lambda msg, default="": next(prompts))
        with pytest.raises(ValueError, match="At least one keyword is required"):
            CLI().get_smsf_input()

    def test_prompt_continue(self, monkeypatch):
        monkeypatch.setattr("src.cli.Confirm.ask", lambda msg, default=True: True)
        assert CLI().prompt_continue() is True

        monkeypatch.setattr("src.cli.Confirm.ask", lambda msg, default=True: False)
        assert CLI().prompt_continue() is False


class TestBatchLoading:
    def test_load_json_with_search_terms(self, tmp_path: Path):
        path = tmp_path / "batch.json"
        path.write_text('[{"smsf":"Aura Super","search_terms":"andy.studt74@gmail.com;ventas;exceedia"}]')
        result = CLI._load_batch_file(path)
        assert result[0].smsf == "Aura Super"
        assert result[0].search_terms == ["andy.studt74@gmail.com", "ventas", "exceedia"]

    def test_load_json_with_date_range(self, tmp_path: Path):
        path = tmp_path / "batch.json"
        path.write_text('[{"smsf":"Aura Super","search_terms":"keyword1","start_date":"2025-01-01","end_date":"2025-06-30"}]')
        result = CLI._load_batch_file(path)
        assert result[0].start_date.strftime("%Y-%m-%d") == "2025-01-01"
        assert result[0].end_date.strftime("%Y-%m-%d") == "2025-06-30"

    def test_load_csv_with_search_terms(self, tmp_path: Path):
        path = tmp_path / "batch.csv"
        path.write_text("smsf,search_terms\nAura Super,\"term1;term2;term3\"")
        result = CLI._load_batch_file(path)
        assert result[0].smsf == "Aura Super"
        assert result[0].search_terms == ["term1", "term2", "term3"]

    def test_load_csv_with_date_range(self, tmp_path: Path):
        path = tmp_path / "batch.csv"
        path.write_text("smsf,search_terms,start_date,end_date\nAura Super,term1,2025-01-01,2025-06-30")
        result = CLI._load_batch_file(path)
        assert result[0].start_date.strftime("%Y-%m-%d") == "2025-01-01"
        assert result[0].end_date.strftime("%Y-%m-%d") == "2025-06-30"

    def test_load_csv_defaults_to_all_time(self, tmp_path: Path):
        path = tmp_path / "batch.csv"
        path.write_text("smsf,search_terms\nAura Super,term1")
        result = CLI._load_batch_file(path)
        assert result[0].start_date is None
        assert result[0].end_date is None

    def test_load_unsupported_format(self, tmp_path: Path):
        path = tmp_path / "batch.txt"
        path.write_text("x")
        with pytest.raises(ValueError, match="Unsupported"):
            CLI._load_batch_file(path)