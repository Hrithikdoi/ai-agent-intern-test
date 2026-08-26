from app.agent import SupportAgent


def main():
    agent = SupportAgent()

    print("Aster & Row Support Agent")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        if not user_input:
            continue

        response = agent.handle(user_input)

        print("\nAgent:")
        print(response.answer)

        if response.sources:
            print("\nSources:")
            for source in response.sources:
                print(
                    f"- {source['filename']} "
                    f"→ {source['heading']}"
                )

        print(f"\nTool: {response.tool_used}")
        print(f"Handoff: {response.handoff}")
        print()


if __name__ == "__main__":
    main()