"""Execution API — run walkthrough scripts and generate trace JSON."""
import json
import subprocess
import sys
import uuid
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..config import NOTES_DIR, TRACES_DIR, FILES_DIR, ensure_dirs, get_python_path

router = APIRouter(prefix="/api/execute", tags=["execute"])


class ExecuteRequest(BaseModel):
    path: str
    content: Optional[str] = None  # Optional: auto-save before execute

class ExecuteResponse(BaseModel):
    run_id: str
    status: str  # "ok" | "error"
    trace_url: Optional[str] = None
    steps: Optional[int] = None
    error: Optional[str] = None


RUNNER = Path(__file__).parent.parent / "runner.py"


@router.post("")
def execute_note(req: ExecuteRequest) -> ExecuteResponse:
    ensure_dirs()

    # Auto-save if content provided
    note_path = NOTES_DIR / req.path
    note_path.parent.mkdir(parents=True, exist_ok=True)
    if req.content is not None:
        note_path.write_text(req.content, encoding="utf-8")

    if not note_path.exists():
        raise HTTPException(404, f"Note not found: {req.path}")

    # Generate trace path
    run_id = uuid.uuid4().hex[:8]
    module_name = req.path.replace("/", ".").replace(".py", "")
    trace_path = TRACES_DIR / f"{module_name}.json"

    # Run subprocess
    env = os.environ.copy()
    # Add walkabout to PYTHONPATH so core engine is importable
    walkabout_root = str(Path(__file__).parent.parent.parent)
    walkabout_core = str(Path(__file__).parent.parent / 'core')
    existing = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = f'{walkabout_core}:{walkabout_root}' + (f':{existing}' if existing else '')
    env["WALKABOUT_HOME"] = str(Path.home() / ".walkabout")

    # Use configured Python interpreter
    python_exe = get_python_path()

    try:
        result = subprocess.run(
            [python_exe, "-u", str(RUNNER),
             "--workspace", str(NOTES_DIR),
             "--module", module_name,
             "--output", str(trace_path)],
            capture_output=True, text=True,
            timeout=60,
            cwd=str(NOTES_DIR),
            env=env
        )

        if result.returncode != 0:
            return ExecuteResponse(
                run_id=run_id,
                status="error",
                error=result.stderr.strip() or result.stdout.strip() or "Unknown error"
            )

        if not trace_path.exists():
            return ExecuteResponse(
                run_id=run_id,
                status="error",
                error="Trace file was not generated"
            )

        with open(trace_path) as f:
            trace = json.load(f)
        steps = len(trace.get("steps", []))

        return ExecuteResponse(
            run_id=run_id,
            status="ok",
            trace_url=f"/api/traces/{module_name}.json",
            steps=steps
        )

    except subprocess.TimeoutExpired:
        return ExecuteResponse(
            run_id=run_id,
            status="error",
            error="Execution timed out (60s limit)"
        )
    except Exception as e:
        return ExecuteResponse(
            run_id=run_id,
            status="error",
            error=str(e)
        )
