"""Settings API — configure Python path, view settings."""
from fastapi import APIRouter
from pydantic import BaseModel
from ..config import load_settings, save_settings, get_python_path, set_python_path

router = APIRouter(prefix="/api/config", tags=["config"])


class PythonPathUpdate(BaseModel):
    path: str


@router.get("")
def get_config() -> dict:
    s = load_settings()
    s["python_path"] = get_python_path()
    return s


@router.post("/python")
def update_python(body: PythonPathUpdate) -> dict:
    set_python_path(body.path)
    return {"ok": True, "python_path": body.path}
