"""Notes CRUD API — list, read, write, create, delete walkthrough scripts."""
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..config import NOTES_DIR, TRACES_DIR, ensure_dirs

router = APIRouter(prefix="/api/notes", tags=["notes"])


class NoteInfo(BaseModel):
    name: str
    path: str
    modified: float

class NoteContent(BaseModel):
    path: str
    content: str
    trace_url: Optional[str] = None  # Set if a previous trace exists on disk

class CreateNote(BaseModel):
    name: str

class WriteNote(BaseModel):
    content: str


def _ensure_package_init(path: Path) -> None:
    """Ensure every parent directory of *path* under NOTES_DIR has an __init__.py.

    This makes subdirectories importable as Python packages when the
    note is executed via runner.py → importlib.import_module().
    Only directories strictly below NOTES_DIR get __init__.py to avoid
    touching filesystem roots (e.g. /__init__.py).
    """
    notes_root = (NOTES_DIR.resolve())
    for parent in reversed(path.parents):
        if parent == path or parent == path.anchor:
            continue
        try:
            parent.relative_to(notes_root)
        except ValueError:
            continue
        init = parent / "__init__.py"
        if not init.exists():
            init.write_text("", encoding="utf-8")


def _resolve(relpath: str) -> Path:
    """Resolve a relative path to an absolute path under NOTES_DIR.

    Uses Path.relative_to() which is case-insensitive on Windows."""
    p = (NOTES_DIR / relpath).resolve()
    try:
        p.relative_to(NOTES_DIR.resolve())
    except ValueError:
        raise HTTPException(400, "Path traversal not allowed")
    return p


_SKIP_DIRS = frozenset({
    "__pycache__", ".venv", ".git", ".svn", ".hg",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "node_modules", ".tox", ".egg-info",
})


@router.get("")
def list_notes() -> list[NoteInfo]:
    ensure_dirs()
    notes = []
    for root, dirs, files in os.walk(NOTES_DIR):
        # Skip irrelevant directories in-place so os.walk doesn't descend
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for f in files:
            if f.endswith(".py"):
                full = Path(root) / f
                rel = full.relative_to(NOTES_DIR)
                notes.append(NoteInfo(
                    name=str(rel).replace(".py", ""),
                    path=str(rel),
                    modified=full.stat().st_mtime
                ))
    return sorted(notes, key=lambda n: n.name)


@router.get("/{path:path}")
def read_note(path: str) -> NoteContent:
    full = _resolve(path)
    if not full.exists():
        raise HTTPException(404, f"Note not found: {path}")

    # Check if a trace already exists for this note (persist across restarts)
    module_name = path.replace("/", ".").replace(".py", "")
    trace_file = TRACES_DIR / f"{module_name}.json"
    trace_url = f"/api/traces/{module_name}.json" if trace_file.exists() else None

    return NoteContent(path=path, content=full.read_text(encoding="utf-8"), trace_url=trace_url)


@router.put("/{path:path}")
def write_note(path: str, body: WriteNote) -> dict:
    full = _resolve(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    _ensure_package_init(full)
    full.write_text(body.content, encoding="utf-8")
    return {"ok": True, "path": path}


@router.post("")
def create_note(body: CreateNote) -> NoteContent:
    name = body.name
    if not name.endswith(".py"):
        name += ".py"
    full = NOTES_DIR / name
    full.parent.mkdir(parents=True, exist_ok=True)
    _ensure_package_init(full)
    if full.exists():
        raise HTTPException(409, f"Note already exists: {name}")
    full.write_text("# Walkthrough\n\nfrom execute_util import text, image, link\n\ndef main():\n    text('## Hello!')\n    text('Welcome to Walkabout!')\n", encoding="utf-8")
    return NoteContent(path=name, content=full.read_text(encoding="utf-8"))


@router.delete("/{path:path}")
def delete_note(path: str) -> dict:
    full = _resolve(path)
    if not full.exists():
        raise HTTPException(404, f"Note not found: {path}")
    full.unlink()
    return {"ok": True, "path": path}
