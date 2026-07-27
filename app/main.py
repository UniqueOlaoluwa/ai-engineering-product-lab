"""Command-line entry point for the AI Engineering Product Lab."""

EXIT_COMMANDS = {"exit", "quit"}


def create_reply(message: str) -> str:
    """Create a temporary mock reply for the user's message."""
    cleaned_message = message.strip()

    if not cleaned_message:
        return "Please type a message so I can help you."

    return f"[Mock assistant] I received your message: {cleaned_message}"


def main() -> None:
    """Run the command-line assistant."""
    print("AI WebCo Prompt Assistant v0.1")
    print("This version uses a mock response.")
    print("Type 'exit' or 'quit' to close the program.\n")

    while True:
        user_message = input("You: ")

        if user_message.strip().lower() in EXIT_COMMANDS:
            print("Assistant: Session closed.")
            break

        assistant_reply = create_reply(user_message)
        print(f"Assistant: {assistant_reply}")


if __name__ == "__main__":
    main()