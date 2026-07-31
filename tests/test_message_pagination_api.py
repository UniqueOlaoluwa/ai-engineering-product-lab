"""API tests for paginated conversation-message retrieval."""

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.database as database
from app.api import app

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DATABASE_DIR = PROJECT_ROOT / ".test_storage"

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_api_database(
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Give each pagination API test a unique local database."""
    TEST_DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    test_database_path = (
        TEST_DATABASE_DIR
        / f"message_pagination_api_{uuid4().hex}.db"
    )

    monkeypatch.setattr(
        database,
        "DATABASE_DIR",
        TEST_DATABASE_DIR,
    )

    monkeypatch.setattr(
        database,
        "DATABASE_PATH",
        test_database_path,
    )

    database.initialize_database()

    return test_database_path


def create_messages(
    session_id: str,
    count: int,
) -> None:
    """Create synthetic stored messages using the chat endpoint."""
    for number in range(1, count + 1):
        response = client.post(
            "/chat",
            json={
                "message": f"Question {number}",
                "role": "business",
                "session_id": session_id,
                "history_limit": 0,
            },
        )

        assert response.status_code == 200


def test_get_conversation_uses_default_message_pagination() -> None:
    """The endpoint should use default pagination values."""
    session_id = f"default-page-{uuid4()}"
    create_messages(session_id, 3)

    response = client.get(
        f"/conversations/{session_id}"
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["session_id"] == session_id
    assert response_data["total"] == 3
    assert response_data["limit"] == 20
    assert response_data["offset"] == 0
    assert response_data["message_count"] == 3
    assert len(response_data["messages"]) == 3


def test_get_conversation_returns_requested_page() -> None:
    """Limit and offset should select the requested messages."""
    session_id = f"requested-page-{uuid4()}"
    create_messages(session_id, 5)

    response = client.get(
        f"/conversations/{session_id}",
        params={
            "limit": 2,
            "offset": 2,
        },
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["total"] == 5
    assert response_data["limit"] == 2
    assert response_data["offset"] == 2
    assert response_data["message_count"] == 2

    user_messages = [
        message["user_message"]
        for message in response_data["messages"]
    ]

    assert user_messages == [
        "Question 3",
        "Question 4",
    ]


def test_get_conversation_returns_partial_final_page() -> None:
    """The final page may contain fewer messages than the limit."""
    session_id = f"partial-page-{uuid4()}"
    create_messages(session_id, 5)

    response = client.get(
        f"/conversations/{session_id}",
        params={
            "limit": 2,
            "offset": 4,
        },
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["total"] == 5
    assert response_data["message_count"] == 1
    assert response_data["messages"][0]["user_message"] == (
        "Question 5"
    )


def test_get_conversation_returns_empty_page_after_end() -> None:
    """An offset beyond the end should return an empty page."""
    session_id = f"past-end-{uuid4()}"
    create_messages(session_id, 2)

    response = client.get(
        f"/conversations/{session_id}",
        params={
            "limit": 20,
            "offset": 10,
        },
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["total"] == 2
    assert response_data["offset"] == 10
    assert response_data["message_count"] == 0
    assert response_data["messages"] == []


def test_get_conversation_rejects_zero_limit() -> None:
    """A zero message limit should return structured validation."""
    session_id = f"zero-limit-{uuid4()}"

    response = client.get(
        f"/conversations/{session_id}",
        params={
            "limit": 0,
            "offset": 0,
        },
    )

    response_data = response.json()

    assert response.status_code == 422
    assert response_data["error"] == "Request validation failed."
    assert response_data["status_code"] == 422
    assert isinstance(response_data["details"], list)


def test_get_conversation_rejects_limit_above_maximum() -> None:
    """A message limit above one hundred should fail validation."""
    session_id = f"high-limit-{uuid4()}"

    response = client.get(
        f"/conversations/{session_id}",
        params={
            "limit": 101,
            "offset": 0,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"] == "Request validation failed."


def test_get_conversation_rejects_negative_offset() -> None:
    """A negative message offset should fail validation."""
    session_id = f"negative-offset-{uuid4()}"

    response = client.get(
        f"/conversations/{session_id}",
        params={
            "limit": 20,
            "offset": -1,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"] == "Request validation failed."


def test_get_unknown_conversation_still_returns_404() -> None:
    """Pagination should preserve unknown-session behaviour."""
    session_id = f"missing-session-{uuid4()}"
    request_id = "missing-paginated-conversation"

    response = client.get(
        f"/conversations/{session_id}",
        headers={
            "X-Request-ID": request_id,
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": "Conversation session not found.",
        "status_code": 404,
        "request_id": request_id,
    }