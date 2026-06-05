"""Walkabout FastAPI application."""
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles as StarletteStaticFiles

from .api.config import router as config_router
from .api.env import router as env_router
from .api.execute import router as execute_router
from .api.export import router as export_router
from .api.notes import router as notes_router
from .config import TRACES_DIR, ensure_dirs
from .plugins.manager import PluginManager


class _NoCacheStaticFiles(StarletteStaticFiles):
    """StaticFiles that sets Cache-Control: no-cache for dev reliability."""
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


def create_app() -> FastAPI:
    ensure_dirs()

    app = FastAPI(title="Walkabout", version="0.2.0")

    # CORS for dev mode (Vite on :5173)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(notes_router)
    app.include_router(execute_router)
    app.include_router(env_router)
    app.include_router(config_router)
    app.include_router(export_router)

    # Load plugins
    pm = PluginManager()
    pm.discover()
    pm.on_startup(app)
    app.state.plugin_manager = pm

    # Serve trace JSON files (no cache for dev reliability)
    app.mount("/api/traces", _NoCacheStaticFiles(directory=str(TRACES_DIR)), name="traces")

    # Serve frontend in production mode
    # When bundled by PyInstaller, sys._MEIPASS points to the temp extraction dir.
    # In development, resolve relative to this source file.
    if getattr(sys, 'frozen', False):
        frontend_dist = Path(sys._MEIPASS) / "frontend" / "dist"
    else:
        frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

    if frontend_dist.exists():
        app.mount("/assets", _NoCacheStaticFiles(directory=str(frontend_dist / "assets")), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str = ""):
            """Serve the React SPA for all non-API routes."""
            if full_path.startswith("api/"):
                return {"detail": "Not Found"}, 404
            index = frontend_dist / "index.html"
            if index.exists():
                resp = FileResponse(str(index))
                resp.headers["Cache-Control"] = "no-cache"
                return resp
            return {"detail": "Frontend not built. Run: cd frontend && npm install && npm run build"}, 500

    return app
