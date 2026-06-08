"""Tests for CLI subcommands: serve, run, export."""
import json
import sys

import pytest


class TestArgparse:
    """Test argument parsing for CLI subcommands."""

    def test_serve_default(self):
        """When no subcommand given, default to serve."""
        from walkabout.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args([])
        # No subcommand → subcommand is None or "serve"
        assert args.subcommand is None or args.subcommand == "serve"

    def test_serve_explicit(self):
        """'walkabout serve' works."""
        from walkabout.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(["serve"])
        assert args.subcommand == "serve"

    def test_run_minimal(self):
        """'walkabout run script.py' parses correctly."""
        from walkabout.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(["run", "script.py"])
        assert args.subcommand == "run"
        assert args.script == "script.py"
        assert args.output is None
        assert args.inspect_all is False

    def test_run_with_output(self):
        """'walkabout run script.py -o trace.json'."""
        from walkabout.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(["run", "script.py", "-o", "trace.json"])
        assert args.output == "trace.json"

    def test_run_with_inspect_all(self):
        """'walkabout run script.py --inspect-all'."""
        from walkabout.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(["run", "script.py", "--inspect-all"])
        assert args.inspect_all is True

    def test_run_missing_script(self):
        """'walkabout run' without script should error."""
        from walkabout.__main__ import create_parser

        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["run"])

    def test_export_minimal(self):
        """'walkabout export script.py' parses correctly."""
        from walkabout.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(["export", "script.py"])
        assert args.subcommand == "export"
        assert args.script == "script.py"
        assert args.from_trace is None

    def test_export_with_output(self):
        """'walkabout export script.py -o out.html'."""
        from walkabout.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(["export", "script.py", "-o", "out.html"])
        assert args.output == "out.html"

    def test_export_with_strip_source(self):
        """'walkabout export script.py --strip-source'."""
        from walkabout.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(["export", "script.py", "--strip-source"])
        assert args.strip_source is True

    def test_export_with_content_only(self):
        """'walkabout export script.py --content-only'."""
        from walkabout.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(["export", "script.py", "--content-only"])
        assert args.content_only is True

    def test_export_from_trace(self):
        """'walkabout export --from-trace trace.json -o out.html'."""
        from walkabout.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["export", "--from-trace", "trace.json", "-o", "out.html"]
        )
        assert args.subcommand == "export"
        assert args.from_trace == "trace.json"
        assert args.script is None
        assert args.output == "out.html"

    def test_export_missing_both(self):
        """'walkabout export' without script or --from-trace should error."""
        from walkabout.__main__ import create_parser

        parser = create_parser()
        # argparse accepts "export" with no args (script is nargs='?'),
        # so parse succeeds:
        args = parser.parse_args(["export"])
        assert args.subcommand == "export"
        assert args.script is None
        assert args.from_trace is None


class TestExecuteNote:
    """Test the reusable execute_note function from walkabout.runner."""

    def test_execute_basic(self, temp_home):
        """Execute a simple walkthrough and verify trace JSON output."""
        from walkabout.runner import execute_note

        script = temp_home / "notes" / "cli_test_basic.py"
        script.write_text(
            '"""Basic test."""\n'
            "from execute_util import text\n"
            "\n"
            "def main():\n"
            '    x = 42  # @inspect x\n'
            '    text("Hello")\n',
            encoding="utf-8",
        )

        output = temp_home / "cli_test_basic.json"
        trace = execute_note(str(script), str(output))

        assert output.exists()
        assert isinstance(trace, dict)
        assert "steps" in trace
        assert "files" in trace
        assert len(trace["steps"]) > 0

    def test_execute_captures_variables(self, temp_home):
        """Verify @inspect variables are captured in trace."""
        from walkabout.runner import execute_note

        script = temp_home / "notes" / "cli_test_vars.py"
        script.write_text(
            '"""Variable test."""\n'
            "from execute_util import text\n"
            "\n"
            "def main():\n"
            "    a = 10  # @inspect a\n"
            '    b = "hello"  # @inspect b\n'
            '    text("done")\n',
            encoding="utf-8",
        )

        output = temp_home / "cli_test_vars.json"
        trace = execute_note(str(script), str(output))

        env_values = {}
        for step in trace["steps"]:
            env_values.update(step.get("env", {}))
        assert env_values.get("a") == 10
        assert env_values.get("b") == "hello"

    def test_execute_invalid_path(self, temp_home):
        """Non-existent script should raise FileNotFoundError."""
        from walkabout.runner import execute_note

        with pytest.raises(FileNotFoundError):
            execute_note(
                str(temp_home / "nonexistent.py"), str(temp_home / "out.json")
            )

    def test_execute_removes_module_from_cache(self, temp_home):
        """After execute_note, the module should be removed from sys.modules."""
        from walkabout.runner import execute_note

        script = temp_home / "notes" / "cli_test_cache.py"
        script.write_text(
            '"""Cache test."""\n'
            "from execute_util import text\n"
            "\n"
            "def main():\n"
            '    text("hello")\n',
            encoding="utf-8",
        )

        module_name = "cli_test_cache"
        assert module_name not in sys.modules

        output = temp_home / "cli_test_cache.json"
        execute_note(str(script), str(output))

        assert module_name not in sys.modules


class TestExportCommand:
    """Test the export command flow."""

    def test_export_from_trace_file(self, temp_home):
        """Export HTML from an existing trace JSON."""
        from walkabout.__main__ import export_command

        trace = {
            "files": {"script.py": "print('hello')\n"},
            "steps": [
                {
                    "stack": [
                        {
                            "path": "script.py",
                            "line_number": 1,
                            "function_name": "<module>",
                            "code": "print('hello')",
                        }
                    ],
                    "env": {},
                    "renderings": [],
                    "stdout": "",
                    "stderr": "",
                }
            ],
        }
        trace_path = temp_home / "test_export_trace.json"
        with open(trace_path, "w", encoding="utf-8") as f:
            json.dump(trace, f)

        output_path = temp_home / "test_export_output.html"

        export_command(
            script=None,
            from_trace=str(trace_path),
            output=str(output_path),
            strip_source=False,
            content_only=False,
        )

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "<!doctype html>" in content.lower()

    def test_export_requires_script_or_trace(self, temp_home):
        """Export with neither script nor --from-trace should exit."""
        from walkabout.__main__ import export_command

        with pytest.raises(SystemExit):
            export_command(
                script=None,
                from_trace=None,
                output=None,
                strip_source=False,
                content_only=False,
            )

    def test_export_default_output_name(self, temp_home):
        """Export without -o derives output name from trace path."""
        from walkabout.__main__ import export_command

        trace_path = temp_home / "mytrace.json"
        trace_path.write_text(
            json.dumps({
                "files": {"s.py": "print(1)"},
                "steps": [
                    {
                        "stack": [
                            {
                                "path": "s.py",
                                "line_number": 1,
                                "function_name": "<module>",
                                "code": "print(1)",
                            }
                        ],
                        "env": {},
                        "renderings": [],
                        "stdout": "",
                        "stderr": "",
                    }
                ],
            }),
            encoding="utf-8",
        )

        export_command(
            script=None,
            from_trace=str(trace_path),
            output=None,
            strip_source=False,
            content_only=False,
        )

        expected_html = temp_home / "mytrace.html"
        assert expected_html.exists()
        content = expected_html.read_text(encoding="utf-8")
        assert "<!doctype html>" in content.lower()
