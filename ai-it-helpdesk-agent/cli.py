"""
cli.py
------
A terminal chat interface for the AI IT Helpdesk Agent -- useful for
quick demos or testing without running the Flask server.

Run:
    python cli.py
"""

import uuid

from agent import ITHelpdeskAgent


def main():
    print("=" * 60)
    print(" AI IT Helpdesk Agent  (Agent + RAG + Tools + Memory)")
    print(" Type 'exit' or 'quit' to leave.")
    print("=" * 60)

    helpdesk_agent = ITHelpdeskAgent()
    session_id = str(uuid.uuid4())

    print(
        "\nAssistant: Hi! Describe the IT issue you're facing and I'll help "
        "you troubleshoot it.\n"
    )

    while True:
        try:
            user_message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_message:
            continue
        if user_message.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        result = helpdesk_agent.handle_message(session_id, user_message)
        print(f"\nAssistant: {result['response']}\n")

        if result.get("sources"):
            src = ", ".join(f"{s['title']} ({s['id']})" for s in result["sources"])
            print(f"[sources: {src}]")
        if result.get("tools_used"):
            tool_names = ", ".join(t["tool"] for t in result["tools_used"])
            print(f"[tools used: {tool_names}]")
        if result.get("escalated"):
            print("[escalated to human support]")
        print()


if __name__ == "__main__":
    main()
