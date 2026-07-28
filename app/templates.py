"""Load and validate assistant role templates from JSON configuration."""

import json
from pathlib import Path
from typing import Any

from app.exceptions import (
    InvalidTemplateJSONError,
    InvalidTemplateStructureError,
    TemplateFileNotFoundError,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_FILE = PROJECT_ROOT / "data" / "prompt_templates.json"


def validate_prompt_templates(templates: object) -> dict[str, Any]:
    """Validate and return the prompt-template configuration."""
    if not isinstance(templates, dict):
        raise InvalidTemplateStructureError(
            "Prompt-template configuration must be a JSON object."
        )

    default_role = templates.get("default_role")
    roles = templates.get("roles")

    if not isinstance(default_role, str) or not default_role.strip():
        raise InvalidTemplateStructureError(
            "Prompt-template configuration must contain a non-empty "
            "default_role string."
        )

    if not isinstance(roles, dict) or not roles:
        raise InvalidTemplateStructureError(
            "Prompt-template configuration must contain a non-empty roles object."
        )

    if default_role not in roles:
        raise InvalidTemplateStructureError(
            f"Default role '{default_role}' does not exist in the roles object."
        )

    for role_key, role_config in roles.items():
        if not isinstance(role_key, str) or not role_key.strip():
            raise InvalidTemplateStructureError(
                "Every role must have a non-empty string key."
            )

        if not isinstance(role_config, dict):
            raise InvalidTemplateStructureError(
                f"Role '{role_key}' must contain a configuration object."
            )

        role_name = role_config.get("name")
        instruction = role_config.get("instruction")

        if not isinstance(role_name, str) or not role_name.strip():
            raise InvalidTemplateStructureError(
                f"Role '{role_key}' must contain a non-empty name."
            )

        if not isinstance(instruction, str) or not instruction.strip():
            raise InvalidTemplateStructureError(
                f"Role '{role_key}' must contain a non-empty instruction."
            )

    return templates


def load_prompt_templates(
    file_path: Path = TEMPLATES_FILE,
) -> dict[str, Any]:
    """Load, validate, and return prompt templates from a JSON file."""
    try:
        with file_path.open("r", encoding="utf-8") as file:
            templates = json.load(file)
    except FileNotFoundError as error:
        raise TemplateFileNotFoundError(
            f"Prompt-template file was not found: {file_path}"
        ) from error
    except json.JSONDecodeError as error:
        raise InvalidTemplateJSONError(
            f"Prompt-template file contains invalid JSON: "
            f"line {error.lineno}, column {error.colno}."
        ) from error

    return validate_prompt_templates(templates)