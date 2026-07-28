"""Command-line entry point for the AI Engineering Product Lab."""

from app.prompt_builder import ROLE_INSTRUCTIONS, build_prompt, normalize_role

EXIT_COMMANDS = {"exit", "quit"}


def create_mock_reply(prompt: str, selected_role: str) -> str:
    """Create a temporary mock response for the generated prompt."""
    return (
        f"[Mock {selected_role} assistant]\n"
        f"The application successfully built this prompt:\n\n{prompt}"
    )


def display_available_roles() -> None:
    """Display the assistant roles available to the user."""
    print("Available assistant roles:")

    for role in ROLE_INSTRUCTIONS:
        print(f"- {role}")


def main() -> None:
    """Run the role-based command-line assistant."""
    print("AI WebCo Prompt Assistant v0.2")
    print("This version builds role-based prompts.")
    print("Type 'exit' or 'quit' to close the program.\n")

    display_available_roles()

    requested_role = input("\nChoose an assistant role: ")
    selected_role = normalize_role(requested_role)

    if selected_role != requested_role.strip().lower():
        print(
            f"Role '{requested_role.strip()}' is not supported. "
            f"Using '{selected_role}' instead."
        )

    print(f"\nActive role: {selected_role}\n")

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


if __name__ == "__main__":
    main()