"""Tests for paginated conversation-session listing and search."""

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
    """Redirect operations to a unique project-local database."""
    TEST_DATABASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    test_database_path = (
        TEST_DATABASE_DIR
        / f"conversation_listing_{uuid4().hex}.db"
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
    user_message: str,
) -> int:
    """Save one synthetic message for a listing test."""
    return database.save_message(
        session_id=session_id,
        role="business",
        user_message=user_message,
        assistant_reply=f"Reply to: {user_message}",
        provider="MockLLMProvider",
    )


def test_count_conversation_sessions_returns_distinct_count(
    isolated_database: Path,
) -> None:
    """Multiple messages in one session should count once."""
    save_test_message("session-one", "First message")
    save_test_message("session-one", "Second message")
    save_test_message("session-two", "Third message")

    total = database.count_conversation_sessions()

    assert isolated_database.exists()
    assert total == 2


def test_count_conversation_sessions_returns_zero_when_empty(
    isolated_database: Path,
) -> None:
    """An empty database should contain no conversation sessions."""
    total = database.count_conversation_sessions()

    assert isolated_database.exists()
    assert total == 0


def test_list_conversation_sessions_groups_messages(
    isolated_database: Path,
) -> None:
    """The listing should return one summary per session."""
    save_test_message("grouped-session", "First message")
    save_test_message("grouped-session", "Second message")

    conversations = database.list_conversation_sessions()

    assert isolated_database.exists()
    assert len(conversations) == 1
    assert conversations[0]["session_id"] == "grouped-session"
    assert conversations[0]["message_count"] == 2
    assert conversations[0]["first_created_at"] is not None
    assert conversations[0]["last_created_at"] is not None


def test_list_conversation_sessions_respects_limit(
    isolated_database: Path,
) -> None:
    """The listing should not return more than the requested limit."""
    save_test_message("session-one", "Message one")
    save_test_message("session-two", "Message two")
    save_test_message("session-three", "Message three")

    conversations = database.list_conversation_sessions(
        limit=2,
        offset=0,
    )

    assert isolated_database.exists()
    assert len(conversations) == 2


def test_list_conversation_sessions_respects_offset(
    isolated_database: Path,
) -> None:
    """Pagination offset should skip earlier summary records."""
    save_test_message("session-one", "Message one")
    save_test_message("session-two", "Message two")
    save_test_message("session-three", "Message three")

    first_page = database.list_conversation_sessions(
        limit=2,
        offset=0,
    )

    second_page = database.list_conversation_sessions(
        limit=2,
        offset=2,
    )

    first_page_sessions = {
        item["session_id"]
        for item in first_page
    }

    second_page_sessions = {
        item["session_id"]
        for item in second_page
    }

    assert isolated_database.exists()
    assert len(first_page) == 2
    assert len(second_page) == 1
    assert first_page_sessions.isdisjoint(second_page_sessions)


def test_list_conversation_sessions_returns_empty_when_no_data(
    isolated_database: Path,
) -> None:
    """An empty database should return an empty conversation list."""
    conversations = database.list_conversation_sessions()

    assert isolated_database.exists()
    assert conversations == []


def test_search_filters_session_ids_case_insensitively(
    isolated_database: Path,
) -> None:
    """Search should match session identifiers regardless of case."""
    save_test_message(
        "clinic-reception-demo",
        "Clinic message",
    )
    save_test_message(
        "CLINIC-support-session",
        "Support message",
    )
    save_test_message(
        "retail-automation-demo",
        "Retail message",
    )

    conversations = database.list_conversation_sessions(
        search="clinic",
    )

    session_ids = {
        item["session_id"]
        for item in conversations
    }

    assert isolated_database.exists()
    assert session_ids == {
        "clinic-reception-demo",
        "CLINIC-support-session",
    }


def test_search_returns_partial_session_matches(
    isolated_database: Path,
) -> None:
    """Search should match text appearing within a session ID."""
    save_test_message(
        "customer-clinic-support",
        "Clinic support message",
    )
    save_test_message(
        "customer-retail-support",
        "Retail support message",
    )

    conversations = database.list_conversation_sessions(
        search="clinic",
    )

    assert len(conversations) == 1
    assert conversations[0]["session_id"] == (
        "customer-clinic-support"
    )


def test_search_count_matches_filtered_listing(
    isolated_database: Path,
) -> None:
    """Filtered count should represent matching sessions only."""
    save_test_message("clinic-one", "First clinic message")
    save_test_message("clinic-two", "Second clinic message")
    save_test_message("retail-one", "Retail message")

    total = database.count_conversation_sessions(
        search="clinic",
    )

    conversations = database.list_conversation_sessions(
        search="clinic",
    )

    assert total == 2
    assert len(conversations) == 2


def test_search_combines_with_pagination(
    isolated_database: Path,
) -> None:
    """Search results should still support limit and offset."""
    save_test_message("clinic-one", "Message one")
    save_test_message("clinic-two", "Message two")
    save_test_message("clinic-three", "Message three")
    save_test_message("retail-one", "Retail message")

    first_page = database.list_conversation_sessions(
        limit=2,
        offset=0,
        search="clinic",
    )

    second_page = database.list_conversation_sessions(
        limit=2,
        offset=2,
        search="clinic",
    )

    first_page_ids = {
        item["session_id"]
        for item in first_page
    }

    second_page_ids = {
        item["session_id"]
        for item in second_page
    }

    assert len(first_page) == 2
    assert len(second_page) == 1
    assert first_page_ids.isdisjoint(second_page_ids)

    for session_id in first_page_ids | second_page_ids:
        assert "clinic" in session_id.lower()


def test_search_returns_empty_for_no_matches(
    isolated_database: Path,
) -> None:
    """A valid search with no matches should return an empty list."""
    save_test_message("retail-session", "Retail message")

    total = database.count_conversation_sessions(
        search="clinic",
    )

    conversations = database.list_conversation_sessions(
        search="clinic",
    )

    assert total == 0
    assert conversations == []


def test_search_trims_surrounding_spaces(
    isolated_database: Path,
) -> None:
    """Search should remove accidental surrounding whitespace."""
    save_test_message("clinic-demo", "Clinic message")

    conversations = database.list_conversation_sessions(
        search="  clinic  ",
    )

    assert len(conversations) == 1
    assert conversations[0]["session_id"] == "clinic-demo"


def test_search_rejects_blank_value(
    isolated_database: Path,
) -> None:
    """A search containing only whitespace should be rejected."""
    with pytest.raises(
        ValueError,
        match="Conversation search cannot be blank",
    ):
        database.list_conversation_sessions(
            search="   ",
        )


def test_search_rejects_excessive_length(
    isolated_database: Path,
) -> None:
    """A search longer than 100 characters should be rejected."""
    with pytest.raises(
        ValueError,
        match="Conversation search cannot exceed 100 characters",
    ):
        database.list_conversation_sessions(
            search="a" * 101,
        )


def test_list_conversation_sessions_rejects_zero_limit(
    isolated_database: Path,
) -> None:
    """A zero page limit should be rejected."""
    with pytest.raises(
        ValueError,
        match="Conversation limit must be at least 1",
    ):
        database.list_conversation_sessions(
            limit=0,
            offset=0,
        )


def test_list_conversation_sessions_rejects_excessive_limit(
    isolated_database: Path,
) -> None:
    """A limit above the maximum should be rejected."""
    with pytest.raises(
        ValueError,
        match="Conversation limit cannot exceed 100",
    ):
        database.list_conversation_sessions(
            limit=101,
            offset=0,
        )


def test_list_conversation_sessions_rejects_negative_offset(
    isolated_database: Path,
) -> None:
    """A negative pagination offset should be rejected."""
    with pytest.raises(
        ValueError,
        match="Conversation offset cannot be negative",
    ):
        database.list_conversation_sessions(
            limit=20,
            offset=-1,
        )