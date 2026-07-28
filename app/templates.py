"""Load assistant role templates from JSON configuration."""

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_FILE = PROJECT_ROOT / "data" / "prompt_templates.json"


def load_prompt_templates(
    file_path: Path = TEMPLATES_FILE,
) -> dict[str, Any]:
    """Load and return prompt-template configuration from a JSON file."""
    try:
        with file_path.open("r", encoding="utf-8") as file:
            templates = json.load(file)
    except FileNotFoundError as error:
        raise RuntimeError(
            f"Prompt-template file was not found: {file_path}"
        ) from error
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Prompt-template file contains invalid JSON: {file_path}"
        ) from error

    if "default_role" not in templates:
        raise RuntimeError("Prompt-template configuration has no default_role.")

    if "roles" not in templates or not isinstance(templates["roles"], dict):
        raise RuntimeError(
            "Prompt-template configuration must contain a roles object."
        )

    if not templates["roles"]:
        raise RuntimeError("Prompt-template configuration contains no roles.")

    return templates