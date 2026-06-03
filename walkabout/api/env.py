"""Environment management — uv-based Python package installation."""
from __future__ import annotations
import subprocess, os, shutil, json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..config import NOTES_DIR

router = APIRouter(prefix="/api/env", tags=["env"])


class InstallRequest(BaseModel):
    packages: list[str]


class EnvInfo(BaseModel):
    python: str
    venv: str | None
    packages: list[str]


def _find_uv() -> str | None:
    return shutil.which("uv")


def _get_venv_python() -> str | None:
    for base in [NOTES_DIR, Path.home() / ".walkabout"]:
        venv = base / ".venv" / "bin" / "python3"
        if venv.exists():
            return str(venv)
    return None


def _get_system_python() -> str:
    venv = _get_venv_python()
    if venv:
        return venv
    return shutil.which("python3") or shutil.which("python") or "python3"


@router.get("")
def get_env_info() -> EnvInfo:
    python = _get_system_python()
    venv = _get_venv_python()
    packages = []
    try:
        result = subprocess.run(
            [python, "-m", "pip", "list", "--format=json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            packages = [p["name"] for p in json.loads(result.stdout)]
    except Exception:
        pass
    return EnvInfo(python=python, venv=venv, packages=packages)


@router.post("/install")
def install_packages(req: InstallRequest) -> dict:
    uv = _find_uv()
    python = _get_system_python()
    workspace = str(Path.home() / ".walkabout")
    packages = req.packages
    if not packages:
        raise HTTPException(400, "No packages specified")

    try:
        if uv:
            cmd = [uv, "pip", "install"] + packages
            venv_python = _get_venv_python()
            if venv_python:
                cmd.extend(["--python", venv_python])
            else:
                cwd = Path.home() / ".walkabout"
                subprocess.run(
                    [uv, "venv", str(cwd / ".venv")],
                    capture_output=True, text=True, timeout=30, cwd=str(cwd)
                )
                new_venv = str(cwd / ".venv" / "bin" / "python3")
                cmd.extend(["--python", new_venv])
        else:
            cmd = [python, "-m", "pip", "install"] + packages

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, cwd=workspace
        )
        if result.returncode != 0:
            raise HTTPException(500, f"Install failed: {result.stderr.strip()[-500:]}")
        return {"ok": True, "packages": packages, "output": (result.stdout + result.stderr).strip()[-500:]}
    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(408, "Install timed out")
    except Exception as e:
        raise HTTPException(500, str(e))
