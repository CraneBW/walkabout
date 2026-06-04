"""Walkabout API routers and shared utilities."""

import os
import subprocess
from pathlib import Path

RUNNER = Path(__file__).parent.parent / "runner.py"


def _run_trace_subprocess(module_name: str, trace_path: Path, cwd: Path, timeout: float = 60) -> None:
    """Execute a note via runner.py subprocess and wait for the trace JSON.

    Raises RuntimeError on failure or timeout.
    """
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
