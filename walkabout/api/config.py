"""Settings API — schema, get/set, validation, reset."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import (
    SETTINGS_SCHEMA,
    get_defaults,
    load_settings,
    save_settings,
    set_setting,
)

router = APIRouter(prefix="/api/config", tags=["config"])


class SettingUpdate(BaseModel):
    key: str
    value: object


class SettingsUpdate(BaseModel):
    settings: dict


@router.get("/schema")
def get_schema() -> list[dict]:
    return SETTINGS_SCHEMA


@router.get("")
def get_config() -> dict:
    return load_settings()


@router.get("/defaults")
def get_defaults_endpoint() -> dict:
    return get_defaults()


@router.post("/set")
def update_single(body: SettingUpdate) -> dict:
    for item in SETTINGS_SCHEMA:
        if item["key"] == body.key:
            if item["type"] == "boolean" and not isinstance(body.value, bool):
                raise HTTPException(400, f"'{body.key}' expects boolean")
            if item["type"] == "integer" and not isinstance(body.value, int):
                raise HTTPException(400, f"'{body.key}' expects integer")
            if "enum" in item and body.value not in item["enum"]:
                raise HTTPException(400, f"Value must be one of: {item['enum']}")
            break
    else:
        raise HTTPException(400, f"Unknown setting: '{body.key}'")
    set_setting(body.key, body.value)
    return {"ok": True, "key": body.key, "value": body.value}


@router.post("")
def update_all(body: SettingsUpdate) -> dict:
    save_settings(body.settings)
    return {"ok": True}


@router.post("/reset")
def reset_settings() -> dict:
    save_settings({})
    return {"ok": True, "settings": get_defaults()}
