"""SQLite utilities for tracking processed webhook events."""

from contextlib import closing
from typing import Any

from app import database


def _get_table_columns(
    table_name: str,
) -> set[str]:
    """Return the column names belonging to a SQLite table."""
    with closing(database.get_connection()) as connection:
        rows = connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

    return {
        str(row["name"])
        for row in rows
    }


def initialize_webhook_events_table() -> None:
    """Create or safely update the webhook-events table."""
    with closing(database.get_connection()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                inbound_message_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                stored_message_id INTEGER NOT NULL,
                reply TEXT NOT NULL,
                response_provider TEXT NOT NULL DEFAULT 'unknown',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider, inbound_message_id)
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_webhook_events_lookup
            ON webhook_events (
                provider,
                inbound_message_id
            )
            """
        )

        connection.commit()

    columns = _get_table_columns("webhook_events")

    if "response_provider" not in columns:
        with closing(database.get_connection()) as connection:
            connection.execute(
                """
                ALTER TABLE webhook_events
                ADD COLUMN response_provider
                TEXT NOT NULL DEFAULT 'unknown'
                """
            )
            connection.commit()


def normalize_webhook_identifier(
    value: str,
    field_name: str,
) -> str:
    """Validate and normalize a webhook identifier."""
    cleaned_value = value.strip()

    if not cleaned_value:
        raise ValueError(f"{field_name} cannot be empty.")

    return cleaned_value


def get_webhook_event(
    provider: str,
    inbound_message_id: str,
) -> dict[str, Any] | None:
    """Return a previously processed webhook event when present."""
    cleaned_provider = normalize_webhook_identifier(
        provider,
        "Webhook provider",
    )

    cleaned_message_id = normalize_webhook_identifier(
        inbound_message_id,
        "Inbound message ID",
    )

    with closing(database.get_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                id,
                provider,
                inbound_message_id,
                session_id,
                stored_message_id,
                reply,
                response_provider,
                created_at
            FROM webhook_events
            WHERE provider = ?
              AND inbound_message_id = ?
            """,
            (
                cleaned_provider,
                cleaned_message_id,
            ),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def save_webhook_event(
    provider: str,
    inbound_message_id: str,
    session_id: str,
    stored_message_id: int,
    reply: str,
    response_provider: str,
) -> int:
    """Save a processed webhook event and return its database ID."""
    cleaned_provider = normalize_webhook_identifier(
        provider,
        "Webhook provider",
    )

    cleaned_message_id = normalize_webhook_identifier(
        inbound_message_id,
        "Inbound message ID",
    )

    cleaned_session_id = normalize_webhook_identifier(
        session_id,
        "Session ID",
    )

    cleaned_reply = reply.strip()

    cleaned_response_provider = normalize_webhook_identifier(
        response_provider,
        "Response provider",
    )

    if stored_message_id < 1:
        raise ValueError(
            "Stored message ID must be a positive integer."
        )

    if not cleaned_reply:
        raise ValueError("Webhook reply cannot be empty.")

    with closing(database.get_connection()) as connection:
        cursor = connection.execute(
            """
            INSERT INTO webhook_events (
                provider,
                inbound_message_id,
                session_id,
                stored_message_id,
                reply,
                response_provider
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                cleaned_provider,
                cleaned_message_id,
                cleaned_session_id,
                stored_message_id,
                cleaned_reply,
                cleaned_response_provider,
            ),
        )

        connection.commit()
        event_id = cursor.lastrowid

    if event_id is None:
        raise RuntimeError(
            "The database did not return a webhook event ID."
        )

    return int(event_id)