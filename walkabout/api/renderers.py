"""Renderers API — list registered custom renderers from plugins."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/renderers", tags=["renderers"])


@router.get("")
def list_renderers(request: Request):
    """Return a dict of registered custom renderers.

    Each entry maps type_name -> {type, frontend_js}.
    Frontend JS is gathered from each plugin's get_frontend_components().
    """
    pm = getattr(request.app.state, "plugin_manager", None)
    if pm is None:
        return {}

    registry = getattr(pm, "registry", None)
    if registry is None:
        return {}

    type_names = registry.list()
    result = {}
    for t in type_names:
        result[t] = {"type": t, "frontend_js": None}

    # Enrich with frontend JS from plugins
    for plugin in getattr(pm, "plugins", []):
        try:
            for comp in plugin.get_frontend_components():
                rt = comp.get("renderer_type")
                if rt and rt in result:
                    result[rt]["frontend_js"] = comp.get("js")
                    result[rt]["type"] = rt
        except Exception:
            pass

    return result
