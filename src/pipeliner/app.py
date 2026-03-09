from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from pipeliner.api.router import install_exception_handlers, router
from pipeliner.config import Settings, get_settings
from pipeliner.db import Database


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    db = Database(app_settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        app_settings.ensure_directories()
        db.create_all()
        yield
        db.dispose()

    app = FastAPI(title="Pipeliner MVP", version="0.1.0", lifespan=lifespan)
    app.state.settings = app_settings
    app.state.db = db
    app.include_router(router)
    install_exception_handlers(app)
    return app
