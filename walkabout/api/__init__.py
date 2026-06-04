"""Walkabout API routers and shared utilities."""

import os
import sys
import subprocess
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
    pythonpath = f"{walkabout_core}:{walkabout_root}"
    if existing:
        pythonpath += f":{existing}"

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
    )

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise RuntimeError(f"Execution timed out ({timeout}s limit)")

    if proc.returncode != 0:
        raise RuntimeError(stderr.strip() or stdout.strip() or "Execution failed")

    if not trace_path.exists():
        raise RuntimeError("Trace file not generated")


def _run_trace_inprocess(module_name: str, trace_path: Path, cwd: Path) -> None:
    """Execute a note in-process (used inside PyInstaller bundle)."""
    import importlib
    import json
    from dataclasses import asdict

    old_cwd = os.getcwd()
    old_home = os.environ.get("WALKABOUT_HOME")
    old_path = sys.path.copy()
    try:
        os.environ["WALKABOUT_HOME"] = str(Path.home() / ".walkabout")
        os.chdir(str(cwd))

        # core/ uses bare imports (from execute_util import ...) — needs on sys.path
        core_dir = str(Path(__file__).parent.parent / "core")
        for p in [str(cwd), core_dir]:
            if p not in sys.path:
                sys.path.insert(0, p)

        from ..core.execute import execute

        trace = execute(module_name=module_name, inspect_all_variables=False)

        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with open(trace_path, "w") as f:
            json.dump(asdict(trace), f, indent=2)
    finally:
        sys.path[:] = old_path
        os.chdir(old_cwd)
        if old_home is not None:
            os.environ["WALKABOUT_HOME"] = old_home
