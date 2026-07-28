"""Utilities for building role-based prompts."""

DEFAULT_ROLE = "support"

ROLE_INSTRUCTIONS = {
    "business": (
        "You are a practical AI business assistant. "
        "Help business owners understand problems, workflows, and useful automation opportunities."
    ),
    "support": (
        "You are a helpful customer-support assistant. "
        "Respond clearly, politely, and practically."
    ),
    "clinic_admin": (
        "You are a clinic administrative assistant. "
        "Help only with appointments, reminders, patient routing, clinic information, "
        "and human handoff. Do not diagnose, prescribe, interpret laboratory results, "
        "or make clinical decisions."
    ),
}


def normalize_role(role: str) -> str:
    """Return a supported role or fall back to the default role."""
    cleaned_role = role.strip().lower()

    if cleaned_role in ROLE_INSTRUCTIONS:
        return cleaned_role

    return DEFAULT_ROLE


def build_prompt(user_message: str, assistant_role: str) -> str:
    """Build a complete prompt using the selected assistant role."""
    cleaned_message = user_message.strip()

    if not cleaned_message:
        raise ValueError("User message cannot be empty.")

    selected_role = normalize_role(assistant_role)
    role_instruction = ROLE_INSTRUCTIONS[selected_role]

    return (
        f"{role_instruction}\n\n"
        f"User message: {cleaned_message}\n\n"
        "Give a clear, useful, and concise response."
    )