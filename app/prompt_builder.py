"""Utilities for building role-based prompts."""

from functools import lru_cache
from typing import Any

from app.templates import load_prompt_templates


@lru_cache(maxsize=1)
def get_prompt_templates() -> dict[str, Any]:
    """Load and cache the prompt-template configuration."""
    return load_prompt_templates()


def get_default_role() -> str:
    """Return the configured default assistant role."""
    templates = get_prompt_templates()
    return str(templates["default_role"])


def get_role_configs() -> dict[str, dict[str, Any]]:
    """Return the configured assistant roles."""
    templates = get_prompt_templates()
    return templates["roles"]


def normalize_role(role: str) -> str:
    """Return a supported role or fall back to the configured default role."""
    cleaned_role = role.strip().lower()
    role_configs = get_role_configs()

    if cleaned_role in role_configs:
        return cleaned_role

    return get_default_role()


def get_role_name(role: str) -> str:
    """Return the display name for a supported or fallback role."""
    selected_role = normalize_role(role)
    role_configs = get_role_configs()

    return str(role_configs[selected_role]["name"])


def build_prompt(user_message: str, assistant_role: str) -> str:
    """Build a complete prompt using the selected assistant role."""
    cleaned_message = user_message.strip()

    if not cleaned_message:
        raise ValueError("User message cannot be empty.")

    selected_role = normalize_role(assistant_role)
    role_configs = get_role_configs()
    role_instruction = str(role_configs[selected_role]["instruction"])

    return (
        f"{role_instruction}\n\n"
        f"User message: {cleaned_message}\n\n"
        "Give a clear, useful, and concise response."
    )