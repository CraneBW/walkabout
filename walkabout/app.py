"""Walkabout FastAPI application."""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from .config import NOTES_DIR, TRACES_DIR, FILES_DIR, ensure_dirs
from .api.notes import router as notes_router
from .api.execute import router as execute_router
from .api.env import router as env_router
from .api.config import router as config_router
from .api.export import router as export_router
from .plugins.manager import PluginManager


def create_app() -> FastAPI:
    ensure_dirs()

    app = FastAPI(title="Walkabout", version="0.1.0")

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

    # Serve trace JSON files
    app.mount("/api/traces", StaticFiles(directory=str(TRACES_DIR)), name="traces")

    # Serve frontend in production mode
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str = ""):
            """Serve the React SPA for all non-API routes."""
            if full_path.startswith("api/"):
                return {"detail": "Not Found"}, 404
            index = frontend_dist / "index.html"
            if index.exists():
                return FileResponse(str(index))
            return {"detail": "Frontend not built. Run: cd frontend && npm install && npm run build"}, 500

    return app
