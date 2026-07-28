"""Command-line entry point for the AI Engineering Product Lab."""

from app.exceptions import PromptTemplateError, ProviderError
from app.prompt_builder import (
    build_prompt,
    get_role_configs,
    get_role_name,
    normalize_role,
)
from app.providers.base import BaseLLMProvider
from app.providers.mock import MockLLMProvider

EXIT_COMMANDS = {"exit", "quit"}


def display_available_roles() -> None:
    """Display the configured assistant roles."""
    role_configs = get_role_configs()

    print("Available assistant roles:")

    for role_key, role_config in role_configs.items():
        role_name = role_config["name"]
        print(f"- {role_key}: {role_name}")


def run_assistant(provider: BaseLLMProvider) -> None:
    """Run the interactive role-based assistant."""
    print("AI WebCo Prompt Assistant v0.5")
    print("This version uses a replaceable model provider.")
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
            assistant_reply = provider.generate(prompt)
        except ValueError as error:
            print(f"Assistant: {error}")
            continue
        except ProviderError as error:
            print("Assistant: The AI provider could not complete the request.")
            print(f"Provider error: {error}")
            print("Please try again or request human support.\n")
            continue

        print(f"Assistant:\n{assistant_reply}\n")


def main() -> None:
    """Start the application with safe configuration handling."""
    provider = MockLLMProvider()

    try:
        run_assistant(provider)
    except PromptTemplateError as error:
        print("The application could not start.")
        print(f"Configuration error: {error}")
        print(
            "Check data/prompt_templates.json, correct the problem, "
            "and restart the application."
        )


if __name__ == "__main__":
    main()