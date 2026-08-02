"""Reusable application service for processing chatbot messages."""

from dataclasses import dataclass

from app.config import load_settings
from app.conversation_context import build_contextual_message
from app.database import (
    get_messages_by_session,
    save_message,
)
from app.prompt_builder import (
    build_prompt,
    get_role_name,
    normalize_role,
)
from app.providers.factory import create_provider


@dataclass(frozen=True)
class ChatServiceResult:
    """Represent the result of processing one chatbot message."""

    message_id: int
    session_id: str
    role: str
    role_name: str
    reply: str
    provider: str


def process_chat_message(
    message: str,
    role: str,
    session_id: str,
    history_limit: int = 5,
) -> ChatServiceResult:
    """Process, generate, and store one chatbot exchange."""
    cleaned_message = message.strip()
    cleaned_session_id = session_id.strip()

    if not cleaned_message:
        raise ValueError("Message cannot be empty.")

    if not cleaned_session_id:
        raise ValueError("Session ID cannot be empty.")

    if history_limit < 0:
        raise ValueError("History limit cannot be negative.")

    if history_limit > 20:
        raise ValueError("History limit cannot exceed 20.")

    settings = load_settings()
    provider = create_provider(settings)

    selected_role = normalize_role(role)

    previous_messages = get_messages_by_session(
        cleaned_session_id
    )

    contextual_message = build_contextual_message(
        current_message=cleaned_message,
        previous_messages=previous_messages,
        limit=history_limit,
    )

    prompt = build_prompt(
        contextual_message,
        selected_role,
    )

    reply = provider.generate(prompt)
    provider_name = type(provider).__name__

    message_id = save_message(
        session_id=cleaned_session_id,
        role=selected_role,
        user_message=cleaned_message,
        assistant_reply=reply,
        provider=provider_name,
    )

    return ChatServiceResult(
        message_id=message_id,
        session_id=cleaned_session_id,
        role=selected_role,
        role_name=get_role_name(selected_role),
        reply=reply,
        provider=provider_name,
    )