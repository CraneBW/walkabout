"""Notes CRUD API — list, read, write, create, delete walkthrough scripts."""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..config import NOTES_DIR, ensure_dirs

router = APIRouter(prefix="/api/notes", tags=["notes"])


class NoteInfo(BaseModel):
    name: str
    path: str
    modified: float

class NoteContent(BaseModel):
    path: str
    content: str

class CreateNote(BaseModel):
    name: str

class WriteNote(BaseModel):
    content: str


def _resolve(relpath: str) -> Path:
    """Resolve a relative path to an absolute path under NOTES_DIR."""
    p = (NOTES_DIR / relpath).resolve()
    if not str(p).startswith(str(NOTES_DIR.resolve())):
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
    return NoteContent(path=path, content=full.read_text(encoding="utf-8"))


@router.put("/{path:path}")
def write_note(path: str, body: WriteNote) -> dict:
    full = _resolve(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(body.content, encoding="utf-8")
    return {"ok": True, "path": path}


@router.post("")
def create_note(body: CreateNote) -> NoteContent:
    name = body.name
    if not name.endswith(".py"):
        name += ".py"
    full = NOTES_DIR / name
    full.parent.mkdir(parents=True, exist_ok=True)
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
