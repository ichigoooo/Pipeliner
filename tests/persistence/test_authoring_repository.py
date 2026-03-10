from __future__ import annotations

import pytest

from pipeliner.db import Database
from pipeliner.persistence.models import AuthoringSessionModel, AuthoringDraftModel
from pipeliner.persistence.repositories import AuthoringRepository


@pytest.fixture()
def repository(settings) -> AuthoringRepository:
    # Use real db for integration test
    from pathlib import Path
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    db = Database(settings)
    db.create_all()
    session = db.session_factory()
    yield AuthoringRepository(session)
    session.close()

def test_authoring_repository_session_lifecycle(repository: AuthoringRepository):
    # 1. Create a session
    session = repository.create_session(
        session_id="session-123",
        title="Test Session",
        intent_brief="I want a simple pipeline",
    )
    assert session.id == "session-123"
    assert session.title == "Test Session"
    assert session.status == "active"

    # 2. Get the session
    fetched = repository.get_session("session-123")
    assert fetched is not None
    assert fetched.title == "Test Session"

    # 3. List sessions
    sessions = repository.list_sessions(status="active")
    assert len(sessions) == 1
    assert sessions[0].id == "session-123"

def test_authoring_repository_draft_lifecycle(repository: AuthoringRepository):
    # Setup session
    repository.create_session(
        session_id="session-456",
        title="Draft Test",
        intent_brief="Testing drafts",
    )

    # 1. Create a draft
    mock_spec = {"nodes": [], "edges": []}
    draft = repository.create_draft(
        session_id="session-456",
        revision=1,
        spec_json=mock_spec,
        workflow_view_json={"cards": []},
        graph_json={"nodes": [], "edges": []},
        lint_report_json={"warnings": ["Empty nodes"], "errors": [], "blocking": False},
        lint_warnings=["Empty nodes"],
    )
    assert draft.session_id == "session-456"
    assert draft.revision == 1
    assert draft.spec_json == mock_spec
    assert draft.graph_json["nodes"] == []
    assert len(draft.lint_warnings) == 1

    # 2. Add second draft
    repository.create_draft(
        session_id="session-456",
        revision=2,
        spec_json={"nodes": [{"id": "Start"}]},
        workflow_view_json={"cards": [{"node_id": "Start"}]},
        graph_json={"nodes": [{"id": "Start"}], "edges": []},
        lint_report_json={"warnings": [], "errors": [], "blocking": False},
        lint_warnings=[],
    )

    # 3. Get draft
    fetched = repository.get_draft("session-456", 1)
    assert fetched is not None
    assert fetched.revision == 1

    # 4. Get latest draft
    latest = repository.get_latest_draft("session-456")
    assert latest is not None
    assert latest.revision == 2

    repository.add_message("session-456", role="user", content="Update draft", revision=2)
    messages = repository.list_messages("session-456")
    assert len(messages) == 1
    assert messages[0].content == "Update draft"
