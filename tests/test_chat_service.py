"""Tests for the reusable chatbot application service."""

from pathlib import Path
from uuid import uuid4

import pytest

import app.database as database
from app.chat_service import (
    ChatServiceResult,
    process_chat_message,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DATABASE_DIR = PROJECT_ROOT / ".test_storage"


@pytest.fixture
def isolated_database(
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Give each service test a unique project-local database."""
    TEST_DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    test_database_path = (
        TEST_DATABASE_DIR
        / f"chat_service_{uuid4().hex}.db"
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


def test_process_chat_message_returns_service_result(
    isolated_database: Path,
) -> None:
    """A valid message should return a structured service result."""
    result = process_chat_message(
        message="Help me improve customer support.",
        role="business",
        session_id="service-result-session",
        history_limit=0,
    )

    assert isolated_database.exists()
    assert isinstance(result, ChatServiceResult)
    assert result.message_id == 1
    assert result.session_id == "service-result-session"
    assert result.role == "business"
    assert result.role_name == "Business Assistant"
    assert result.provider == "MockLLMProvider"
    assert "Help me improve customer support." in result.reply


def test_process_chat_message_saves_exchange(
    isolated_database: Path,
) -> None:
    """The processed exchange should be stored in SQLite."""
    process_chat_message(
        message="What is an AI agent?",
        role="business",
        session_id="stored-service-session",
        history_limit=0,
    )

    messages = database.get_messages_by_session(
        "stored-service-session"
    )

    assert isolated_database.exists()
    assert len(messages) == 1
    assert messages[0]["user_message"] == "What is an AI agent?"
    assert messages[0]["role"] == "business"
    assert messages[0]["provider"] == "MockLLMProvider"


def test_process_chat_message_normalizes_unknown_role(
    isolated_database: Path,
) -> None:
    """An unsupported role should fall back to support."""
    result = process_chat_message(
        message="When are you open?",
        role="unknown-role",
        session_id="fallback-service-session",
        history_limit=0,
    )

    assert isolated_database.exists()
    assert result.role == "support"
    assert result.role_name == "Customer Support Assistant"


def test_process_chat_message_uses_previous_context(
    isolated_database: Path,
) -> None:
    """A follow-up should include earlier session context."""
    first_result = process_chat_message(
        message="What is workflow automation?",
        role="business",
        session_id="context-service-session",
        history_limit=5,
    )

    second_result = process_chat_message(
        message="Give me a clinic example.",
        role="business",
        session_id="context-service-session",
        history_limit=5,
    )

    assert isolated_database.exists()
    assert first_result.message_id == 1
    assert second_result.message_id == 2
    assert "Previous conversation context:" in second_result.reply
    assert "What is workflow automation?" in second_result.reply
    assert "Give me a clinic example." in second_result.reply


def test_process_chat_message_can_disable_context(
    isolated_database: Path,
) -> None:
    """A zero history limit should exclude previous messages."""
    process_chat_message(
        message="Remember this message.",
        role="business",
        session_id="disabled-context-session",
        history_limit=5,
    )

    result = process_chat_message(
        message="Respond without earlier context.",
        role="business",
        session_id="disabled-context-session",
        history_limit=0,
    )

    assert isolated_database.exists()
    assert "Previous conversation context:" not in result.reply
    assert "Remember this message." not in result.reply


def test_process_chat_message_keeps_sessions_isolated(
    isolated_database: Path,
) -> None:
    """One session should not inherit another session's history."""
    process_chat_message(
        message="Private first-session content.",
        role="business",
        session_id="first-service-session",
        history_limit=5,
    )

    result = process_chat_message(
        message="Start an unrelated conversation.",
        role="business",
        session_id="second-service-session",
        history_limit=5,
    )

    assert isolated_database.exists()
    assert "Private first-session content." not in result.reply
    assert "Previous conversation context:" not in result.reply


def test_process_chat_message_trims_message_and_session(
    isolated_database: Path,
) -> None:
    """Surrounding spaces should not be stored."""
    result = process_chat_message(
        message="  Trim this message.  ",
        role="business",
        session_id="  trimmed-service-session  ",
        history_limit=0,
    )

    messages = database.get_messages_by_session(
        "trimmed-service-session"
    )

    assert isolated_database.exists()
    assert result.session_id == "trimmed-service-session"
    assert len(messages) == 1
    assert messages[0]["user_message"] == "Trim this message."


def test_process_chat_message_rejects_blank_message(
    isolated_database: Path,
) -> None:
    """A blank message should be rejected."""
    with pytest.raises(
        ValueError,
        match="Message cannot be empty",
    ):
        process_chat_message(
            message="   ",
            role="support",
            session_id="blank-message-session",
            history_limit=5,
        )


def test_process_chat_message_rejects_blank_session(
    isolated_database: Path,
) -> None:
    """A blank session identifier should be rejected."""
    with pytest.raises(
        ValueError,
        match="Session ID cannot be empty",
    ):
        process_chat_message(
            message="Hello",
            role="support",
            session_id="   ",
            history_limit=5,
        )


def test_process_chat_message_rejects_negative_history_limit(
    isolated_database: Path,
) -> None:
    """A negative history limit should be rejected."""
    with pytest.raises(
        ValueError,
        match="History limit cannot be negative",
    ):
        process_chat_message(
            message="Hello",
            role="support",
            session_id="negative-history-session",
            history_limit=-1,
        )


def test_process_chat_message_rejects_excessive_history_limit(
    isolated_database: Path,
) -> None:
    """A history limit above twenty should be rejected."""
    with pytest.raises(
        ValueError,
        match="History limit cannot exceed 20",
    ):
        process_chat_message(
            message="Hello",
            role="support",
            session_id="high-history-session",
            history_limit=21,
        )