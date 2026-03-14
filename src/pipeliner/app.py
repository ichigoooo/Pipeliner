from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pipeliner.api.router import install_exception_handlers, router
from pipeliner.config import Settings, get_settings
from pipeliner.db import Database
from pipeliner.services.run_drive_coordinator import RunDriveCoordinator


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    db = Database(app_settings)
    run_drive_coordinator = RunDriveCoordinator(db, app_settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        app_settings.ensure_directories()
        db.create_all()
        yield
        run_drive_coordinator.shutdown()
        db.dispose()

    app = FastAPI(title="Pipeliner MVP", version="0.1.0", lifespan=lifespan)
    app.state.settings = app_settings
    app.state.db = db
    app.state.run_drive_coordinator = run_drive_coordinator
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://127.0.0.1:3001",
            "http://localhost:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    install_exception_handlers(app)
    return app
