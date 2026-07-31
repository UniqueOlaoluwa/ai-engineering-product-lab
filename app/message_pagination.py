"""Paginated query utilities for stored conversation messages."""

from contextlib import closing
from typing import Any

from app import database

DEFAULT_MESSAGE_LIMIT = 20
MAX_MESSAGE_LIMIT = 100


def validate_message_pagination(
    limit: int,
    offset: int,
) -> None:
    """Validate message-pagination values."""
    if limit < 1:
        raise ValueError("Message limit must be at least 1.")

    if limit > MAX_MESSAGE_LIMIT:
        raise ValueError(
            f"Message limit cannot exceed {MAX_MESSAGE_LIMIT}."
        )

    if offset < 0:
        raise ValueError("Message offset cannot be negative.")


def count_messages_by_session(session_id: str) -> int:
    """Return the number of stored exchanges in one session."""
    cleaned_session_id = session_id.strip()

    if not cleaned_session_id:
        raise ValueError("Session ID cannot be empty.")

    with closing(database.get_connection()) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM messages
            WHERE session_id = ?
            """,
            (cleaned_session_id,),
        ).fetchone()

    if row is None:
        return 0

    return int(row["total"])


def get_messages_by_session_page(
    session_id: str,
    limit: int = DEFAULT_MESSAGE_LIMIT,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return one paginated page of messages for a session."""
    cleaned_session_id = session_id.strip()

    if not cleaned_session_id:
        raise ValueError("Session ID cannot be empty.")

    validate_message_pagination(
        limit=limit,
        offset=offset,
    )

    with closing(database.get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                session_id,
                role,
                user_message,
                assistant_reply,
                provider,
                created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            LIMIT ?
            OFFSET ?
            """,
            (
                cleaned_session_id,
                limit,
                offset,
            ),
        ).fetchall()

    return [dict(row) for row in rows]