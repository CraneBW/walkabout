"""Export API — generate standalone HTML from a walkthrough trace."""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..config import NOTES_DIR, TRACES_DIR, ensure_dirs, load_settings
from ..export import export_note
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

router = APIRouter(prefix="/api/export", tags=["export"])


class ExportRequest(BaseModel):
    path: str
    content: Optional[str] = None
    title: Optional[str] = None
    content_only: bool = False  # preserve source code and env panel by default


@router.get("")
def export_note_get(path: str, title: Optional[str] = None) -> FileResponse:
    """Generate and download standalone HTML from an existing trace (GET version)."""
    ensure_dirs()

    module_name = path.replace("/", ".").replace(".py", "")
    trace_path = TRACES_DIR / f"{module_name}.json"
    if not trace_path.exists():
        raise HTTPException(404, "No trace found. Run the note first, then export.")

    html_name = module_name.replace(".", "_") + ".html"
    html_path = TRACES_DIR / html_name

    name = title or module_name
    export_note(trace_path, html_path, title=name, strip_source=False)

    return FileResponse(
        str(html_path),
        media_type="text/html",
        filename=html_name,
        headers={"Content-Disposition": f'attachment; filename="{html_name}"'},
    )


@router.post("")
def export_note_endpoint(req: ExportRequest) -> FileResponse:
    """Run a note and return a standalone HTML file as download."""
    ensure_dirs()

    note_path = _resolve(req.path)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    if req.content is not None:
        note_path.write_text(req.content, encoding="utf-8")
    if not note_path.exists():
        raise HTTPException(404, f"Note not found: {req.path}")

    module_name = req.path.replace("/", ".").replace(".py", "")
    html_name = module_name.replace(".", "_") + ".html"
    html_path = TRACES_DIR / html_name

    try:
        trace_path = TRACES_DIR / f"{module_name}.json"
        _run_trace_subprocess(module_name, trace_path, cwd=NOTES_DIR)
        title = req.title or module_name
        export_note(trace_path, html_path, title=title, strip_source=False)
    except RuntimeError as e:
        raise HTTPException(500, str(e)) from e

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


@router.post("/save")
def export_and_save(req: ExportRequest) -> dict:
    """Generate standalone HTML and save to the configured export directory.

    Returns the absolute path to the saved file so the UI can show it.
    """
    ensure_dirs()

    note_path = _resolve(req.path)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    if req.content is not None:
        note_path.write_text(req.content, encoding="utf-8")
    if not note_path.exists():
        raise HTTPException(404, f"Note not found: {req.path}")

    module_name = req.path.replace("/", ".").replace(".py", "")
    html_name = module_name.replace(".", "_") + ".html"

    # Determine export directory from settings (default: ~/.walkabout/exports)
    settings = load_settings()
    export_dir = settings.get("export", {}).get("directory", "") or ""
    export_path = Path(export_dir) if export_dir else Path.home() / ".walkabout" / "exports"
    export_path.mkdir(parents=True, exist_ok=True)
    html_path = export_path / html_name

    try:
        trace_path = TRACES_DIR / f"{module_name}.json"
        _run_trace_subprocess(module_name, trace_path, cwd=NOTES_DIR)
        title = req.title or module_name
        export_note(trace_path, html_path, title=title, strip_source=True, content_only=req.content_only)
    except RuntimeError as e:
        raise HTTPException(500, str(e)) from e

    return {"path": str(html_path)}
