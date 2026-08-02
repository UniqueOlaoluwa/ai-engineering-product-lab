"""SQLite database utilities for storing chatbot conversations."""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_DIR = PROJECT_ROOT / "storage"
DATABASE_PATH = DATABASE_DIR / "conversations.db"

DEFAULT_CONVERSATION_LIMIT = 20
MAX_CONVERSATION_LIMIT = 100
MAX_CONVERSATION_SEARCH_LENGTH = 100


def get_connection() -> sqlite3.Connection:
    """Create and return a configured SQLite connection."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database() -> None:
    """Create the required database tables and indexes."""
    with closing(get_connection()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                user_message TEXT NOT NULL,
                assistant_reply TEXT NOT NULL,
                provider TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_session_id
            ON messages (session_id)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_created_at
            ON messages (created_at)
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                inbound_message_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                stored_message_id INTEGER NOT NULL,
                reply TEXT NOT NULL,
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


def save_message(
    session_id: str,
    role: str,
    user_message: str,
    assistant_reply: str,
    provider: str,
) -> int:
    """Save a chatbot exchange and return its database ID."""
    cleaned_session_id = session_id.strip()
    cleaned_role = role.strip()
    cleaned_user_message = user_message.strip()
    cleaned_assistant_reply = assistant_reply.strip()
    cleaned_provider = provider.strip()

    if not cleaned_session_id:
        raise ValueError("Session ID cannot be empty.")

    if not cleaned_role:
        raise ValueError("Role cannot be empty.")

    if not cleaned_user_message:
        raise ValueError("User message cannot be empty.")

    if not cleaned_assistant_reply:
        raise ValueError("Assistant reply cannot be empty.")

    if not cleaned_provider:
        raise ValueError("Provider cannot be empty.")

    with closing(get_connection()) as connection:
        cursor = connection.execute(
            """
            INSERT INTO messages (
                session_id,
                role,
                user_message,
                assistant_reply,
                provider
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                cleaned_session_id,
                cleaned_role,
                cleaned_user_message,
                cleaned_assistant_reply,
                cleaned_provider,
            ),
        )

        connection.commit()
        message_id = cursor.lastrowid

    if message_id is None:
        raise RuntimeError("The database did not return a message ID.")

    return int(message_id)


def get_messages_by_session(
    session_id: str,
) -> list[dict[str, Any]]:
    """Return all saved messages for a session."""
    cleaned_session_id = session_id.strip()

    if not cleaned_session_id:
        raise ValueError("Session ID cannot be empty.")

    with closing(get_connection()) as connection:
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
            """,
            (cleaned_session_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def delete_messages_by_session(session_id: str) -> int:
    """Delete all messages for a session and return the deleted count."""
    cleaned_session_id = session_id.strip()

    if not cleaned_session_id:
        raise ValueError("Session ID cannot be empty.")

    with closing(get_connection()) as connection:
        cursor = connection.execute(
            """
            DELETE FROM messages
            WHERE session_id = ?
            """,
            (cleaned_session_id,),
        )

        connection.commit()
        deleted_count = cursor.rowcount

    return max(deleted_count, 0)


def validate_conversation_pagination(
    limit: int,
    offset: int,
) -> None:
    """Validate pagination values used when listing conversations."""
    if limit < 1:
        raise ValueError("Conversation limit must be at least 1.")

    if limit > MAX_CONVERSATION_LIMIT:
        raise ValueError(
            "Conversation limit cannot exceed "
            f"{MAX_CONVERSATION_LIMIT}."
        )

    if offset < 0:
        raise ValueError("Conversation offset cannot be negative.")


def normalize_conversation_search(
    search: str | None,
) -> str | None:
    """Validate and normalize an optional conversation search value."""
    if search is None:
        return None

    cleaned_search = search.strip()

    if not cleaned_search:
        raise ValueError("Conversation search cannot be blank.")

    if len(cleaned_search) > MAX_CONVERSATION_SEARCH_LENGTH:
        raise ValueError(
            "Conversation search cannot exceed "
            f"{MAX_CONVERSATION_SEARCH_LENGTH} characters."
        )

    return cleaned_search


def count_conversation_sessions(
    search: str | None = None,
) -> int:
    """Return the number of distinct matching conversation sessions."""
    cleaned_search = normalize_conversation_search(search)

    with closing(get_connection()) as connection:
        if cleaned_search is None:
            row = connection.execute(
                """
                SELECT COUNT(DISTINCT session_id) AS total
                FROM messages
                """
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT COUNT(DISTINCT session_id) AS total
                FROM messages
                WHERE LOWER(session_id) LIKE LOWER(?)
                """,
                (f"%{cleaned_search}%",),
            ).fetchone()

    if row is None:
        return 0

    return int(row["total"])


def list_conversation_sessions(
    limit: int = DEFAULT_CONVERSATION_LIMIT,
    offset: int = 0,
    search: str | None = None,
) -> list[dict[str, Any]]:
    """Return paginated and optionally filtered conversation summaries."""
    validate_conversation_pagination(limit, offset)
    cleaned_search = normalize_conversation_search(search)

    with closing(get_connection()) as connection:
        if cleaned_search is None:
            rows = connection.execute(
                """
                SELECT
                    session_id,
                    COUNT(*) AS message_count,
                    MIN(created_at) AS first_created_at,
                    MAX(created_at) AS last_created_at
                FROM messages
                GROUP BY session_id
                ORDER BY last_created_at DESC, MAX(id) DESC
                LIMIT ?
                OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT
                    session_id,
                    COUNT(*) AS message_count,
                    MIN(created_at) AS first_created_at,
                    MAX(created_at) AS last_created_at
                FROM messages
                WHERE LOWER(session_id) LIKE LOWER(?)
                GROUP BY session_id
                ORDER BY last_created_at DESC, MAX(id) DESC
                LIMIT ?
                OFFSET ?
                """,
                (
                    f"%{cleaned_search}%",
                    limit,
                    offset,
                ),
            ).fetchall()

    return [dict(row) for row in rows]