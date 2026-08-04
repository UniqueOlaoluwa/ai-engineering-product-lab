"""Persist outbound WhatsApp delivery attempts in SQLite."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.database import DATABASE_PATH

OUTBOUND_PROVIDER = "whatsapp"
DELIVERY_STATUS_PENDING = "pending"
DELIVERY_STATUS_SENT = "sent"
DELIVERY_STATUS_RETRY_PENDING = "retry_pending"

DEFAULT_RETRY_LIMIT = 20
MAX_RETRY_LIMIT = 100


class OutboundDeliveryStorageError(RuntimeError):
    """Represent an outbound-delivery storage failure."""


def get_outbound_delivery_database_path() -> Path:
    """Return the SQLite path used by outbound delivery storage."""
    return DATABASE_PATH


def get_outbound_delivery_connection() -> sqlite3.Connection:
    """Create a configured SQLite connection."""
    database_path = get_outbound_delivery_database_path()

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        database_path,
        timeout=10,
    )

    connection.row_factory = sqlite3.Row

    return connection


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO format."""
    return datetime.now(UTC).isoformat()


def initialize_outbound_deliveries_table() -> None:
    """Create the outbound-delivery table and indexes."""
    with closing(
        get_outbound_delivery_connection()
    ) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS outbound_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                inbound_message_id TEXT NOT NULL,
                recipient_phone TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL,
                delivery_provider TEXT,
                outbound_message_id TEXT,
                error TEXT,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                sent_at TEXT,
                UNIQUE(provider, inbound_message_id)
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_outbound_deliveries_status
            ON outbound_deliveries(status)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_outbound_deliveries_recipient
            ON outbound_deliveries(recipient_phone)
            """
        )

        connection.commit()


def row_to_dictionary(
    row: sqlite3.Row,
) -> dict[str, Any]:
    """Convert a SQLite row into a plain dictionary."""
    return dict(row)


def create_outbound_delivery(
    inbound_message_id: str,
    recipient_phone: str,
    message: str,
    provider: str = OUTBOUND_PROVIDER,
) -> int:
    """Create one pending outbound-delivery record."""
    timestamp = utc_now_iso()

    try:
        with closing(
            get_outbound_delivery_connection()
        ) as connection:
            cursor = connection.execute(
                """
                INSERT INTO outbound_deliveries (
                    provider,
                    inbound_message_id,
                    recipient_phone,
                    message,
                    status,
                    attempt_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    provider,
                    inbound_message_id,
                    recipient_phone,
                    message,
                    DELIVERY_STATUS_PENDING,
                    0,
                    timestamp,
                    timestamp,
                ),
            )

            connection.commit()

            return int(cursor.lastrowid)

    except sqlite3.IntegrityError as error:
        raise OutboundDeliveryStorageError(
            "Outbound delivery already exists for this "
            "provider and inbound message ID."
        ) from error

    except sqlite3.Error as error:
        raise OutboundDeliveryStorageError(
            f"Unable to create outbound delivery: {error}"
        ) from error


def get_outbound_delivery(
    provider: str,
    inbound_message_id: str,
) -> dict[str, Any] | None:
    """Return one outbound-delivery record."""
    try:
        with closing(
            get_outbound_delivery_connection()
        ) as connection:
            row = connection.execute(
                """
                SELECT *
                FROM outbound_deliveries
                WHERE provider = ?
                  AND inbound_message_id = ?
                """,
                (
                    provider,
                    inbound_message_id,
                ),
            ).fetchone()

            if row is None:
                return None

            return row_to_dictionary(row)

    except sqlite3.Error as error:
        raise OutboundDeliveryStorageError(
            f"Unable to read outbound delivery: {error}"
        ) from error


def mark_outbound_delivery_sent(
    provider: str,
    inbound_message_id: str,
    delivery_provider: str,
    outbound_message_id: str,
) -> bool:
    """Mark one delivery as successfully sent."""
    timestamp = utc_now_iso()

    try:
        with closing(
            get_outbound_delivery_connection()
        ) as connection:
            cursor = connection.execute(
                """
                UPDATE outbound_deliveries
                SET status = ?,
                    delivery_provider = ?,
                    outbound_message_id = ?,
                    error = NULL,
                    attempt_count = attempt_count + 1,
                    updated_at = ?,
                    sent_at = ?
                WHERE provider = ?
                  AND inbound_message_id = ?
                """,
                (
                    DELIVERY_STATUS_SENT,
                    delivery_provider,
                    outbound_message_id,
                    timestamp,
                    timestamp,
                    provider,
                    inbound_message_id,
                ),
            )

            connection.commit()

            return cursor.rowcount > 0

    except sqlite3.Error as error:
        raise OutboundDeliveryStorageError(
            f"Unable to mark outbound delivery as sent: {error}"
        ) from error


def mark_outbound_delivery_failed(
    provider: str,
    inbound_message_id: str,
    error_message: str,
) -> bool:
    """Mark one failed delivery as waiting for retry."""
    timestamp = utc_now_iso()

    try:
        with closing(
            get_outbound_delivery_connection()
        ) as connection:
            cursor = connection.execute(
                """
                UPDATE outbound_deliveries
                SET status = ?,
                    error = ?,
                    attempt_count = attempt_count + 1,
                    updated_at = ?
                WHERE provider = ?
                  AND inbound_message_id = ?
                """,
                (
                    DELIVERY_STATUS_RETRY_PENDING,
                    error_message,
                    timestamp,
                    provider,
                    inbound_message_id,
                ),
            )

            connection.commit()

            return cursor.rowcount > 0

    except sqlite3.Error as error:
        raise OutboundDeliveryStorageError(
            f"Unable to mark outbound delivery as failed: {error}"
        ) from error


def list_retry_pending_deliveries(
    limit: int = DEFAULT_RETRY_LIMIT,
) -> list[dict[str, Any]]:
    """Return retryable deliveries ordered from oldest to newest."""
    if limit < 1:
        raise ValueError(
            "Retry delivery limit must be at least 1."
        )

    if limit > MAX_RETRY_LIMIT:
        raise ValueError(
            f"Retry delivery limit cannot exceed {MAX_RETRY_LIMIT}."
        )

    try:
        with closing(
            get_outbound_delivery_connection()
        ) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM outbound_deliveries
                WHERE status = ?
                ORDER BY updated_at ASC, id ASC
                LIMIT ?
                """,
                (
                    DELIVERY_STATUS_RETRY_PENDING,
                    limit,
                ),
            ).fetchall()

            return [
                row_to_dictionary(row)
                for row in rows
            ]

    except sqlite3.Error as error:
        raise OutboundDeliveryStorageError(
            f"Unable to list retry deliveries: {error}"
        ) from error


def delete_outbound_delivery(
    provider: str,
    inbound_message_id: str,
) -> bool:
    """Delete one outbound-delivery record."""
    try:
        with closing(
            get_outbound_delivery_connection()
        ) as connection:
            cursor = connection.execute(
                """
                DELETE FROM outbound_deliveries
                WHERE provider = ?
                  AND inbound_message_id = ?
                """,
                (
                    provider,
                    inbound_message_id,
                ),
            )

            connection.commit()

            return cursor.rowcount > 0

    except sqlite3.Error as error:
        raise OutboundDeliveryStorageError(
            f"Unable to delete outbound delivery: {error}"
        ) from error