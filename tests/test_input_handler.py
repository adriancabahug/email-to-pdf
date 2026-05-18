import pytest
from unittest.mock import patch
from src.cli import InputHandler, ExecutionContext, ExecutionMode
from src.exceptions import StdinUnavailableError


class TestInputHandler:
    @patch('src.cli.require_stdin')
    @patch('builtins.input', side_effect=['John', 'Smith', 'Test SMSF', 'john@test.com'])
    def test_get_director_input_returns_all_fields(self, mock_input, mock_require):
        handler = InputHandler()
        result = handler.get_director_input()
        assert result['first_name'] == 'John'
        assert result['last_name'] == 'Smith'
        assert result['smsf_name'] == 'Test SMSF'
        assert result['email'] == 'john@test.com'

    @patch('src.cli.require_stdin')
    @patch('builtins.input', side_effect=['Jane', 'Doe', '', ''])
    def test_get_director_input_with_optional_fields_empty(self, mock_input, mock_require):
        handler = InputHandler()
        result = handler.get_director_input()
        assert result['first_name'] == 'Jane'
        assert result['last_name'] == 'Doe'
        assert result['smsf_name'] == ''
        assert result['email'] == ''

    @patch('src.cli.require_stdin')
    @patch('builtins.input', side_effect=['John', 'Smith', '', ''])
    def test_get_director_input_with_only_required_fields(self, mock_input, mock_require):
        handler = InputHandler()
        result = handler.get_director_input()
        assert result['first_name'] == 'John'
        assert result['last_name'] == 'Smith'
        assert result['smsf_name'] == ''
        assert result['email'] == ''

    def test_validate_director_input_with_valid_data(self):
        handler = InputHandler()
        valid = handler.validate_director_input('John', 'Smith')
        assert valid is True

    def test_validate_director_input_with_empty_name(self):
        handler = InputHandler()
        valid = handler.validate_director_input('', 'Smith')
        assert valid is False

    def test_validate_director_input_with_only_spaces(self):
        handler = InputHandler()
        valid = handler.validate_director_input('   ', 'Smith')
        assert valid is False

    def test_get_director_input_raises_stdin_unavailable(self):
        handler = InputHandler()
        with patch('src.cli.stdin_available', return_value=False):
            with pytest.raises(StdinUnavailableError) as exc_info:
                handler.get_director_input()
            assert "prompt" in str(exc_info.value)
            assert "--interactive" in str(exc_info.value)

    def test_prompt_continue_raises_stdin_unavailable(self):
        handler = InputHandler()
        with patch('src.cli.stdin_available', return_value=False):
            with pytest.raises(StdinUnavailableError) as exc_info:
                handler.prompt_continue()
            assert "continue prompt" in str(exc_info.value)
            assert "--interactive" in str(exc_info.value)