"""Utilities for building conversation context from stored messages."""

from typing import Any

DEFAULT_HISTORY_LIMIT = 5


def select_recent_messages(
    messages: list[dict[str, Any]],
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> list[dict[str, Any]]:
    """Return the most recent stored messages within the requested limit."""
    if limit < 0:
        raise ValueError("History limit cannot be negative.")

    if limit == 0:
        return []

    return messages[-limit:]


def format_conversation_context(
    messages: list[dict[str, Any]],
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> str:
    """Format recent stored exchanges as readable prompt context."""
    recent_messages = select_recent_messages(messages, limit)

    if not recent_messages:
        return ""

    context_lines = [
        "Previous conversation context:",
    ]

    for message in recent_messages:
        user_message = str(
            message.get("user_message", "")
        ).strip()
        assistant_reply = str(
            message.get("assistant_reply", "")
        ).strip()

        if user_message:
            context_lines.append(f"User: {user_message}")

        if assistant_reply:
            context_lines.append(f"Assistant: {assistant_reply}")

    return "\n".join(context_lines)


def build_contextual_message(
    current_message: str,
    previous_messages: list[dict[str, Any]],
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> str:
    """Combine recent conversation history with the current message."""
    cleaned_message = current_message.strip()

    if not cleaned_message:
        raise ValueError("Current message cannot be empty.")

    conversation_context = format_conversation_context(
        previous_messages,
        limit,
    )

    if not conversation_context:
        return cleaned_message

    return (
        f"{conversation_context}\n\n"
        f"Current user message:\n{cleaned_message}"
    )