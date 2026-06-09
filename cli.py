from config import MODEL, WORKSPACE
from runner import clear_history, run_agent
from tools import set_run_shell_confirmation_handler


def confirm_shell_command(command: str, reason: str) -> bool:
    print("\nShell command confirmation required.")
    print(f"Reason: {reason}")
    print(f"Command: {command}")

    try:
        answer = input("Run it? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return False

    return answer in {"y", "yes"}


def print_help() -> None:
    print(
        """
Commands:
  exit / quit       Stop the agent
  /help             Show this help
  /model            Show current model
  /workspace        Show workspace
  /clear            Clear conversation history, keep system prompt

Examples:
  list files in the current dir
  what could this folder be about?
  read README.md
  find files matching *.conf
  search for exec-once
  show git status
  review my changes
  run make
  run norminette on .
"""
    )


def main() -> None:
    set_run_shell_confirmation_handler(confirm_shell_command)

    print(f"Local agent running with model: {MODEL}")
    print(f"Workspace: {WORKSPACE}")
    print("Type 'exit', 'quit', or '/help'.\n")

    while True:
        try:
            prompt = input("You > ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break

        if not prompt:
            continue

        lowered = prompt.lower()

        if lowered in {"exit", "quit"}:
            break

        if lowered == "/help":
            print_help()
            continue

        if lowered == "/model":
            print(MODEL)
            continue

        if lowered == "/workspace":
            print(WORKSPACE)
            continue

        if lowered == "/clear":
            clear_history()
            print("Conversation history cleared.")
            continue

        print("\nAgent >")
        answer = run_agent(prompt)
        print(answer)
        print()
