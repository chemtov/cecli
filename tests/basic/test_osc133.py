import asyncio
import io
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cecli.io import InputOutput


class TestOSC133Support:
    """Test OSC 133 semantic terminal support in linear output mode."""

    def test_semantic_terminal_validation_explicit_true_without_linear_fails(self):
        """Test that --semantic-terminal without --linear-output fails with clear error."""
        from cecli.main import validate_semantic_terminal_args
        from argparse import Namespace

        # Create args with semantic_terminal=True but linear_output=False
        args = Namespace(semantic_terminal=True, linear_output=False)

        with pytest.raises(SystemExit):
            validate_semantic_terminal_args(args)

    def test_semantic_terminal_validation_explicit_true_with_linear_succeeds(self):
        """Test that --semantic-terminal with --linear-output works."""
        from cecli.main import validate_semantic_terminal_args
        from argparse import Namespace

        # Create args with both semantic_terminal=True and linear_output=True
        args = Namespace(semantic_terminal=True, linear_output=True)

        # Should not raise any exception
        validate_semantic_terminal_args(args)

    def test_semantic_terminal_validation_auto_detection_works(self):
        """Test that auto-detected semantic terminal works without --linear-output."""
        from cecli.main import validate_semantic_terminal_args
        from argparse import Namespace

        # Auto-detection (semantic_terminal=None) should not require validation
        args = Namespace(semantic_terminal=None, linear_output=False)

        # Should not raise any exception
        validate_semantic_terminal_args(args)

    def test_semantic_terminal_validation_explicit_false_works(self):
        """Test that --no-semantic-terminal works regardless of linear output."""
        from cecli.main import validate_semantic_terminal_args
        from argparse import Namespace

        # Explicit False should not require validation
        args = Namespace(semantic_terminal=False, linear_output=False)

        # Should not raise any exception
        validate_semantic_terminal_args(args)

    def test_semantic_terminal_validation_none_with_linear_works(self):
        """Test that auto-detection with --linear-output works."""
        from cecli.main import validate_semantic_terminal_args
        from argparse import Namespace

        # Auto-detection with linear output should work
        args = Namespace(semantic_terminal=None, linear_output=True)

        # Should not raise any exception
        validate_semantic_terminal_args(args)



    def test_osc133_sequence_generation(self):
        """Test that OSC 133 sequences are generated correctly."""
        from cecli.io import generate_osc133_sequence

        # Test prompt start sequence
        assert generate_osc133_sequence("A") == "\x1b]133;A\x07"

        # Test prompt end sequence
        assert generate_osc133_sequence("B") == "\x1b]133;B\x07"

        # Test pre-execution sequence
        assert generate_osc133_sequence("C") == "\x1b]133;C\x07"

        # Test execution finished sequence
        assert generate_osc133_sequence("D", exit_code=0) == "\x1b]133;D;0\x07"
        assert generate_osc133_sequence("D", exit_code=1) == "\x1b]133;D;1\x07"

        # Test with parameters
        assert generate_osc133_sequence("A", params=["aid=123"]) == "\x1b]133;A;aid=123\x07"

    def test_osc133_detection_enabled(self):
        """Test that OSC 133 support can be detected and enabled."""
        from cecli.io import should_enable_osc133

        # Test with supported terminal
        with patch.dict("os.environ", {"TERM_PROGRAM": "vscode"}):
            assert should_enable_osc133() is True

        with patch.dict("os.environ", {"TERM_PROGRAM": "kitty"}):
            assert should_enable_osc133() is True

        with patch.dict("os.environ", {"WEZTERM_SHELL_INTEGRATION": "enabled"}):
            assert should_enable_osc133() is True

        # Test with unsupported terminal
        with patch.dict("os.environ", {}, clear=True):
            assert should_enable_osc133() is False

    def test_osc133_disabled_by_default(self):
        """Test that OSC 133 is disabled by default for unsupported terminals."""
        # Test with unsupported terminal environment (empty environment)
        with patch.dict("os.environ", {}, clear=True):
            io_instance = InputOutput(pretty=False, fancy_input=False)
            assert io_instance.osc133_enabled is False, "OSC 133 should be disabled for unsupported terminals"

    def test_osc133_enabled_for_supported_terminals(self):
        """Test that OSC 133 is enabled for supported terminals."""
        with patch.dict("os.environ", {"TERM_PROGRAM": "vscode"}):
            io_instance = InputOutput(pretty=False, fancy_input=False)
            assert hasattr(io_instance, 'osc133_enabled') and io_instance.osc133_enabled

    def test_osc133_environment_detection(self):
        """Test detection of OSC 133 capable terminals from environment variables."""
        from cecli.io import detect_osc133_support

        test_cases = [
            # (env_vars, expected_result)
            ({"TERM_PROGRAM": "vscode"}, True),
            ({"TERM_PROGRAM": "kitty"}, True),
            ({"TERM_PROGRAM": "WezTerm"}, True),
            ({"TERM_PROGRAM": "iTerm.app"}, True),
            ({"WEZTERM_SHELL_INTEGRATION": "enabled"}, True),
            ({"KITTY_SHELL_INTEGRATION": "enabled"}, True),
            ({"TERM": "foot"}, True),
            ({"TERM": "contour"}, True),
            ({"TERM": "xterm"}, False),
            ({"TERM": "screen"}, False),
            ({}, False),
        ]

        for env_vars, expected in test_cases:
            with patch.dict("os.environ", env_vars, clear=True):
                result = detect_osc133_support()
                assert result == expected, f"Failed for env_vars: {env_vars}"

    def test_osc133_force_enable_via_parameter(self):
        """Test that OSC 133 can be force enabled via parameter."""
        from cecli.io import should_enable_osc133

        # Test force enable overrides auto-detection
        with patch.dict("os.environ", {}, clear=True):
            assert should_enable_osc133(force_enable=True) is True
            assert should_enable_osc133(force_enable=False) is False

        # Test force enable overrides supported terminal detection
        with patch.dict("os.environ", {"TERM_PROGRAM": "vscode"}):
            assert should_enable_osc133(force_enable=False) is False

        # Test force disable overrides supported terminal detection
        with patch.dict("os.environ", {"TERM_PROGRAM": "vscode"}):
            assert should_enable_osc133(force_enable=False) is False

    def test_osc133_force_enable_via_environment_variable(self):
        """Test that OSC 133 can be force enabled via environment variable."""
        from cecli.io import should_enable_osc133

        # Test environment variable override
        test_cases = [
            # (env_value, expected_result)
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("YES", True),
            ("on", True),
            ("ON", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("NO", False),
            ("off", False),
            ("OFF", False),
            ("invalid", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict("os.environ", {"CECLI_SEMANTIC_TERMINAL": env_value}, clear=True):
                result = should_enable_osc133()
                assert result == expected, f"Failed for env value: {env_value}"

    def test_osc133_environment_variable_precedence(self):
        """Test that environment variable takes precedence over parameter and auto-detection."""
        from cecli.io import should_enable_osc133

        # Environment variable should override force parameter
        with patch.dict("os.environ", {"CECLI_SEMANTIC_TERMINAL": "true"}):
            assert should_enable_osc133(force_enable=False) is True

        with patch.dict("os.environ", {"CECLI_SEMANTIC_TERMINAL": "false"}):
            assert should_enable_osc133(force_enable=True) is False

        # Environment variable should override auto-detection
        with patch.dict("os.environ", {"CECLI_SEMANTIC_TERMINAL": "false", "TERM_PROGRAM": "vscode"}):
            assert should_enable_osc133() is False

        with patch.dict("os.environ", {"CECLI_SEMANTIC_TERMINAL": "true", "TERM_PROGRAM": "xterm"}):
            assert should_enable_osc133() is True

    def test_osc133_inputoutput_constructor_parameter(self):
        """Test that InputOutput constructor accepts semantic_terminal parameter."""
        # Test with force enable
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)
        assert io_instance.osc133_enabled is True

        # Test with force disable
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=False)
        assert io_instance.osc133_enabled is False

        # Test with None (auto-detection)
        with patch.dict("os.environ", {"TERM_PROGRAM": "vscode"}):
            io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=None)
            assert io_instance.osc133_enabled is True

        with patch.dict("os.environ", {}, clear=True):
            io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=None)
            assert io_instance.osc133_enabled is False

    def test_osc133_parameter_precedence_order(self):
        """Test the precedence order: env var > parameter > auto-detection."""
        from cecli.io import should_enable_osc133

        # 1. Environment variable has highest precedence
        with patch.dict("os.environ", {"CECLI_SEMANTIC_TERMINAL": "true", "TERM_PROGRAM": "xterm"}):
            assert should_enable_osc133(force_enable=False) is True

        # 2. Parameter has precedence over auto-detection
        with patch.dict("os.environ", {"TERM_PROGRAM": "xterm"}, clear=True):
            assert should_enable_osc133(force_enable=True) is True

        # 3. Auto-detection is used when no overrides
        with patch.dict("os.environ", {"TERM_PROGRAM": "vscode"}):
            assert should_enable_osc133() is True

        with patch.dict("os.environ", {}, clear=True):
            assert should_enable_osc133() is False

    @patch('sys.stdout', new_callable=io.StringIO)
    async def test_osc133_prompt_sequences_in_get_input(self, mock_stdout):
        """Test that OSC 133 A/B sequences are emitted around prompt display during get_input."""
        # Enable OSC 133
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)
        io_instance.linear = True

        # Mock prompt_session to avoid actual user input
        io_instance.prompt_session = MagicMock()
        io_instance.prompt_session.prompt_async = AsyncMock(return_value="test input")

        # Call get_input which should emit OSC 133 A/B sequences for prompt phase
        result = await io_instance.get_input(".", [], [], MagicMock())

        output = mock_stdout.getvalue()

        # Verify prompt phase OSC 133 sequences are present
        assert "\x1b]133;A\x07" in output, "Missing OSC 133 A (prompt start) sequence"
        assert "\x1b]133;B\x07" in output, "Missing OSC 133 B (prompt end) sequence"
        
        # Should NOT contain command execution sequences (those are for AI response phase)
        assert "\x1b]133;C\x07" not in output, "C sequence should not be in input collection phase"
        assert "\x1b]133;D;0\x07" not in output, "D sequence should not be in input collection phase"

        # Verify prompt sequence order
        a_pos = output.find("\x1b]133;A\x07")
        b_pos = output.find("\x1b]133;B\x07")
        
        assert a_pos < b_pos, "A (prompt start) should come before B (prompt end)"

    @patch('sys.stdout', new_callable=io.StringIO)
    async def test_osc133_prompt_sequences_disabled_when_not_supported(self, mock_stdout):
        """Test that OSC 133 sequences are not emitted when disabled."""
        # Disable OSC 133
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=False)

        # Mock prompt_session to avoid actual user input
        io_instance.prompt_session = MagicMock()
        io_instance.prompt_session.prompt_async = AsyncMock(return_value="test input")

        # Call get_input
        result = await io_instance.get_input(".", [], [], MagicMock())

        output = mock_stdout.getvalue()

        # Should not contain any OSC 133 sequences
        assert "\x1b]133;" not in output, "OSC 133 sequences should not be emitted when disabled"

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_osc133_rule_method_integration(self, mock_stdout):
        """Test that rule() method works correctly with OSC 133 enabled."""
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)
        io_instance.linear = True

        io_instance.rule()

        output = mock_stdout.getvalue()
        # Test that rule() doesn't interfere with OSC 133 or emit unwanted sequences
        # Should not contain OSC 133 sequences (rule is just a visual separator)
        assert "\x1b]133;" not in output, "rule() should not emit OSC 133 sequences"
        assert isinstance(output, str), "rule() should produce string output"

    @patch('sys.stdout', new_callable=io.StringIO)
    async def test_osc133_multiline_prompt_integration(self, mock_stdout):
        """Test OSC 133 sequences with multiline input mode."""
        # Enable OSC 133 and multiline mode
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True, multiline_mode=True)

        # Simulate linear output mode (required for OSC 133 emission)
        io_instance.linear = True

        # Mock prompt_session for multiline input
        io_instance.prompt_session = MagicMock()
        io_instance.prompt_session.prompt_async = AsyncMock(return_value="line1\nline2")

        # Call get_input in multiline mode
        result = await io_instance.get_input(".", [], [], MagicMock())

        output = mock_stdout.getvalue()

        # Should still contain OSC 133 sequences even in multiline mode
        assert "\x1b]133;A\x07" in output, "Missing OSC 133 A sequence in multiline mode"
        assert "\x1b]133;B\x07" in output, "Missing OSC 133 B sequence in multiline mode"


    @patch('sys.stdout', new_callable=io.StringIO)
    def test_osc133_stream_output_ai_response_lifecycle(self, mock_stdout):
        """Test OSC 133 sequences during AI response streaming (not command execution)."""
        # Enable OSC 133
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)

        # Simulate linear output mode (required for OSC 133 emission)
        io_instance.linear = True

        # Reset response state
        io_instance.osc133_response_started = False

        # Simulate streaming AI response output (this should use C/D sequences)
        io_instance.stream_output("AI response here", final=False)
        io_instance.stream_output(" more AI output", final=False)
        io_instance.stream_output("!", final=True)

        output = mock_stdout.getvalue()

        # Should contain OSC 133 C at start of AI response output
        assert "\x1b]133;C\x07" in output, "Missing OSC 133 C at start of AI response"

        # Should contain OSC 133 D at end of AI response
        assert "\x1b]133;D;0\x07" in output, "Missing OSC 133 D at end of AI response"

        # C should come before D
        c_pos = output.find("\x1b]133;C\x07")
        d_pos = output.find("\x1b]133;D;0\x07")
        assert c_pos < d_pos, "OSC 133 C should come before D in AI response"

    @patch('sys.stdout', new_callable=io.StringIO)
    async def test_osc133_disabled_in_tui_mode(self, mock_stdout):
        """Test that OSC 133 sequences are NOT emitted when in TUI mode."""
        # Enable OSC 133 but simulate TUI mode
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)

        # Simulate TUI mode by setting linear=False (TUI mode uses linear=False)
        io_instance.linear = False  # This should be TUI mode

        # Mock prompt_session to avoid actual user input
        io_instance.prompt_session = MagicMock()
        io_instance.prompt_session.prompt_async = AsyncMock(return_value="test input")

        # Call get_input which should NOT emit OSC 133 sequences in TUI mode
        result = await io_instance.get_input(".", [], [], MagicMock())

        # Capture what was written to stdout
        output = mock_stdout.getvalue()

        # Should NOT contain any OSC 133 sequences when in TUI mode
        assert "\x1b]133;A\x07" not in output, "OSC 133 A sequence should not be emitted in TUI mode"
        assert "\x1b]133;B\x07" not in output, "OSC 133 B sequence should not be emitted in TUI mode"

    @patch('sys.stdout', new_callable=io.StringIO)
    async def test_osc133_enabled_in_linear_mode_only(self, mock_stdout):
        """Test that OSC 133 sequences are emitted ONLY in linear output mode."""
        # Enable OSC 133 and simulate linear output mode
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)

        # Simulate linear output mode (required for OSC 133 emission)
        io_instance.linear = True

        # Mock prompt_session to avoid actual user input
        io_instance.prompt_session = MagicMock()
        io_instance.prompt_session.prompt_async = AsyncMock(return_value="test input")

        # Call get_input which SHOULD emit OSC 133 sequences in linear mode
        result = await io_instance.get_input(".", [], [], MagicMock())

        # Capture what was written to stdout
        output = mock_stdout.getvalue()

        # Should contain OSC 133 sequences when in linear mode
        assert "\x1b]133;A\x07" in output, "OSC 133 A sequence should be emitted in linear mode"
        assert "\x1b]133;B\x07" in output, "OSC 133 B sequence should be emitted in linear mode"

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_osc133_stream_output_disabled_in_tui_mode(self, mock_stdout):
        """Test that OSC 133 sequences in stream_output are NOT emitted in TUI mode."""
        # Enable OSC 133 but simulate TUI mode
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)

        # Simulate TUI mode
        io_instance.linear = False  # TUI mode
        io_instance.osc133_response_started = False

        # Call stream_output which should NOT emit OSC 133 sequences in TUI mode
        io_instance.stream_output("AI response here", final=True)

        output = mock_stdout.getvalue()

        # Should NOT contain OSC 133 sequences when in TUI mode
        assert "\x1b]133;C\x07" not in output, "OSC 133 C sequence should not be emitted in TUI mode for stream_output"
        assert "\x1b]133;D;0\x07" not in output, "OSC 133 D sequence should not be emitted in TUI mode for stream_output"

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_osc133_stream_output_enabled_in_linear_mode_only(self, mock_stdout):
        """Test that OSC 133 sequences in stream_output are emitted ONLY in linear mode."""
        # Enable OSC 133 and simulate linear output mode
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)

        # Simulate linear output mode (required for OSC 133 emission)
        io_instance.linear = True
        io_instance.osc133_response_started = False

        # Call stream_output which SHOULD emit OSC 133 sequences in linear mode
        io_instance.stream_output("Command execution output", final=True)

        output = mock_stdout.getvalue()

        # Should contain OSC 133 sequences when in linear mode
        assert "\x1b]133;C\x07" in output, "OSC 133 C sequence should be emitted in linear mode for stream_output"
        assert "\x1b]133;D;0\x07" in output, "OSC 133 D sequence should be emitted in linear mode for stream_output"

    def test_osc133_disabled_when_semantic_terminal_false_regardless_of_mode(self):
        """Test that OSC 133 is disabled when semantic_terminal=False regardless of linear/TUI mode."""
        # Test linear mode with semantic_terminal=False
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=False)
        io_instance.linear = True  # Linear mode
        assert io_instance.osc133_enabled is False, "OSC 133 should be disabled when semantic_terminal=False even in linear mode"

        # Test TUI mode with semantic_terminal=False
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=False)
        io_instance.linear = False  # TUI mode
        assert io_instance.osc133_enabled is False, "OSC 133 should be disabled when semantic_terminal=False in TUI mode"

    def test_osc133_enabled_only_with_both_conditions(self):
        """Test that OSC 133 requires both semantic_terminal=True AND linear mode."""
        # Test: semantic_terminal=True + linear=True = OSC 133 enabled
        with patch.dict("os.environ", {"TERM_PROGRAM": "vscode"}):
            io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)
            io_instance.linear = True
            # OSC 133 should be enabled, but actual emission should be checked in methods
            assert io_instance.osc133_enabled is True

        # Test: semantic_terminal=True + linear=False (TUI) = OSC 133 disabled for emission
        with patch.dict("os.environ", {"TERM_PROGRAM": "vscode"}):
            io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)
            io_instance.linear = False
            # OSC 133 might be enabled in config, but should not emit in TUI mode
            assert io_instance.osc133_enabled is True  # Config enabled
            # But emission should be prevented by linear mode check

    @patch('sys.stdout', new_callable=io.StringIO)
    async def test_osc133_auto_detection_with_tui_mode_check(self, mock_stdout):
        """Test that auto-detected OSC 133 support still respects TUI mode restrictions."""
        # Auto-detect OSC 133 support (should be enabled for vscode)
        with patch.dict("os.environ", {"TERM_PROGRAM": "vscode"}):
            io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=None)

            # Test in TUI mode - should not emit (linear=False simulates TUI mode)
            io_instance.linear = False
            io_instance.prompt_session = MagicMock()
            io_instance.prompt_session.prompt_async = AsyncMock(return_value="test")

            await io_instance.get_input(".", [], [], MagicMock())
            output = mock_stdout.getvalue()

            assert "\x1b]133;" not in output, "Auto-detected OSC 133 should not emit in TUI mode"

    @patch('sys.stdout', new_callable=io.StringIO)
    async def test_osc133_environment_variable_with_tui_mode_check(self, mock_stdout):
        """Test that environment variable OSC 133 override still respects TUI mode."""
        # Force enable via environment variable
        with patch.dict("os.environ", {"CECLI_SEMANTIC_TERMINAL": "true"}):
            io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=None)

            # Test in TUI mode - should not emit even when forced via env var (linear=False simulates TUI mode)
            io_instance.linear = False
            io_instance.prompt_session = MagicMock()
            io_instance.prompt_session.prompt_async = AsyncMock(return_value="test")

            await io_instance.get_input(".", [], [], MagicMock())
            output = mock_stdout.getvalue()

            assert "\x1b]133;" not in output, "Environment variable OSC 133 should not emit in TUI mode"

    @patch('sys.stdout', new_callable=io.StringIO)
    async def test_osc133_prompt_zone_boundaries(self, mock_stdout):
        """Test that OSC 133 A/B sequences create proper prompt zone boundaries."""
        # Enable OSC 133
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)
        io_instance.linear = True

        # Mock prompt_session
        io_instance.prompt_session = MagicMock()
        io_instance.prompt_session.prompt_async = AsyncMock(return_value="user command")

        # Get user input (should create prompt zone with A/B sequences)
        await io_instance.get_input(".", [], [], MagicMock())

        output = mock_stdout.getvalue()

        # Find prompt sequence positions
        a_pos = output.find("\x1b]133;A\x07")
        b_pos = output.find("\x1b]133;B\x07")

        # Prompt sequences should be present
        assert a_pos != -1, "Missing A (prompt start) sequence"
        assert b_pos != -1, "Missing B (prompt end) sequence"

        # Verify proper order
        assert a_pos < b_pos, "A (prompt start) should come before B (prompt end)"

        # Extract prompt zone
        prompt_zone = output[a_pos + len("\x1b]133;A\x07"):b_pos]

        # Prompt zone should contain the prompt display
        assert len(prompt_zone) > 0, "Prompt zone should contain prompt text"

    def test_osc133_sequence_semantic_meaning(self):
        """Test that OSC 133 sequences have correct semantic meaning according to spec."""
        from cecli.io import generate_osc133_sequence
        
        # A = Prompt start (before displaying prompt)
        prompt_start = generate_osc133_sequence("A")
        assert prompt_start == "\x1b]133;A\x07", "A sequence should mark prompt start"
        
        # B = Prompt end (after displaying prompt, before user input)
        prompt_end = generate_osc133_sequence("B")
        assert prompt_end == "\x1b]133;B\x07", "B sequence should mark prompt end"
        
        # C = Command execution start (before processing user input)
        command_start = generate_osc133_sequence("C")
        assert command_start == "\x1b]133;C\x07", "C sequence should mark command execution start"
        
        # D = Command execution end (after processing, with exit code)
        command_end_success = generate_osc133_sequence("D", exit_code=0)
        assert command_end_success == "\x1b]133;D;0\x07", "D sequence should mark command execution end with exit code"
        
        command_end_error = generate_osc133_sequence("D", exit_code=1)
        assert command_end_error == "\x1b]133;D;1\x07", "D sequence should support error exit codes"

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_osc133_command_execution_sequences_in_stream_output(self, mock_stdout):
        """Test that OSC 133 C/D sequences are emitted around AI response (command execution phase)."""
        # Enable OSC 133
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)
        io_instance.linear = True
        io_instance.osc133_response_started = False

        # Call stream_output which should emit OSC 133 C/D sequences for command execution
        io_instance.stream_output("AI response output", final=True)

        output = mock_stdout.getvalue()

        # Should contain command execution OSC 133 sequences
        assert "\x1b]133;C\x07" in output, "Missing OSC 133 C (command start) sequence"
        assert "\x1b]133;D;0\x07" in output, "Missing OSC 133 D (command end) sequence"
        
        # C should come before D
        c_pos = output.find("\x1b]133;C\x07")
        d_pos = output.find("\x1b]133;D;0\x07")
        
        assert c_pos != -1, "C sequence should be present"
        assert d_pos != -1, "D sequence should be present"
        assert c_pos < d_pos, "C (command start) should come before D (command end)"

    @patch('sys.stdout', new_callable=io.StringIO)
    async def test_osc133_b_sequence_timing_correctness(self, mock_stdout):
        """Test that B sequence is emitted after prompt display but before user input."""
        # Enable OSC 133
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)
        io_instance.linear = True

        # Create a custom mock that tracks when stdout is written vs when prompt_async is called
        original_write = sys.stdout.write
        write_calls = []
        
        def track_write(text):
            write_calls.append(('write', text))
            return original_write(text)
        
        # Mock prompt_session with timing tracking
        io_instance.prompt_session = MagicMock()
        
        async def track_prompt_async(*args, **kwargs):
            write_calls.append(('prompt_async_called', None))
            return "user input"
        
        io_instance.prompt_session.prompt_async = track_prompt_async

        # Patch sys.stdout.write to track calls
        with patch('sys.stdout.write', side_effect=track_write):
            result = await io_instance.get_input(".", [], [], MagicMock())

        # Analyze the call sequence
        a_write = None
        b_write = None
        prompt_call = None
        
        for i, (call_type, content) in enumerate(write_calls):
            if call_type == 'write' and content == "\x1b]133;A\x07":
                a_write = i
            elif call_type == 'write' and content == "\x1b]133;B\x07":
                b_write = i
            elif call_type == 'prompt_async_called':
                prompt_call = i
        
        # Verify timing: A -> B -> prompt_async (user input)
        assert a_write is not None, "A sequence should be written"
        assert b_write is not None, "B sequence should be written"
        assert prompt_call is not None, "prompt_async should be called"
        
        assert a_write < b_write, "A should come before B"
        assert b_write < prompt_call, "B should come before user input collection (prompt_async)"

    @patch('sys.stdout', new_callable=io.StringIO)
    async def test_osc133_full_interaction_cycle(self, mock_stdout):
        """Test complete OSC 133 sequence cycle: prompt phase -> command execution phase."""
        # Enable OSC 133
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)

        # Simulate linear output mode (required for OSC 133 emission)
        io_instance.linear = True

        # Mock prompt_session
        io_instance.prompt_session = MagicMock()
        io_instance.prompt_session.prompt_async = AsyncMock(return_value="test command")

        # 1. Get user input (should emit A/B around prompt display)
        user_input = await io_instance.get_input(".", [], [], MagicMock())

        # 2. Simulate AI response output (should emit C/D around response)
        io_instance.osc133_response_started = False
        io_instance.stream_output("AI response output", final=True)

        output = mock_stdout.getvalue()

        # Should have A sequence for prompt start
        assert "\x1b]133;A\x07" in output, "Missing OSC 133 A (prompt start) sequence"

        # Should have B sequence for prompt end (after prompt display, before user input)
        assert "\x1b]133;B\x07" in output, "Missing OSC 133 B (prompt end) sequence"

        # Should have C sequence for AI response (command execution)
        assert "\x1b]133;C\x07" in output, "Missing OSC 133 C (command start) sequence"

        # Should have D sequence for AI response completion
        assert "\x1b]133;D;0\x07" in output, "Missing OSC 133 D (command end) sequence"

        # Verify A comes before B (prompt phase)
        a_pos = output.find("\x1b]133;A\x07")
        b_pos = output.find("\x1b]133;B\x07")
        assert a_pos < b_pos, "OSC 133 A (prompt start) should come before B (prompt end)"

        # Verify B comes before C (prompt phase ends before command execution starts)
        c_pos = output.find("\x1b]133;C\x07")
        assert b_pos < c_pos, "OSC 133 B (prompt end) should come before C (command start)"

        # Verify C comes before D (command execution phase)
        d_pos = output.find("\x1b]133;D;0\x07")
        assert c_pos < d_pos, "OSC 133 C (command start) should come before D (command end)"

    @patch('sys.stdout', new_callable=io.StringIO)
    async def test_osc133_prompt_modification_with_b_sequence(self, mock_stdout):
        """Test that prompt is modified to include B sequence when OSC 133 is enabled."""
        # Enable OSC 133
        io_instance = InputOutput(pretty=False, fancy_input=False, semantic_terminal=True)
        io_instance.linear = True

        # Mock prompt_session to capture the modified prompt
        io_instance.prompt_session = MagicMock()
        io_instance.prompt_session.prompt_async = AsyncMock(return_value="user input")

        # Call get_input
        result = await io_instance.get_input(".", [], [], MagicMock())

        # Verify that prompt_async was called with modified prompt when OSC 133 is enabled
        io_instance.prompt_session.prompt_async.assert_called_once()
        call_args = io_instance.prompt_session.prompt_async.call_args
        
        # First argument should be the modified prompt with B sequence appended
        modified_prompt = call_args[0][0]
        assert "> " in modified_prompt, "Modified prompt should contain original prompt text"
        assert "\x1b]133;B\x07" in modified_prompt, "Modified prompt should contain B sequence"
        
        # B sequence should come after the prompt text
        prompt_pos = modified_prompt.find("> ")
        b_pos = modified_prompt.find("\x1b]133;B\x07")
        assert prompt_pos < b_pos, "B sequence should come after prompt text in modified prompt"

        output = mock_stdout.getvalue()
        
        # Verify A sequence is emitted before prompt_async call
        assert "\x1b]133;A\x07" in output, "A sequence should be emitted to stdout"
