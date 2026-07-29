"""SQLite database utilities for storing chatbot conversations."""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_DIR = PROJECT_ROOT / "storage"
DATABASE_PATH = DATABASE_DIR / "conversations.db"


def get_connection() -> sqlite3.Connection:
    """Create and return a configured SQLite connection."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database() -> None:
    """Create the required database tables when they do not exist."""
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


def get_messages_by_session(session_id: str) -> list[dict[str, Any]]:
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