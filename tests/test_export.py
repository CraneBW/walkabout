"""Tests for walkabout.export — trace-to-HTML export engine."""
import json
import os
import tempfile
from pathlib import Path

from walkabout.export import _clean_trace, export_note, generate_html


def _make_sample_trace():
    """Create a minimal valid trace dict for testing."""
    return {
        "files": {
            "test.py": "def main():\n    x = 1  # @inspect x\n    text('hello')\n"
        },
        "steps": [
            {
                "stack": [
                    {"path": "test.py", "line_number": 1,
                     "function_name": "main", "code": "def main():"}
                ],
                "env": {"x": 1},
                "renderings": [
                    {"type": "markdown", "data": "hello", "style": {}}
                ],
                "stdout": "", "stderr": ""
            },
            {
                "stack": [
                    {"path": "test.py", "line_number": 2,
                     "function_name": "main", "code": "text('hello')"}
                ],
                "env": {},
                "renderings": [
                    {"type": "markdown", "data": "hello", "style": {}}
                ],
                "stdout": "", "stderr": ""
            },
        ]
    }


class TestCleanTrace:
    """Test _clean_trace — stripping unreferenced source code."""

    def test_keeps_referenced_lines(self):
        trace = _make_sample_trace()
        cleaned = _clean_trace(trace)
        content = cleaned["files"]["test.py"]
        # Lines 1 and 2 should be preserved
        assert "def main():" in content
        assert "text('hello')" in content

    def test_does_not_modify_original(self):
        trace = _make_sample_trace()
        original = trace["files"]["test.py"]
        _clean_trace(trace)
        assert trace["files"]["test.py"] == original  # original unchanged


class TestGenerateHTML:
    """Test generate_html — HTML generation."""

    def test_generates_valid_html(self):
        trace = _make_sample_trace()
        html = generate_html(trace, title="Test", strip_source=False, content_only=False)
        assert "<!doctype html>" in html.lower()
        assert "Walkabout - Test</title>" in html or "Test" in html
        assert "__TRACE_JSON__" not in html  # placeholder replaced
        assert "__TITLE__" not in html

    def test_content_only_mode(self):
        trace = _make_sample_trace()
        html = generate_html(trace, title="Test", strip_source=True, content_only=True)
        # In content_only mode, the JS flag is set to true
        assert "var contentOnly = true" in html or 'contentOnly = true' in html

    def test_strip_source_mode(self):
        trace = _make_sample_trace()
        html = generate_html(trace, title="Test", strip_source=True, content_only=False)
        assert "__TRACE_JSON__" not in html

    def test_xss_escaping(self):
        """Verify </script> injection is escaped."""
        trace = _make_sample_trace()
        # Inject malicious content
        trace["steps"][0]["env"]["x"] = "</script><script>alert(1)</script>"
        html = generate_html(trace, title="Test", strip_source=False, content_only=False)
        # The </script> should be escaped to <\/script> or similar
        assert "<\\/" in html or "<\\\\/" in html or "</script><script>" not in html.lower()

    def test_title_in_html(self):
        trace = _make_sample_trace()
        html = generate_html(trace, title="My Walkthrough", strip_source=False, content_only=False)
        assert "My Walkthrough" in html


class TestExportNote:
    """Test export_note — end-to-end export."""

    def test_export_creates_html_file(self):
        trace = _make_sample_trace()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            tf.write(json.dumps(trace).encode("utf-8"))
            trace_path = tf.name

        html_path = trace_path.replace(".json", ".html")
        try:
            export_note(Path(trace_path), Path(html_path), title="Test Export")
            assert os.path.exists(html_path)
            content = Path(html_path).read_text(encoding="utf-8")
            assert "<!doctype html>" in content.lower()
            assert "Test Export" in content
        finally:
            for p in [trace_path, html_path]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_export_creates_parent_dirs(self):
        trace = _make_sample_trace()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            tf.write(json.dumps(trace).encode("utf-8"))
            trace_path = tf.name

        html_path = os.path.join(tempfile.mkdtemp(), "subdir", "output.html")
        try:
            export_note(Path(trace_path), Path(html_path), title="Test")
            assert os.path.exists(html_path)
        finally:
            if os.path.exists(trace_path):
                os.unlink(trace_path)
            parent = Path(html_path).parent
            if parent.exists():
                import shutil
                shutil.rmtree(parent.parent, ignore_errors=True)
