import pytest
from unittest.mock import patch, MagicMock

from src.cli import CLI, ExecutionContext, ExecutionMode
from src.exceptions import StdinUnavailableError


class TestCLIInput:
    @patch('rich.prompt.Prompt.ask', side_effect=['John', 'Smith', 'Test SMSF'])
    def test_get_director_input_returns_all_fields(self, mock_prompt):
        cli = CLI()
        result = cli.get_director_input()
        assert result['first'] == 'John'
        assert result['last'] == 'Smith'
        assert result['smsf'] == 'Test SMSF'

    @patch('rich.prompt.Prompt.ask', side_effect=['Jane', 'Doe', ''])
    def test_get_director_input_with_optional_empty(self, mock_prompt):
        cli = CLI()
        result = cli.get_director_input()
        assert result['first'] == 'Jane'
        assert result['last'] == 'Doe'
        assert result['smsf'] == ''

    @patch('rich.prompt.Prompt.ask', side_effect=['John', 'Smith', ''])
    def test_get_director_input_with_only_required_fields(self, mock_prompt):
        cli = CLI()
        result = cli.get_director_input()
        assert result['first'] == 'John'
        assert result['last'] == 'Smith'
        assert result['smsf'] == ''

    def test_validate_director_input_with_valid_data(self):
        valid = CLI.validate_director_input('John', 'Smith')
        assert valid is True

    def test_validate_director_input_with_empty_name(self):
        valid = CLI.validate_director_input('', 'Smith')
        assert valid is False

    def test_validate_director_input_with_only_spaces(self):
        valid = CLI.validate_director_input('   ', 'Smith')
        assert valid is False

    @patch('rich.prompt.Confirm.ask', return_value=False)
    def test_prompt_continue_returns_false(self, mock_confirm):
        cli = CLI()
        result = cli.prompt_continue()
        assert result is False

    @patch('rich.prompt.Confirm.ask', return_value=True)
    def test_prompt_continue_returns_true(self, mock_confirm):
        cli = CLI()
        result = cli.prompt_continue()
        assert result is True