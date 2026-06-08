"""Tests for walkabout.core.execute — trace execution engine."""
import dataclasses
import os
import sys
from pathlib import Path

import pytest

# Ensure core modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent / "walkabout" / "core"))

from walkabout.core.execute import (
    StackElement,
    Step,
    Trace,
    execute,
    get_inspect_variables,
    to_serializable_value,
)


class TestGetInspectVariables:
    """Test comment-based @inspect variable extraction."""

    def test_single_inspect(self):
        code = 'x = 42  # @inspect x'
        assert get_inspect_variables(code) == ["x"]

    def test_multiple_inspect(self):
        code = 'x, y = 1, 2  # @inspect x, @inspect y'
        assert get_inspect_variables(code) == ["x", "y"]

    def test_no_inspect(self):
        code = 'x = 42'
        assert get_inspect_variables(code) == []

    def test_inspect_with_other_comments(self):
        code = 'x = 42  # this is a comment @inspect x'
        assert get_inspect_variables(code) == ["x"]

    def test_inspect_underscore_names(self):
        code = 'result = do_stuff()  # @inspect my_var_1'
        assert get_inspect_variables(code) == ["my_var_1"]

    def test_empty_code(self):
        assert get_inspect_variables("") == []


class TestToSerializableValue:
    """Test value serialization for JSON output."""

    def test_primitives(self):
        assert to_serializable_value(42) == 42
        assert to_serializable_value("hello") == "hello"
        assert to_serializable_value(True) is True
        assert to_serializable_value(3.14) == 3.14

    def test_list(self):
        assert to_serializable_value([1, 2, 3]) == [1, 2, 3]

    def test_nested_list(self):
        assert to_serializable_value([[1, 2], [3, 4]]) == [[1, 2], [3, 4]]

    def test_dict(self):
        result = to_serializable_value({"a": 1, "b": "hello"})
        assert result == {"a": 1, "b": "hello"}

    def test_object_falls_back_to_str(self):
        class Foo:
            def __str__(self):
                return "FooObject"
        def __repr__(self):
            return "FooObject"
        result = to_serializable_value(Foo())
        assert isinstance(result, str)

    def test_bool_values(self):
        assert to_serializable_value(True) is True
        assert to_serializable_value(False) is False


class TestStackElement:
    """Test StackElement dataclass."""

    def test_create(self):
        el = StackElement(path="test.py", line_number=10, function_name="main", code="x = 1")
        assert el.path == "test.py"
        assert el.line_number == 10
        assert el.function_name == "main"
        assert el.code == "x = 1"

    def test_frozen(self):
        el = StackElement(path="t.py", line_number=1, function_name="f", code="pass")
        with pytest.raises(dataclasses.FrozenInstanceError):
            el.path = "other.py"


class TestStep:
    """Test Step dataclass."""

    def test_defaults(self):
        step = Step(stack=[], env={})
        assert step.renderings == []
        assert step.stdout is None
        assert step.stderr is None

    def test_with_renderings(self):
        from walkabout.core.execute_util import Rendering
        r = Rendering(type="markdown", data="Hello")
        step = Step(stack=[], env={}, renderings=[r])
        assert len(step.renderings) == 1


class TestTrace:
    """Test Trace dataclass."""

    def test_create(self):
        trace = Trace(files={"test.py": "x = 1"}, steps=[])
        assert trace.files == {"test.py": "x = 1"}
        assert trace.steps == []


class TestExecute:
    """Integration tests for the execute() function."""

    def test_execute_basic_note(self, temp_home):
        """Execute a simple walkthrough and verify trace structure."""
        note = temp_home / "notes" / "basic.py"
        note.write_text("""\"\"\"Basic test.\"\"\"
from execute_util import text

def main():
    a = 10  # @inspect a
    b = 20  # @inspect b
    text("Result: " + str(a + b))
""", encoding="utf-8")

        # Add core to sys.path (bare imports in execute_util, etc.)
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        old_cwd = os.getcwd()
        old_path = sys.path.copy()
        try:
            os.chdir(str(temp_home / "notes"))
            if str(temp_home / "notes") not in sys.path:
                sys.path.insert(0, str(temp_home / "notes"))
            if core_dir not in sys.path:
                sys.path.insert(0, core_dir)

            trace = execute(module_name="basic", inspect_all_variables=False)

            assert isinstance(trace, Trace)
            assert len(trace.steps) > 0, "Should have at least 1 step"
            # Check that variables were captured
            env_values = {}
            for step in trace.steps:
                env_values.update(step.env)
            assert env_values.get("a") == 10
            assert env_values.get("b") == 20
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_path

    @pytest.mark.xfail(reason="text() renderings require execute_util imports in user module context")
    def test_execute_with_renderings(self, temp_home):
        """Verify renderings are captured from text() calls."""
        note = temp_home / "notes" / "rendering_test.py"
        note.write_text("""\"\"\"Rendering test.\"\"\"
from execute_util import text

def main():
    text("## Section 1")
    text("Some content here")
""", encoding="utf-8")

        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        old_cwd = os.getcwd()
        old_path = sys.path.copy()
        try:
            os.chdir(str(temp_home / "notes"))
            if str(temp_home / "notes") not in sys.path:
                sys.path.insert(0, str(temp_home / "notes"))
            if core_dir not in sys.path:
                sys.path.insert(0, core_dir)

            trace = execute(module_name="rendering_test", inspect_all_variables=False)

            all_renderings = []
            for step in trace.steps:
                all_renderings.extend(step.renderings)
            # Should have at least 2 markdown renderings
            markdown_count = sum(1 for r in all_renderings if r.type == "markdown")
            assert markdown_count >= 2, f"Expected >=2 markdown renderings, got {markdown_count}"
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_path

    def test_execute_module_not_found(self, temp_home):
        """Executing a non-existent module should raise ModuleNotFoundError."""
        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        old_path = sys.path.copy()
        old_cwd = os.getcwd()
        try:
            os.chdir(str(temp_home / "notes"))
            if core_dir not in sys.path:
                sys.path.insert(0, core_dir)
            with pytest.raises(ModuleNotFoundError):
                execute(module_name="nonexistent_module", inspect_all_variables=False)
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_path

    def test_list_comprehension_inspect(self, temp_home, capsys):
        """List comprehension @inspect captures the variable without WARNING spam."""
        note = temp_home / "notes" / "listcomp_test.py"
        note.write_text('''"""Test."""
def main():
    squares = [x * x for x in range(5)]  # @inspect squares
    _ = squares
''', encoding="utf-8")

        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        old_cwd = os.getcwd()
        old_path = sys.path.copy()
        try:
            os.chdir(str(temp_home / "notes"))
            if str(temp_home / "notes") not in sys.path:
                sys.path.insert(0, str(temp_home / "notes"))
            if core_dir not in sys.path:
                sys.path.insert(0, core_dir)

            trace = execute(module_name="listcomp_test", inspect_all_variables=False)

            # Check that squares was captured correctly
            env_values = {}
            for step in trace.steps:
                env_values.update(step.env)
            assert env_values.get("squares") == [0, 1, 4, 9, 16]

            # Check no WARNING was printed about squares not found
            captured = capsys.readouterr()
            assert "WARNING: variable squares not found" not in captured.out
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_path

    def test_set_comprehension_inspect(self, temp_home, capsys):
        """Set comprehension @inspect captures without WARNING spam."""
        note = temp_home / "notes" / "setcomp_test.py"
        note.write_text('''"""Test."""
def main():
    myset = {x for x in range(3)}  # @inspect myset
    _ = myset
''', encoding="utf-8")

        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        old_cwd = os.getcwd()
        old_path = sys.path.copy()
        try:
            os.chdir(str(temp_home / "notes"))
            if str(temp_home / "notes") not in sys.path:
                sys.path.insert(0, str(temp_home / "notes"))
            if core_dir not in sys.path:
                sys.path.insert(0, core_dir)

            trace = execute(module_name="setcomp_test", inspect_all_variables=False)

            env_values = {}
            for step in trace.steps:
                env_values.update(step.env)
            # Sets are serialised as strings (not JSON-native)
            assert env_values.get("myset") == '{0, 1, 2}'

            captured = capsys.readouterr()
            assert "WARNING: variable myset not found" not in captured.out
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_path

    def test_dict_comprehension_inspect(self, temp_home, capsys):
        """Dict comprehension @inspect captures without WARNING spam."""
        note = temp_home / "notes" / "dictcomp_test.py"
        note.write_text('''"""Test."""
def main():
    mydict = {k: v for k, v in [("a", 1)]}  # @inspect mydict
    _ = mydict
''', encoding="utf-8")

        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        old_cwd = os.getcwd()
        old_path = sys.path.copy()
        try:
            os.chdir(str(temp_home / "notes"))
            if str(temp_home / "notes") not in sys.path:
                sys.path.insert(0, str(temp_home / "notes"))
            if core_dir not in sys.path:
                sys.path.insert(0, core_dir)

            trace = execute(module_name="dictcomp_test", inspect_all_variables=False)

            env_values = {}
            for step in trace.steps:
                env_values.update(step.env)
            assert env_values.get("mydict") == {"a": 1}

            captured = capsys.readouterr()
            assert "WARNING: variable mydict not found" not in captured.out
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_path

    def test_generator_expression_inspect(self, temp_home, capsys):
        """Generator expression @inspect captures without WARNING spam."""
        note = temp_home / "notes" / "genexpr_test.py"
        note.write_text('''"""Test."""
def main():
    total = sum(x for x in range(3))  # @inspect total
    _ = total
''', encoding="utf-8")

        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        old_cwd = os.getcwd()
        old_path = sys.path.copy()
        try:
            os.chdir(str(temp_home / "notes"))
            if str(temp_home / "notes") not in sys.path:
                sys.path.insert(0, str(temp_home / "notes"))
            if core_dir not in sys.path:
                sys.path.insert(0, core_dir)

            trace = execute(module_name="genexpr_test", inspect_all_variables=False)

            env_values = {}
            for step in trace.steps:
                env_values.update(step.env)
            assert env_values.get("total") == 3

            captured = capsys.readouterr()
            assert "WARNING: variable total not found" not in captured.out
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_path

    def test_regular_inspect_still_works(self, temp_home, capsys):
        """Regular (non-comprehension) @inspect still works after comprehension fix."""
        note = temp_home / "notes" / "regular_inspect.py"
        note.write_text('''"""Test."""
def main():
    a = 10  # @inspect a
    b = 20  # @inspect b
    _ = a + b
''', encoding="utf-8")

        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        old_cwd = os.getcwd()
        old_path = sys.path.copy()
        try:
            os.chdir(str(temp_home / "notes"))
            if str(temp_home / "notes") not in sys.path:
                sys.path.insert(0, str(temp_home / "notes"))
            if core_dir not in sys.path:
                sys.path.insert(0, core_dir)

            trace = execute(module_name="regular_inspect", inspect_all_variables=False)

            env_values = {}
            for step in trace.steps:
                env_values.update(step.env)
            assert env_values.get("a") == 10
            assert env_values.get("b") == 20

            captured = capsys.readouterr()
            assert "WARNING" not in captured.out
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_path

    def test_execute_produces_file_dict(self, temp_home):
        """Trace should include the executed file in files dict."""
        note = temp_home / "notes" / "file_test.py"
        note.write_text("""\"\"\"File test.\"\"\"
def main():
    pass
""", encoding="utf-8")

        core_dir = str(Path(__file__).parent.parent / "walkabout" / "core")
        old_cwd = os.getcwd()
        old_path = sys.path.copy()
        try:
            os.chdir(str(temp_home / "notes"))
            if str(temp_home / "notes") not in sys.path:
                sys.path.insert(0, str(temp_home / "notes"))
            if core_dir not in sys.path:
                sys.path.insert(0, core_dir)

            trace = execute(module_name="file_test", inspect_all_variables=False)
            assert len(trace.files) == 1
            assert any("file_test.py" in k for k in trace.files)
        finally:
            os.chdir(old_cwd)
            sys.path[:] = old_path
