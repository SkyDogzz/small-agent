import argparse

import config
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--model")
    parser.add_argument("--workspace")
    parser.add_argument("--max-tool-loops", type=int)
    parser.add_argument("--max-file-read-bytes", type=int)
    parser.add_argument("--max-tool-output-chars", type=int)
    parser.add_argument("--max-console-tool-preview-chars", type=int)
    parser.add_argument(
        "--show-tool-calls",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("-h", "--help", action="help")
    return parser


def print_help() -> None:
    print(
        """
Commands:
  exit / quit       Stop the agent
  /help             Show this help
  /model            Show current model
  /workspace        Show workspace
  /clear            Clear conversation history, keep system prompt
  /config           Show runtime config

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


def print_runtime_config() -> None:
    print(f"Model: {config.MODEL}")
    print(f"Workspace: {config.WORKSPACE}")
    print(f"Max tool loops: {config.MAX_TOOL_LOOPS}")
    print(f"Max file read bytes: {config.MAX_FILE_READ_BYTES}")
    print(f"Max tool output chars: {config.MAX_TOOL_OUTPUT_CHARS}")
    print(
        "Max console tool preview chars: "
        f"{config.MAX_CONSOLE_TOOL_PREVIEW_CHARS}"
    )
    print(f"Show tool calls: {config.SHOW_TOOL_CALLS}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    config.apply_runtime_config(
        model=args.model,
        workspace=args.workspace,
        max_tool_loops=args.max_tool_loops,
        max_file_read_bytes=args.max_file_read_bytes,
        max_tool_output_chars=args.max_tool_output_chars,
        max_console_tool_preview_chars=args.max_console_tool_preview_chars,
        show_tool_calls=args.show_tool_calls,
    )

    from runner import clear_history, run_agent

    set_run_shell_confirmation_handler(confirm_shell_command)

    print(f"Local agent running with model: {config.MODEL}")
    print(f"Workspace: {config.WORKSPACE}")
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
            print(config.MODEL)
            continue

        if lowered == "/workspace":
            print(config.WORKSPACE)
            continue

        if lowered == "/clear":
            clear_history()
            print("Conversation history cleared.")
            continue

        if lowered == "/config":
            print_runtime_config()
            continue

        print("\nAgent >")
        answer = run_agent(prompt)
        print(answer)
        print()
