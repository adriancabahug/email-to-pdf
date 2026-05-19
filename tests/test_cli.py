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
        csv_file.write_text("first,last,smsf\nAlice,Smith,SMSF001\n")

        ctx = CLI.resolve(["--batch", str(csv_file)])
        assert ctx.mode == ExecutionMode.BATCH
        assert len(ctx.directors) == 1
        assert ctx.directors[0]["first"] == "Alice"

    def test_interactive_mode_requires_tty(self, monkeypatch):
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        with pytest.raises(SystemExit):
            CLI.resolve([])

    def test_output_dir_default(self, tmp_path: Path):
        csv_file = tmp_path / "x.csv"
        csv_file.write_text("first,last,smsf\nX,Y,Z\n")
        ctx = CLI.resolve(["--batch", str(csv_file)])
        assert ctx.output_dir == Path(".").resolve()

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

    def test_prompt_continue(self, monkeypatch):
        monkeypatch.setattr("src.cli.Confirm.ask", lambda msg, default=True: True)
        assert CLI().prompt_continue() is True

        monkeypatch.setattr("src.cli.Confirm.ask", lambda msg, default=True: False)
        assert CLI().prompt_continue() is False


class TestBatchLoading:
    def test_load_json(self, tmp_path: Path):
        path = tmp_path / "batch.json"
        path.write_text('[{"first":"A","last":"B","smsf":"1"}]')
        result = CLI._load_batch_file(path)
        assert result[0]["first"] == "A"

    def test_load_unsupported_format(self, tmp_path: Path):
        path = tmp_path / "batch.txt"
        path.write_text("x")
        with pytest.raises(ValueError, match="Unsupported"):
            CLI._load_batch_file(path)