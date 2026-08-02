"""Tests for webhook-event idempotency storage."""

import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

import app.database as database
from app.webhook_events import (
    get_webhook_event,
    initialize_webhook_events_table,
    save_webhook_event,
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
        / f"webhook_events_{uuid4().hex}.db"
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
    initialize_webhook_events_table()

    return test_database_path


def test_initialize_webhook_events_table(
    isolated_database: Path,
) -> None:
    """Initialization should create the webhook-events table."""
    connection = database.get_connection()

    try:
        table_row = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'webhook_events'
            """
        ).fetchone()

        column_rows = connection.execute(
            """
            PRAGMA table_info(webhook_events)
            """
        ).fetchall()
    finally:
        connection.close()

    columns = {
        row["name"]
        for row in column_rows
    }

    assert isolated_database.exists()
    assert table_row is not None
    assert table_row["name"] == "webhook_events"
    assert "response_provider" in columns


def test_save_and_retrieve_webhook_event(
    isolated_database: Path,
) -> None:
    """A processed event should be retrievable by provider and ID."""
    event_id = save_webhook_event(
        provider="whatsapp",
        inbound_message_id="wamid.test-001",
        session_id="whatsapp-2348012345678",
        stored_message_id=7,
        reply="The clinic is open.",
        response_provider="MockLLMProvider",
    )

    event = get_webhook_event(
        provider="whatsapp",
        inbound_message_id="wamid.test-001",
    )

    assert isolated_database.exists()
    assert event_id == 1
    assert event is not None
    assert event["provider"] == "whatsapp"
    assert event["inbound_message_id"] == "wamid.test-001"
    assert event["session_id"] == "whatsapp-2348012345678"
    assert event["stored_message_id"] == 7
    assert event["reply"] == "The clinic is open."
    assert event["response_provider"] == "MockLLMProvider"


def test_get_unknown_webhook_event_returns_none(
    isolated_database: Path,
) -> None:
    """An unknown event should return None."""
    event = get_webhook_event(
        provider="whatsapp",
        inbound_message_id="wamid.missing",
    )

    assert isolated_database.exists()
    assert event is None


def test_duplicate_provider_message_id_is_rejected(
    isolated_database: Path,
) -> None:
    """The same provider message ID should not be stored twice."""
    save_webhook_event(
        provider="whatsapp",
        inbound_message_id="wamid.duplicate",
        session_id="whatsapp-2348012345678",
        stored_message_id=1,
        reply="First reply.",
        response_provider="MockLLMProvider",
    )

    with pytest.raises(sqlite3.IntegrityError):
        save_webhook_event(
            provider="whatsapp",
            inbound_message_id="wamid.duplicate",
            session_id="whatsapp-2348012345678",
            stored_message_id=2,
            reply="Second reply.",
            response_provider="MockLLMProvider",
        )


def test_same_message_id_can_exist_for_different_provider(
    isolated_database: Path,
) -> None:
    """Provider name should form part of the unique event key."""
    first_id = save_webhook_event(
        provider="whatsapp",
        inbound_message_id="provider-shared-id",
        session_id="whatsapp-2348012345678",
        stored_message_id=1,
        reply="WhatsApp reply.",
        response_provider="MockLLMProvider",
    )

    second_id = save_webhook_event(
        provider="telegram",
        inbound_message_id="provider-shared-id",
        session_id="telegram-123456",
        stored_message_id=2,
        reply="Telegram reply.",
        response_provider="MockLLMProvider",
    )

    assert isolated_database.exists()
    assert first_id == 1
    assert second_id == 2


def test_save_webhook_event_trims_values(
    isolated_database: Path,
) -> None:
    """Surrounding spaces should be removed before storage."""
    save_webhook_event(
        provider="  whatsapp  ",
        inbound_message_id="  wamid.trimmed  ",
        session_id="  whatsapp-2348012345678  ",
        stored_message_id=3,
        reply="  Trimmed reply.  ",
        response_provider="  MockLLMProvider  ",
    )

    event = get_webhook_event(
        provider="whatsapp",
        inbound_message_id="wamid.trimmed",
    )

    assert event is not None
    assert event["provider"] == "whatsapp"
    assert event["session_id"] == "whatsapp-2348012345678"
    assert event["reply"] == "Trimmed reply."
    assert event["response_provider"] == "MockLLMProvider"


def test_save_webhook_event_rejects_invalid_message_id(
    isolated_database: Path,
) -> None:
    """A blank inbound message ID should be rejected."""
    with pytest.raises(
        ValueError,
        match="Inbound message ID cannot be empty",
    ):
        save_webhook_event(
            provider="whatsapp",
            inbound_message_id="   ",
            session_id="whatsapp-2348012345678",
            stored_message_id=1,
            reply="Reply.",
            response_provider="MockLLMProvider",
        )


def test_save_webhook_event_rejects_invalid_stored_message_id(
    isolated_database: Path,
) -> None:
    """A non-positive stored-message ID should be rejected."""
    with pytest.raises(
        ValueError,
        match="must be a positive integer",
    ):
        save_webhook_event(
            provider="whatsapp",
            inbound_message_id="wamid.invalid-stored-id",
            session_id="whatsapp-2348012345678",
            stored_message_id=0,
            reply="Reply.",
            response_provider="MockLLMProvider",
        )


def test_save_webhook_event_rejects_blank_reply(
    isolated_database: Path,
) -> None:
    """A blank webhook reply should be rejected."""
    with pytest.raises(
        ValueError,
        match="Webhook reply cannot be empty",
    ):
        save_webhook_event(
            provider="whatsapp",
            inbound_message_id="wamid.blank-reply",
            session_id="whatsapp-2348012345678",
            stored_message_id=1,
            reply="   ",
            response_provider="MockLLMProvider",
        )


def test_save_webhook_event_rejects_blank_response_provider(
    isolated_database: Path,
) -> None:
    """A blank AI provider name should be rejected."""
    with pytest.raises(
        ValueError,
        match="Response provider cannot be empty",
    ):
        save_webhook_event(
            provider="whatsapp",
            inbound_message_id="wamid.blank-provider",
            session_id="whatsapp-2348012345678",
            stored_message_id=1,
            reply="Reply.",
            response_provider="   ",
        )