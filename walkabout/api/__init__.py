"""Walkabout API routers and shared utilities."""

import os
import subprocess
import sys
from pathlib import Path

RUNNER = Path(__file__).parent.parent / "runner.py"


def _run_trace_subprocess(module_name: str, trace_path: Path, cwd: Path, timeout: float = 60) -> None:
    """Execute a note via runner.py subprocess and wait for the trace JSON.

    When running inside a PyInstaller bundle, execute the runner logic
    in-process instead of spawning a subprocess (sys.executable would be
    the walkabout binary itself and would launch another GUI).

    Raises RuntimeError on failure or timeout.
    """
    if getattr(sys, 'frozen', False):
        return _run_trace_inprocess(module_name, trace_path, cwd)

    from ..config import get_python_path

    walkabout_root = str(Path(__file__).parent.parent.parent)
    walkabout_core = str(Path(__file__).parent.parent / "core")
    existing = os.environ.get("PYTHONPATH", "")
    pythonpath = os.pathsep.join([walkabout_core, walkabout_root])
    if existing:
        pythonpath += os.pathsep + existing

    env = os.environ.copy()
    env["PYTHONPATH"] = pythonpath
    env["WALKABOUT_HOME"] = str(Path.home() / ".walkabout")

    python_exe = get_python_path()

    proc = subprocess.Popen(
        [python_exe, "-u", str(RUNNER),
         "--workspace", str(cwd),
         "--module", module_name,
         "--output", str(trace_path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
        cwd=str(cwd),
        env=env,
        **(dict(creationflags=subprocess.CREATE_NO_WINDOW) if sys.platform == "win32" else {}),
    )

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise RuntimeError(f"Execution timed out ({timeout}s limit)") from None

    if proc.returncode != 0:
        raise RuntimeError(stderr.strip() or stdout.strip() or "Execution failed")

    if not trace_path.exists():
        raise RuntimeError("Trace file not generated")


def _run_trace_inprocess(module_name: str, trace_path: Path, cwd: Path) -> None:
    """Execute a note in-process (used inside PyInstaller bundle)."""
    import json
    from dataclasses import asdict

    old_cwd = os.getcwd()
    old_home = os.environ.get("WALKABOUT_HOME")
    old_path = sys.path.copy()

    # Resolve core_dir BEFORE os.chdir() — __file__ may be relative
    # inside a PyInstaller bundle, and chdir would break resolution.
    core_dir = str(Path(__file__).resolve().parent.parent / "core")

    # Resolve cwd to canonical form (important on Windows where Path()
    # and Path().resolve() may differ in case/drive formatting).
    cwd_resolved = str(cwd.resolve())
    cwd.mkdir(parents=True, exist_ok=True)

    try:
        os.environ["WALKABOUT_HOME"] = str(Path.home() / ".walkabout")
        os.chdir(cwd_resolved)

        # User walkthrough scripts use ``from execute_util import ...``
        # (bare import).  The core/ directory must be on sys.path for this.
        # In PyInstaller, also add sys._MEIPASS for absolute imports.
        for p in [cwd_resolved, core_dir]:
            if p not in sys.path:
                sys.path.insert(0, p)
        if getattr(sys, 'frozen', False):
            meipass = str(Path(sys._MEIPASS))
            if meipass not in sys.path:
                sys.path.insert(0, meipass)

        # Register bare-import aliases so user walkthrough code like
        # ``from execute_util import text`` resolves to the SAME module
        # object as ``from walkabout.core.execute_util import pop_renderings``.
        # Without this, _current_renderings is a different list and
        # renderings are never captured (views show raw code, not output).
        import walkabout.core.execute_util as _ceu
        import walkabout.core.file_util as _cfu
        sys.modules['execute_util'] = _ceu
        sys.modules['file_util'] = _cfu

        # Pre-import the note module via file path to bypass PyInstaller's
        # FrozenImporter, which may intercept stdlib module names (e.g.,
        # Python's "test" package shadows a user note named test.py).
        import importlib.util as _importlib_util
        _parts = module_name.replace("/", ".").split(".")
        _note_file = cwd.joinpath(*_parts)
        if _note_file.is_dir():
            _note_file = _note_file / "__init__.py"
        else:
            _note_file = _note_file.with_suffix(".py")
        if not _note_file.exists():
            raise ModuleNotFoundError(
                f"Note file not found: {_note_file}. "
                f"Make sure the note exists in the workspace."
            )
        _spec = _importlib_util.spec_from_file_location(module_name, str(_note_file))
        _mod = _importlib_util.module_from_spec(_spec)
        sys.modules[module_name] = _mod
        _spec.loader.exec_module(_mod)

        from ..core.execute import execute

        trace = execute(module_name=module_name, inspect_all_variables=False)

        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with open(trace_path, "w", encoding="utf-8") as f:
            json.dump(asdict(trace), f, indent=2)
    except Exception:
        # On Windows/PyInstaller, provide diagnostic info for debugging
        import traceback as _traceback
        print(f"[_run_trace_inprocess] ERROR executing '{module_name}'", file=sys.stderr)
        print(f"  cwd (original): {cwd}", file=sys.stderr)
        print(f"  cwd (resolved): {cwd_resolved}", file=sys.stderr)
        print(f"  cwd exists: {cwd.is_dir()}", file=sys.stderr)
        print(f"  core_dir: {core_dir}", file=sys.stderr)
        print(f"  core_dir exists: {os.path.isdir(core_dir)}", file=sys.stderr)
        print(f"  sys.path (first 5): {sys.path[:5]}", file=sys.stderr)
        if cwd.is_dir():
            print(f"  files in cwd: {list(cwd.iterdir())[:20]}", file=sys.stderr)
        print(f"  frozen: {getattr(sys, 'frozen', False)}", file=sys.stderr)
        if getattr(sys, 'frozen', False):
            print(f"  _MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}", file=sys.stderr)
        _traceback.print_exc(file=sys.stderr)
        raise
    finally:
        sys.path[:] = old_path
        os.chdir(old_cwd)
        if old_home is not None:
            os.environ["WALKABOUT_HOME"] = old_home
