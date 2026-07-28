"""Utilities for building role-based prompts."""

from typing import Any

from app.templates import load_prompt_templates

PROMPT_TEMPLATES = load_prompt_templates()
DEFAULT_ROLE: str = PROMPT_TEMPLATES["default_role"]
ROLE_CONFIGS: dict[str, dict[str, Any]] = PROMPT_TEMPLATES["roles"]


def normalize_role(role: str) -> str:
    """Return a supported role or fall back to the configured default role."""
    cleaned_role = role.strip().lower()

    if cleaned_role in ROLE_CONFIGS:
        return cleaned_role

    return DEFAULT_ROLE


def get_role_name(role: str) -> str:
    """Return the display name for a supported or fallback role."""
    selected_role = normalize_role(role)
    return str(ROLE_CONFIGS[selected_role]["name"])


def build_prompt(user_message: str, assistant_role: str) -> str:
    """Build a complete prompt using the selected assistant role."""
    cleaned_message = user_message.strip()

    if not cleaned_message:
        raise ValueError("User message cannot be empty.")

    selected_role = normalize_role(assistant_role)
    role_instruction = str(ROLE_CONFIGS[selected_role]["instruction"])

    return (
        f"{role_instruction}\n\n"
        f"User message: {cleaned_message}\n\n"
        "Give a clear, useful, and concise response."
    )