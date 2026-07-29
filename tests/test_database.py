"""Tests for SQLite conversation storage."""

import shutil
from contextlib import closing
from pathlib import Path

import pytest

import app.database as database

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DATABASE_DIR = PROJECT_ROOT / ".test_storage"
TEST_DATABASE_PATH = TEST_DATABASE_DIR / "test_conversations.db"


@pytest.fixture
def isolated_database(
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Use a local ignored database file for each test."""
    if TEST_DATABASE_DIR.exists():
        shutil.rmtree(TEST_DATABASE_DIR)

    TEST_DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(database, "DATABASE_DIR", TEST_DATABASE_DIR)
    monkeypatch.setattr(database, "DATABASE_PATH", TEST_DATABASE_PATH)

    yield TEST_DATABASE_PATH

    if TEST_DATABASE_PATH.exists():
        TEST_DATABASE_PATH.unlink()

    if TEST_DATABASE_DIR.exists():
        TEST_DATABASE_DIR.rmdir()


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

    messages = database.get_messages_by_session("test-session")

    assert isolated_database.exists()
    assert message_id == 1
    assert len(messages) == 1
    assert messages[0]["session_id"] == "test-session"
    assert messages[0]["role"] == "business"
    assert messages[0]["user_message"] == "How can I improve support?"
    assert messages[0]["provider"] == "MockLLMProvider"


def test_get_messages_returns_empty_list_for_unknown_session(
    isolated_database: Path,
) -> None:
    """An unknown session should return an empty list."""
    database.initialize_database()

    messages = database.get_messages_by_session("missing-session")

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