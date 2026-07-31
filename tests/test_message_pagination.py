"""Tests for paginating messages within one conversation."""

from pathlib import Path
from uuid import uuid4

import pytest

import app.database as database
from app.message_pagination import (
    count_messages_by_session,
    get_messages_by_session_page,
    validate_message_pagination,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DATABASE_DIR = PROJECT_ROOT / ".test_storage"


@pytest.fixture
def isolated_database(
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Use a unique project-local SQLite database for each test."""
    TEST_DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    test_database_path = (
        TEST_DATABASE_DIR
        / f"message_pagination_{uuid4().hex}.db"
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


def save_test_message(
    session_id: str,
    number: int,
) -> int:
    """Save one synthetic exchange for pagination tests."""
    return database.save_message(
        session_id=session_id,
        role="business",
        user_message=f"Question {number}",
        assistant_reply=f"Answer {number}",
        provider="MockLLMProvider",
    )


def test_count_messages_returns_session_total(
    isolated_database: Path,
) -> None:
    """Message counting should include every exchange in a session."""
    for number in range(1, 4):
        save_test_message(
            session_id="count-session",
            number=number,
        )

    total = count_messages_by_session("count-session")

    assert isolated_database.exists()
    assert total == 3


def test_count_messages_does_not_include_other_sessions(
    isolated_database: Path,
) -> None:
    """Message counting should remain isolated by session ID."""
    save_test_message("first-session", 1)
    save_test_message("first-session", 2)
    save_test_message("second-session", 1)

    total = count_messages_by_session("first-session")

    assert isolated_database.exists()
    assert total == 2


def test_count_messages_returns_zero_for_unknown_session(
    isolated_database: Path,
) -> None:
    """An unknown session should have a message count of zero."""
    total = count_messages_by_session("missing-session")

    assert isolated_database.exists()
    assert total == 0


def test_get_message_page_respects_limit(
    isolated_database: Path,
) -> None:
    """A page should not exceed the requested limit."""
    for number in range(1, 6):
        save_test_message("limited-session", number)

    messages = get_messages_by_session_page(
        session_id="limited-session",
        limit=2,
        offset=0,
    )

    assert isolated_database.exists()
    assert len(messages) == 2
    assert messages[0]["user_message"] == "Question 1"
    assert messages[1]["user_message"] == "Question 2"


def test_get_message_page_respects_offset(
    isolated_database: Path,
) -> None:
    """Offset should skip earlier messages."""
    for number in range(1, 6):
        save_test_message("offset-session", number)

    messages = get_messages_by_session_page(
        session_id="offset-session",
        limit=2,
        offset=2,
    )

    assert isolated_database.exists()
    assert len(messages) == 2
    assert messages[0]["user_message"] == "Question 3"
    assert messages[1]["user_message"] == "Question 4"


def test_get_final_partial_page(
    isolated_database: Path,
) -> None:
    """The final page may contain fewer messages than the limit."""
    for number in range(1, 6):
        save_test_message("final-page-session", number)

    messages = get_messages_by_session_page(
        session_id="final-page-session",
        limit=2,
        offset=4,
    )

    assert isolated_database.exists()
    assert len(messages) == 1
    assert messages[0]["user_message"] == "Question 5"


def test_get_message_page_returns_empty_after_end(
    isolated_database: Path,
) -> None:
    """An offset beyond the session should return an empty page."""
    save_test_message("short-session", 1)

    messages = get_messages_by_session_page(
        session_id="short-session",
        limit=20,
        offset=10,
    )

    assert isolated_database.exists()
    assert messages == []


def test_get_message_page_does_not_mix_sessions(
    isolated_database: Path,
) -> None:
    """A page should contain messages only from its requested session."""
    save_test_message("requested-session", 1)
    save_test_message("other-session", 1)

    messages = get_messages_by_session_page(
        session_id="requested-session",
    )

    assert isolated_database.exists()
    assert len(messages) == 1
    assert messages[0]["session_id"] == "requested-session"


def test_validate_message_pagination_rejects_zero_limit() -> None:
    """A zero message limit should be rejected."""
    with pytest.raises(
        ValueError,
        match="Message limit must be at least 1",
    ):
        validate_message_pagination(
            limit=0,
            offset=0,
        )


def test_validate_message_pagination_rejects_high_limit() -> None:
    """A message limit above one hundred should be rejected."""
    with pytest.raises(
        ValueError,
        match="Message limit cannot exceed 100",
    ):
        validate_message_pagination(
            limit=101,
            offset=0,
        )


def test_validate_message_pagination_rejects_negative_offset() -> None:
    """A negative message offset should be rejected."""
    with pytest.raises(
        ValueError,
        match="Message offset cannot be negative",
    ):
        validate_message_pagination(
            limit=20,
            offset=-1,
        )


def test_message_queries_reject_blank_session_id(
    isolated_database: Path,
) -> None:
    """Message queries should reject a blank session ID."""
    with pytest.raises(
        ValueError,
        match="Session ID cannot be empty",
    ):
        count_messages_by_session("   ")

    with pytest.raises(
        ValueError,
        match="Session ID cannot be empty",
    ):
        get_messages_by_session_page(
            session_id="   ",
        )