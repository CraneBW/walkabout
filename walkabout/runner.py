"""Subprocess entry point for walkthrough execution.

Usage: python runner.py --workspace NOTES_DIR --module my_note --output trace.json
"""
import argparse
import json
import os
import sys
from dataclasses import asdict


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, help="Path to notes directory")
    parser.add_argument("--module", required=True, help="Module name to import")
    parser.add_argument("--output", required=True, help="Output trace JSON path")
    args = parser.parse_args()
    # When running inside a PyInstaller bundle, sys.executable IS the Python
    # interpreter (the packed binary).  Skip the venv re-exec — it would
    # replace us with a venv Python that may not have walkabout installed.
    # Also skip on Windows, where os.execv is unavailable.
    if not getattr(sys, 'frozen', False) and sys.platform != "win32":
        # Use workspace venv Python if available
        if sys.platform == "win32":
            venv_python = os.path.join(args.workspace, ".venv", "Scripts", "python.exe")
        else:
            venv_python = os.path.join(args.workspace, ".venv", "bin", "python3")
        if not os.path.exists(venv_python):
            venv_python = os.path.join(os.path.expanduser("~/.walkabout"), ".venv",
                                       "Scripts" if sys.platform == "win32" else "bin",
                                       "python.exe" if sys.platform == "win32" else "python3")
        if os.path.exists(venv_python) and sys.executable != venv_python:
            os.execv(venv_python, [venv_python] + sys.argv)


    # Setup paths: workspace first, then core engine
    runner_dir = os.path.dirname(os.path.abspath(__file__))
    core_dir = os.path.join(runner_dir, 'core')  # walkabout/core/ — has execute_util, file_util, execute
    walkabout_root = os.path.join(runner_dir, '..')  # project root — has walkabout package
    sys.path.insert(0, args.workspace)
    sys.path.insert(0, core_dir)  # for execute_util, file_util, etc.
    sys.path.insert(0, walkabout_root)  # for walkabout.core
    os.environ["WALKABOUT_HOME"] = os.path.expanduser("~/.walkabout")
    os.chdir(args.workspace)

    # Import the module
    import importlib
    importlib.import_module(args.module)

    # Execute with tracing
    from walkabout.core.execute import execute

    trace = execute(module_name=args.module, inspect_all_variables=False)

    # Save trace
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(asdict(trace), f, indent=2)

    print(f"Trace saved: {args.output} ({len(trace.steps)} steps)", file=sys.stderr)


def execute_note(script_path: str, output_path: str,
                 inspect_all: bool = False) -> dict:
    """Execute a walkthrough script and save trace JSON, all in-process.

    This is the reusable entry point shared by the ``run`` CLI subcommand
    and the ``export`` CLI subcommand (when no ``--from-trace`` is given).

    Args:
        script_path: Absolute or relative path to the ``.py`` walkthrough.
        output_path: Where to write the trace JSON.
        inspect_all:  If True, capture *all* local variables at each step
            (not just those annotated with ``@inspect``).

    Returns:
        The trace dict (keys ``steps``, ``files``).

    Raises:
        FileNotFoundError: *script_path* does not exist.
    """
    script_path = os.path.abspath(script_path)
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script not found: {script_path}")

    output_path = os.path.abspath(output_path)
    workspace = os.path.dirname(script_path)
    module_name = os.path.splitext(os.path.basename(script_path))[0]

    # Paths for bare imports (mirrors the logic in main(), above)
    runner_dir = os.path.dirname(os.path.abspath(__file__))
    core_dir = os.path.join(runner_dir, 'core')
    walkabout_root = os.path.dirname(runner_dir)  # parent of walkabout/

    old_cwd = os.getcwd()
    old_path = sys.path.copy()
    _saved_aliases: dict[str, object | None] = {}
    try:
        sys.path.insert(0, workspace)
        sys.path.insert(0, core_dir)
        sys.path.insert(0, walkabout_root)
        os.environ.setdefault("WALKABOUT_HOME",
                              os.path.expanduser("~/.walkabout"))
        os.chdir(workspace)

        # Register bare-import aliases so user code that does
        # ``from execute_util import text`` shares the **same** module
        # object as ``from walkabout.core.execute_util import pop_renderings``
        # (B15 fix — without this, _current_renderings is a different list
        # and renderings are never captured).
        import walkabout.core.execute_util as _ceu
        import walkabout.core.file_util as _cfu
        _saved_aliases['execute_util'] = sys.modules.get('execute_util')
        _saved_aliases['file_util'] = sys.modules.get('file_util')
        sys.modules['execute_util'] = _ceu
        sys.modules['file_util'] = _cfu

        from walkabout.core.execute import execute

        trace = execute(module_name=module_name,
                        inspect_all_variables=inspect_all)

        trace_dict = asdict(trace)

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(trace_dict, f, indent=2)

        return trace_dict
    finally:
        os.chdir(old_cwd)
        sys.path[:] = old_path
        # Remove user module from cache so subsequent calls with a
        # different script of the same name work correctly.
        sys.modules.pop(module_name, None)
        # Restore bare-import aliases to their original state.
        for alias, original in _saved_aliases.items():
            if original is None:
                sys.modules.pop(alias, None)
            else:
                sys.modules[alias] = original


if __name__ == "__main__":
    main()
