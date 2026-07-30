"""Tests for conversation-context construction."""

import pytest

from app.conversation_context import (
    build_contextual_message,
    format_conversation_context,
    select_recent_messages,
)


def create_message(
    user_message: str,
    assistant_reply: str,
) -> dict[str, str]:
    """Create a simple stored-message record for testing."""
    return {
        "user_message": user_message,
        "assistant_reply": assistant_reply,
    }


def test_select_recent_messages_respects_limit() -> None:
    """Only the most recent messages should be selected."""
    messages = [
        create_message("Question 1", "Answer 1"),
        create_message("Question 2", "Answer 2"),
        create_message("Question 3", "Answer 3"),
    ]

    recent_messages = select_recent_messages(
        messages,
        limit=2,
    )

    assert len(recent_messages) == 2
    assert recent_messages[0]["user_message"] == "Question 2"
    assert recent_messages[1]["user_message"] == "Question 3"


def test_select_recent_messages_returns_all_when_below_limit() -> None:
    """All records should be returned when fewer than the limit exist."""
    messages = [
        create_message("Question 1", "Answer 1"),
        create_message("Question 2", "Answer 2"),
    ]

    recent_messages = select_recent_messages(
        messages,
        limit=5,
    )

    assert recent_messages == messages


def test_select_recent_messages_returns_empty_for_zero_limit() -> None:
    """A zero history limit should disable conversation context."""
    messages = [
        create_message("Question 1", "Answer 1"),
    ]

    assert select_recent_messages(messages, limit=0) == []


def test_select_recent_messages_rejects_negative_limit() -> None:
    """A negative history limit should be rejected."""
    with pytest.raises(
        ValueError,
        match="History limit cannot be negative",
    ):
        select_recent_messages([], limit=-1)


def test_format_conversation_context_returns_empty_without_history() -> None:
    """No previous messages should produce no context text."""
    context = format_conversation_context([])

    assert context == ""


def test_format_conversation_context_formats_stored_messages() -> None:
    """Stored exchanges should be formatted for prompt inclusion."""
    messages = [
        create_message(
            "What is automation?",
            "Automation performs repeated tasks using systems.",
        ),
    ]

    context = format_conversation_context(messages)

    assert context == (
        "Previous conversation context:\n"
        "User: What is automation?\n"
        "Assistant: Automation performs repeated tasks using systems."
    )


def test_build_contextual_message_returns_current_message_without_history() -> None:
    """A new session should use only the current user message."""
    contextual_message = build_contextual_message(
        "Explain AI assistants.",
        [],
    )

    assert contextual_message == "Explain AI assistants."


def test_build_contextual_message_combines_history_and_current_message() -> None:
    """Existing history should be combined with the current message."""
    messages = [
        create_message(
            "What is automation?",
            "Automation performs repeated tasks.",
        ),
    ]

    contextual_message = build_contextual_message(
        "Give me a clinic example.",
        messages,
    )

    assert contextual_message == (
        "Previous conversation context:\n"
        "User: What is automation?\n"
        "Assistant: Automation performs repeated tasks.\n\n"
        "Current user message:\n"
        "Give me a clinic example."
    )


def test_build_contextual_message_rejects_blank_current_message() -> None:
    """A blank current message should be rejected."""
    with pytest.raises(
        ValueError,
        match="Current message cannot be empty",
    ):
        build_contextual_message("   ", [])