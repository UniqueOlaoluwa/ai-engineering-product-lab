"""Command-line entry point for the AI Engineering Product Lab."""

from app.exceptions import PromptTemplateError
from app.prompt_builder import (
    build_prompt,
    get_role_configs,
    get_role_name,
    normalize_role,
)

EXIT_COMMANDS = {"exit", "quit"}


def create_mock_reply(prompt: str, selected_role: str) -> str:
    """Create a temporary mock response for the generated prompt."""
    role_name = get_role_name(selected_role)

    return (
        f"[Mock {role_name}]\n"
        f"The application successfully built this prompt:\n\n{prompt}"
    )


def display_available_roles() -> None:
    """Display the configured assistant roles."""
    role_configs = get_role_configs()

    print("Available assistant roles:")

    for role_key, role_config in role_configs.items():
        role_name = role_config["name"]
        print(f"- {role_key}: {role_name}")


def run_assistant() -> None:
    """Run the interactive role-based assistant."""
    print("AI WebCo Prompt Assistant v0.4")
    print("This version includes safer configuration handling.")
    print("Type 'exit' or 'quit' to close the program.\n")

    display_available_roles()

    requested_role = input("\nChoose an assistant role: ")
    selected_role = normalize_role(requested_role)

    if selected_role != requested_role.strip().lower():
        print(
            f"Role '{requested_role.strip()}' is not supported. "
            f"Using '{selected_role}' instead."
        )

    print(
        f"\nActive role: "
        f"{selected_role} — {get_role_name(selected_role)}\n"
    )

    while True:
        user_message = input("You: ")

        if user_message.strip().lower() in EXIT_COMMANDS:
            print("Assistant: Session closed.")
            break

        try:
            prompt = build_prompt(user_message, selected_role)
        except ValueError as error:
            print(f"Assistant: {error}")
            continue

        assistant_reply = create_mock_reply(prompt, selected_role)
        print(f"Assistant:\n{assistant_reply}\n")


def main() -> None:
    """Start the application and handle configuration failures safely."""
    try:
        run_assistant()
    except PromptTemplateError as error:
        print("The application could not start.")
        print(f"Configuration error: {error}")
        print(
            "Check data/prompt_templates.json, correct the problem, "
            "and restart the application."
        )


if __name__ == "__main__":
    main()