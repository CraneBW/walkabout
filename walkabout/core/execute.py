from __future__ import annotations

import argparse
import contextlib
import importlib
import importlib.util
import json
import sys
import traceback

try:
    import torch
except ImportError:
    torch = None
try:
    import sympy
except ImportError:
    sympy = None
import os
import re
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from typing import Any

from walkabout.core.execute_util import Rendering, pop_renderings
from walkabout.core.file_util import ensure_directory_exists, relativize


@dataclass(frozen=True)
class StackElement:
    path: str
    """The path to the file containing the code."""

    line_number: int
    """The line number of the code."""

    function_name: str
    """The name of the function that we're in."""

    code: str
    """The source code that is executed."""


@dataclass
class Step:
    stack: list[StackElement]
    """The stack of function calls."""

    env: dict[str, Any]
    """The local variables including function arguments(that we're @inspect-ing)."""

    renderings: list[Rendering] = field(default_factory=list)
    """The output of the code (see execute_util.py)."""

    stdout: str | None = None
    """The stdout of the code."""

    stderr: str | None = None
    """The stderr of the code."""


@dataclass(frozen=True)
class Trace:
    files: dict[str, str]
    steps: list[Step]


def _dict_to_trace(d: dict) -> Trace:
    """Reconstruct a Trace from its ``asdict()`` representation.

    Plugin ``on_post_execute`` hooks receive and return trace dicts, so we
    need to convert back after a plugin modifies the trace.
    """
    from walkabout.core.execute_util import Rendering

    steps: list[Step] = []
    for s in d.get("steps", []):
        stack = [
            StackElement(
                path=e["path"],
                line_number=e["line_number"],
                function_name=e["function_name"],
                code=e["code"],
            )
            for e in s.get("stack", [])
        ]
        renderings = [
            Rendering(
                type=r.get("type", "text"),
                data=r.get("data"),
                style=r.get("style"),
                external_link=r.get("external_link"),
                internal_link=r.get("internal_link"),
            )
            for r in s.get("renderings", [])
        ]
        steps.append(Step(
            stack=stack,
            env=dict(s.get("env", {})),
            renderings=renderings,
            stdout=s.get("stdout"),
            stderr=s.get("stderr"),
        ))
    return Trace(files=dict(d.get("files", {})), steps=steps)


def to_primitive(value: Any) -> Any:
    if isinstance(value, (int, float, str, bool)):
        return value
    # Force it to be a primitive
    return str(value)

def to_serializable_value(value: Any) -> Any:
    """Convert any type to a serializable value."""
    if torch is not None and isinstance(value, torch.Tensor):
        return value.tolist()
    if sympy is not None and isinstance(value, sympy.core.numbers.Integer):
        return int(value)
    if sympy is not None and isinstance(value, sympy.core.numbers.Float):
        return float(value)
    if sympy is not None and isinstance(value, sympy.core.symbol.Symbol):
        return str(value)  # Would be nice to signal that this is not a string
    if isinstance(value, (int, float, str, bool)):
        return value
    if isinstance(value, list):
        return [to_serializable_value(item) for item in value]
    if isinstance(value, dict):
        return {to_primitive(k): to_serializable_value(v) for k, v in value.items()}
    if is_dataclass(value):
        return {
            field.name: to_serializable_value(getattr(value, field.name))
            for field in fields(value)
        }
    # Force it to be a primitive
    return str(value)

def get_inspect_variables(code: str) -> list[str]:
    """
    If code contains "@inspect <variable>" (as a comment), return those variables.
    Example code:
        x, y = str.split("a,b")  # @inspect x, @inspect y
    We would return ["x", "y"]
    """
    variables = []
    # Find all "@inspect <variable>" occurrences
    matches = re.finditer(r"@inspect\s+(\w+)", code)
    for match in matches:
        variables.append(match.group(1))
    return variables


def execute(module_name: str, inspect_all_variables: bool,
            plugin_manager=None) -> Trace:
    """
    Execute the module and return a trace of the execution.
    """
    steps: list[Step] = []

    real_stdout = sys.stdout

    # Figure out which files we're actually tracing
    visible_paths = []

    # Stack of locations that we're stepping over
    stepovers = []

    # Track which files are engine files (not user code)
    _engine_paths: set = set()

    def get_stack() -> list[StackElement]:
        """Return the last element of `stack`, skipping engine/bootstrap frames."""
        stack = []
        items = traceback.extract_stack()
        # Find where execute() sits in the stack
        execute_idx = None
        for i, item in enumerate(items):
            if "walkabout/core/execute.py" in item.filename.replace("\\", "/"):
                execute_idx = i
                break
        if execute_idx is None:
            execute_idx = 1  # fallback
        # Only include frames ABOVE execute() (user code)
        for item in items[execute_idx + 1:]:
            if item.name in ("trace_func", "local_trace_func", "get_stack"):
                continue
            stack.append(StackElement(
                path=relativize(item.filename),
                line_number=item.lineno,
                function_name=item.name,
                code=item.line,
            ))
        # Track engine files for visible_paths
        for i in range(execute_idx + 1):
            if i < len(items):
                _engine_paths.add(items[i].filename)
        return stack

    def trace_func(frame, event, arg):
        """
        trace_func and local_trace_func are called on various lines of code when executed.
        - trace_func is called *before* a line of code is executed.
        - local_trace_func is called *after* a line of code has been executed
          and will have the values of the variables.
        We generally keep the local_trace_func version.  However, when you have
        a function call that you're tracing through, you want to keep both
        versions.

        We don't care about all the events, so here are the rules:
        - In local_trace_func, if the previous event was the same line (presumably the trace_func)
        - Remove all trace_func(return)
        """

        # Get the current file path from the frame and skip if not in visible paths
        # to avoid tracing deep into imports (which would be slow and irrelevant)
        current_path = frame.f_code.co_filename
        if current_path not in visible_paths:
            return trace_func

        stack = get_stack()

        if event == "return":
            return trace_func

        # Print the current line of code
        item = stack[-1]
        if "@stepover" in item.code:
            if len(stepovers) > 0 and stepovers[-1] == (item.path, item.line_number):
                stepovers.pop()
            else:
                stepovers.append((item.path, item.line_number))

        # Skip everything that is strictly under stepovers
        if any(stepover[0] == item.path and stepover[1] == item.line_number for stepover in stepovers for item in stack[:-1]):
            return trace_func

        print(f"  [{len(steps)} {os.path.basename(item.path)}:{item.line_number}] {item.code}", file=real_stdout)

        open_step = Step(
            stack=stack,
            env={},
            stdout="",
            stderr="",
        )
        if len(steps) == 0 or open_step.stack != steps[-1].stack:  # Only add a step if it's not redundant
            steps.append(open_step)
        open_step_index = len(steps) - 1

        # Track which step indices have already received their first
        # local_trace_func call.  The first call fires before the corresponding
        # line has executed, so we suppress "not found" warnings then.  This
        # also handles inlined comprehensions (PEP 709, Python 3.12+), where
        # local_trace_func fires many times for a single source line.
        # CPython comprehension frame names where @inspect variables
        # are not yet assigned.
        _COMPREHENSION_FRAMES = frozenset({
            '<listcomp>', '<setcomp>', '<dictcomp>', '<genexpr>',
        })

        _seen_steps: set[int] = set()

        def local_trace_func(frame, event, arg):
            """This is called *after* a line of code has been executed."""
            # Skip comprehension/generator frames (<listcomp>, <genexpr>, etc.)
            # They run in an implicit function scope where @inspect variables
            # are not yet assigned.  We explicitly check for CPython's
            # comprehension frame markers rather than a blanket '<' / '>'
            # check so that '<module>' (module-level code) is NOT suppressed.
            if frame.f_code.co_name in _COMPREHENSION_FRAMES:
                return trace_func(frame, event, arg)

            # If the last step was the same line, then just use the same one
            # Otherwise, create a new step (e.g., returning from a function)
            if open_step_index == len(steps) - 1:
                close_step = steps[-1]
            else:
                print(f"  [{len(steps)} {os.path.basename(item.path)}:{item.line_number}] {item.code}", file=real_stdout)

                close_step = Step(
                    stack=stack,
                    env={},
                    stdout="",
                    stderr="",
                )
                steps.append(close_step)

            is_first_call = open_step_index not in _seen_steps
            _seen_steps.add(open_step_index)

            # Update the environment with the actual values
            frame_locals = frame.f_locals
            vars = frame_locals.keys() if inspect_all_variables else get_inspect_variables(item.code)
            for var in vars:
                if var in frame_locals:
                    close_step.env[var] = to_serializable_value(frame_locals[var])
                elif var not in close_step.env:
                    if not is_first_call:
                        print(f"WARNING: variable {var} not found in locals")
                    # Place None so subsequent iterations skip re-warning
                    close_step.env[var] = None
                print(f"    env: {var} = {close_step.env.get(var)}", file=real_stdout)

            # Capture the renderings of the last line
            close_step.renderings = pop_renderings()

            # Pass control back to the global trace function
            return trace_func(frame, event, arg)

        # Pass control to local_trace_func to update the environment
        return local_trace_func

    # Resolve module file path and read source *before* importing, so
    # on_pre_execute can modify the source before it executes.
    spec = importlib.util.find_spec(module_name)
    if spec is None or spec.origin is None:
        raise ModuleNotFoundError(f"Cannot find module: {module_name}")
    module_file = spec.origin

    with open(module_file, encoding="utf-8") as f:
        module_source = f.read()

    # Plugin on_pre_execute hook — plugins may return modified source code.
    modified_source = None
    if plugin_manager is not None:
        with contextlib.suppress(Exception):
            modified_source = plugin_manager.on_pre_execute(module_name, module_source)

    if modified_source is not None:
        # Source was modified by a plugin — execute the modified source
        # directly in a new module namespace instead of importing.
        module = importlib.import_module(module_name)
        exec(compile(modified_source, module_file, "exec"), module.__dict__)
    else:
        module = importlib.import_module(module_name)

    visible_paths.append(module_file)

    sys.settrace(trace_func)
    module.main()
    sys.settrace(None)

    files = {}
    for path in visible_paths:
        with open(path, encoding="utf-8") as f:
            files[relativize(path)] = f.read()
    trace = Trace(steps=steps, files=files)

    # Plugin on_post_execute hook — plugins may return a modified trace.
    if plugin_manager is not None:
        try:
            trace_dict = asdict(trace)
            modified_trace = plugin_manager.on_post_execute(module_name, trace_dict)
            if modified_trace is not None:
                trace = _dict_to_trace(modified_trace)
        except Exception:
            pass

    return trace

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--module", help="List of modules to execute (e.g., lecture_01)", type=str, nargs="+")
    parser.add_argument("-o", "--output_path", help="Path to save the trace", type=str, default="var/traces")
    parser.add_argument("-I", "--inspect-all-variables", help="Inspect all variables (default: only inspect variables mentioned in @inspect comments)", action="store_true")
    args = parser.parse_args()

    ensure_directory_exists(args.output_path)

    for module in args.module:
        module = module.replace(".py", "")  # Just in case
        print(f"Executing {module}...")
        trace = execute(module_name=module, inspect_all_variables=args.inspect_all_variables)
        print(f"{len(trace.steps)} steps")
        output_path = os.path.join(args.output_path, f"{module}.json")
        print(f"Saving trace to {output_path}...")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(trace), f, indent=2)
