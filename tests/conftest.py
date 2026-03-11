from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pipeliner.app import create_app
from pipeliner.config import Settings
from pipeliner.storage.local_fs import WorkspaceManager


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / ".pipeliner", projects_root=tmp_path / "projects")


@pytest.fixture()
def client(settings: Settings) -> TestClient:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def workflow_fixture() -> dict:
    path = Path("tests/fixtures/workflows/mvp_review_loop.json")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture()
def workspace_manager(settings: Settings) -> WorkspaceManager:
    return WorkspaceManager(settings)
