"""Execution API — run walkthrough scripts and generate trace JSON."""
import json
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import NOTES_DIR, TRACES_DIR, ensure_dirs
from . import _run_trace_subprocess


def _resolve(relpath: str):
    """Resolve *relpath* against NOTES_DIR, rejecting path traversal.

    Uses Path.relative_to() which is case-insensitive on Windows and
    properly handles path boundaries (no string-startswith tricks)."""
    p = (NOTES_DIR / relpath).resolve()
    try:
        p.relative_to(NOTES_DIR.resolve())
    except ValueError:
        raise HTTPException(403, "Invalid path") from None
    return p

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


@router.post("")
def execute_note(req: ExecuteRequest) -> ExecuteResponse:
    ensure_dirs()

    # Auto-save if content provided
    note_path = _resolve(req.path)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    if req.content is not None:
        note_path.write_text(req.content, encoding="utf-8")

    if not note_path.exists():
        raise HTTPException(404, f"Note not found: {req.path}")

    run_id = uuid.uuid4().hex[:8]
    module_name = req.path.replace("/", ".").replace(".py", "")
    trace_path = TRACES_DIR / f"{module_name}.json"

    try:
        _run_trace_subprocess(module_name, trace_path, cwd=NOTES_DIR)
    except RuntimeError as e:
        return ExecuteResponse(
            run_id=run_id,
            status="error",
            error=str(e)
        )

    with open(trace_path, encoding="utf-8") as f:
        trace = json.load(f)
    steps = len(trace.get("steps", []))

    return ExecuteResponse(
        run_id=run_id,
        status="ok",
        trace_url=f"/api/traces/{module_name}.json",
        steps=steps
    )
