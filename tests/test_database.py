"""Tests for SQLite conversation storage."""

from contextlib import closing
from pathlib import Path
from uuid import uuid4

import pytest

import app.database as database

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DATABASE_DIR = PROJECT_ROOT / ".test_storage"


@pytest.fixture
def isolated_database(
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Redirect database operations to a unique project-local database."""
    TEST_DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    test_database_path = (
        TEST_DATABASE_DIR
        / f"test_conversations_{uuid4().hex}.db"
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

    return test_database_path


def test_initialize_database_creates_messages_table(
    isolated_database: Path,
) -> None:
    """Database initialization should create the messages table."""
    database.initialize_database()

    with closing(database.get_connection()) as connection:
        row = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'messages'
            """
        ).fetchone()

    assert isolated_database.exists()
    assert row is not None
    assert row["name"] == "messages"


def test_save_and_retrieve_message(
    isolated_database: Path,
) -> None:
    """A saved chatbot exchange should be retrievable by session."""
    database.initialize_database()

    message_id = database.save_message(
        session_id="test-session",
        role="business",
        user_message="How can I improve support?",
        assistant_reply="Create a structured FAQ process.",
        provider="MockLLMProvider",
    )

    messages = database.get_messages_by_session(
        "test-session"
    )

    assert isolated_database.exists()
    assert message_id == 1
    assert len(messages) == 1
    assert messages[0]["session_id"] == "test-session"
    assert messages[0]["role"] == "business"
    assert messages[0]["user_message"] == (
        "How can I improve support?"
    )
    assert messages[0]["provider"] == "MockLLMProvider"


def test_get_messages_returns_empty_list_for_unknown_session(
    isolated_database: Path,
) -> None:
    """An unknown session should return an empty list."""
    database.initialize_database()

    messages = database.get_messages_by_session(
        "missing-session"
    )

    assert isolated_database.exists()
    assert messages == []


def test_save_message_rejects_empty_session_id(
    isolated_database: Path,
) -> None:
    """A blank session identifier should be rejected."""
    database.initialize_database()

    with pytest.raises(
        ValueError,
        match="Session ID cannot be empty",
    ):
        database.save_message(
            session_id="   ",
            role="support",
            user_message="Hello",
            assistant_reply="Hi",
            provider="MockLLMProvider",
        )


def test_delete_messages_by_session_removes_all_session_messages(
    isolated_database: Path,
) -> None:
    """Deleting a session should remove all of its messages."""
    database.initialize_database()

    database.save_message(
        session_id="delete-session",
        role="business",
        user_message="First question",
        assistant_reply="First answer",
        provider="MockLLMProvider",
    )

    database.save_message(
        session_id="delete-session",
        role="business",
        user_message="Second question",
        assistant_reply="Second answer",
        provider="MockLLMProvider",
    )

    deleted_count = database.delete_messages_by_session(
        "delete-session"
    )

    remaining_messages = database.get_messages_by_session(
        "delete-session"
    )

    assert isolated_database.exists()
    assert deleted_count == 2
    assert remaining_messages == []


def test_delete_messages_does_not_remove_another_session(
    isolated_database: Path,
) -> None:
    """Deleting one session should not affect another session."""
    database.initialize_database()

    database.save_message(
        session_id="first-session",
        role="business",
        user_message="Delete this message",
        assistant_reply="Delete this reply",
        provider="MockLLMProvider",
    )

    database.save_message(
        session_id="second-session",
        role="support",
        user_message="Keep this message",
        assistant_reply="Keep this reply",
        provider="MockLLMProvider",
    )

    deleted_count = database.delete_messages_by_session(
        "first-session"
    )

    first_messages = database.get_messages_by_session(
        "first-session"
    )

    second_messages = database.get_messages_by_session(
        "second-session"
    )

    assert isolated_database.exists()
    assert deleted_count == 1
    assert first_messages == []
    assert len(second_messages) == 1
    assert second_messages[0]["user_message"] == (
        "Keep this message"
    )


def test_delete_unknown_session_returns_zero(
    isolated_database: Path,
) -> None:
    """Deleting a missing session should return zero."""
    database.initialize_database()

    deleted_count = database.delete_messages_by_session(
        "missing-session"
    )

    assert isolated_database.exists()
    assert deleted_count == 0


def test_delete_messages_rejects_blank_session_id(
    isolated_database: Path,
) -> None:
    """A blank session identifier should not be accepted."""
    database.initialize_database()

    with pytest.raises(
        ValueError,
        match="Session ID cannot be empty",
    ):
        database.delete_messages_by_session("   ")