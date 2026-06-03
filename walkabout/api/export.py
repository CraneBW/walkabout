"""Export API — generate standalone HTML from a walkthrough trace."""
import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from ..config import NOTES_DIR, TRACES_DIR, ensure_dirs, get_python_path
from ..export import export_note

router = APIRouter(prefix="/api/export", tags=["export"])


class ExportRequest(BaseModel):
    path: str
    content: Optional[str] = None
    title: Optional[str] = None


RUNNER = Path(__file__).parent.parent / "runner.py"

def _run_trace(note_path: Path, module_name: str) -> Path:
    """Execute a note and return the path to its trace JSON."""
    trace_path = TRACES_DIR / f"{module_name}.json"

    env = os.environ.copy()
    walkabout_root = str(Path(__file__).parent.parent.parent)
    walkabout_core = str(Path(__file__).parent.parent / "core")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{walkabout_core}:{walkabout_root}" + (f":{existing}" if existing else "")
    env["WALKABOUT_HOME"] = str(Path.home() / ".walkabout")

    python_exe = get_python_path()
    result = subprocess.run(
        [python_exe, "-u", str(RUNNER),
         "--workspace", str(NOTES_DIR),
         "--module", module_name,
         "--output", str(trace_path)],
        capture_output=True, text=True,
        timeout=60, cwd=str(NOTES_DIR), env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Execution failed")
    if not trace_path.exists():
        raise RuntimeError("Trace file not generated")
    return trace_path


@router.post("")
def export_note_endpoint(req: ExportRequest) -> FileResponse:
    """Run a note and return a standalone HTML file as download."""
    ensure_dirs()

    note_path = NOTES_DIR / req.path
    note_path.parent.mkdir(parents=True, exist_ok=True)
    if req.content is not None:
        note_path.write_text(req.content, encoding="utf-8")
    if not note_path.exists():
        raise HTTPException(404, f"Note not found: {req.path}")

    module_name = req.path.replace("/", ".").replace(".py", "")
    html_name = module_name.replace(".", "_") + ".html"
    html_path = TRACES_DIR / html_name

    try:
        trace_path = _run_trace(note_path, module_name)
        title = req.title or module_name
        export_note(trace_path, html_path, title=title)
    except RuntimeError as e:
        raise HTTPException(500, str(e))

    return FileResponse(
        str(html_path),
        media_type="text/html",
        filename=html_name,
        headers={"Content-Disposition": f'attachment; filename="{html_name}"'},
    )


@router.get("/preview/{path:path}")
def preview_export(path: str) -> FileResponse:
    """Serve a previously exported HTML file for preview."""
    module_name = path.replace("/", ".").replace(".py", "")
    html_name = module_name.replace(".", "_") + ".html"
    html_path = TRACES_DIR / html_name
    if not html_path.exists():
        raise HTTPException(404, "Export not found. Run export first.")
    return FileResponse(str(html_path), media_type="text/html")
