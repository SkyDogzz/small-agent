#!/usr/bin/env python3

from ollama import ResponseError, chat
from pathlib import Path
import subprocess
import shlex
import json


# Recommended defaults:
# - qwen3.5:9b for general local agent work
# - qwen2.5-coder:7b for coding-heavy sessions
# - qwen3:8b if qwen3.5:9b is too slow
MODEL = "qwen3.5:9b"

WORKSPACE = Path(".").resolve()

MAX_TOOL_LOOPS = 15
MAX_FILE_READ_BYTES = 80_000
MAX_TOOL_OUTPUT_CHARS = 12_000


SYSTEM_PROMPT = """
You are a local autonomous coding and file-system agent running on the user's machine.

Your job is to help the user inspect, understand, modify, debug, and maintain local projects safely and accurately.

GENERAL BEHAVIOR
- Always answer in English unless the user explicitly asks for another language.
- Be practical, direct, and concise.
- Prefer concrete actions over vague advice.
- Do not hallucinate files, folders, commands, outputs, errors, or project details.
- If you are unsure, use tools to inspect the real environment.
- Base conclusions on tool results.
- Never pretend you inspected something if you did not.
- Never invent paths.
- Never invent command output.
- Never claim a file contains something unless you actually read it.
- Never mention hidden reasoning, internal thoughts, /think, <think>, chain-of-thought, or scratchpads.
- Do not output reasoning tags.
- Do not expose private reasoning.
- Give final answers as clear summaries of what you found or changed.

LOCAL CONTEXT
- The current working directory is the user's active project folder.
- When the user says "this folder", "this directory", "current dir", "here", "this project", "this repo", or "the repo", they usually mean ".".
- If the user asks about the current project and gives no path, use ".".
- Treat "." as the default path unless a different path is explicitly provided.
- If a relative path is given, resolve it from the current workspace.
- Do not use absolute paths unless they come from tool output or the user explicitly gives them.

TOOL USE RULES
- Use tools whenever the answer depends on local files, folders, git state, command output, tests, build results, or project structure.
- Do not answer from memory when a tool can verify the answer.
- For "what is this folder/project/repo about?", call inspect_folder(".") first.
- For "list files", call list_files.
- For "read/show/open this file", call read_file.
- For "find/search/where is", call grep_code or list_files as appropriate.
- When listing files, do not invent counts, rename entries, or omit entries returned by the tool.
- If you summarize a directory listing, keep entry names exactly as returned.
- For "what changed", "diff", or "review my changes", call git_diff and git_status.
- For "does it compile", "build it", or "run make", call run_make.
- For "run norminette", "check norm", or "42 norm", call run_norminette.
- For "debug this error", inspect the relevant files and run the relevant command if safe.
- After every tool call, use the result. Do not ignore tool output.
- If a tool fails, explain the failure and suggest the next useful step.
- Do not repeatedly call the same tool with the same arguments unless there is a clear reason.

PROJECT INSPECTION STRATEGY
When asked to understand a project:
1. Inspect the folder with inspect_folder(".").
2. Read README.md if present.
3. Read TODO.md, AGENTS.md, package.json, pyproject.toml, Makefile, Cargo.toml, go.mod, or similar files if relevant.
4. Summarize what the project appears to be.
5. Clearly separate confirmed facts from likely guesses.

CODE REVIEW STRATEGY
When asked to review code:
1. Read the relevant files first.
2. Identify correctness issues, style issues, edge cases, and maintainability problems.
3. Prioritize the most important issues.
4. Quote or reference function/file names when possible.
5. Suggest minimal fixes.
6. Do not rewrite large files unless the user asks.

CODING STRATEGY
When asked to implement or modify code:
1. Inspect the existing structure first.
2. Preserve the user's style and architecture.
3. Make the smallest safe change that solves the problem.
4. Avoid unnecessary rewrites.
5. After editing, run relevant checks if available.
6. Explain what changed and why.

SAFETY RULES
- Never run destructive commands without explicit user confirmation.
- Destructive commands include deleting files, overwriting many files, force resets, hard cleans, changing permissions recursively, package removals, disk operations, shutdown/reboot commands, and network/system administration changes.
- Never run sudo.
- Never run rm -rf.
- Never run commands that modify files outside the workspace.
- Never access files outside the workspace.
- Never read secrets intentionally.
- If you encounter files such as .env, private keys, tokens, credentials, or SSH keys, do not print their contents.
- If the user asks to reveal secrets, refuse and explain that you can help verify their presence or configure safe loading instead.
- Before writing a file, be certain of the intended path.
- Prefer showing a patch or summary before large edits.

SHELL COMMAND RULES
- Use shell commands only when useful.
- Prefer specific commands over broad ones.
- Keep commands scoped to the workspace.
- Avoid long-running commands.
- Do not start servers unless the user explicitly asks.
- Do not install packages unless the user explicitly asks.
- If a command may take a long time or change the environment, ask for confirmation first.
- For safe read-only inspection, commands like pwd, ls, find, grep, git status, git diff, cat, sed, make -n are acceptable.
- For build/test commands, use the most obvious existing project command.

GIT RULES
- Never commit unless the user explicitly asks.
- Never push unless the user explicitly asks.
- Never reset, rebase, checkout, clean, or stash changes unless the user explicitly asks.
- For repository status questions, use git_status.
- For change review, use git_diff.
- When suggesting commits, provide a commit message but do not commit automatically.

RESPONSE STYLE
- Be concise but useful.
- Use short sections when helpful.
- Prefer bullet points for findings.
- Start with the answer, then give evidence.
- Mention which files or commands were inspected.
- If you made changes, list changed files.
- If you did not make changes, say so.
- If you could not complete a task, say exactly why.
- Avoid generic filler.
- Do not end every response with a question.
- Do not over-apologize.

42 SCHOOL / C PROJECT RULES
When working on 42 School C projects:
- Respect the 42 Norm unless the user says otherwise.
- Avoid for-loops if the project follows strict Norm style.
- Avoid ternaries.
- Keep functions short.
- Keep line lengths reasonable.
- Prefer explicit error handling.
- Be careful with malloc/free ownership.
- Check NULL pointers.
- Avoid memory leaks.
- For push_swap, minishell, libft, philosophers, cub3d, or similar projects, inspect project-specific headers before editing.
- Run make and norminette when relevant and available.

DOTFILES RULES
When working in a dotfiles repository:
- Be careful with configs that affect the user's desktop/session.
- Do not overwrite config files without reading them first.
- For Hyprland, Waybar, Rofi, Kitty, Zsh, Neovim, GTK, Dunst, Greetd, Wlogout, Yazi, Lazygit, Atuin, Bat, or Btop configs, preserve the existing style.
- Prefer small targeted edits.
- Mention if a change may require restarting a service, reloading Hyprland, or opening a new shell.

ERROR HANDLING
- If a user request is ambiguous but a safe default exists, use the safe default.
- If no safe default exists, ask one focused clarification.
- If a file/path does not exist, list nearby files or suggest the closest likely match.
- If a command fails, summarize the error and suggest the next diagnostic step.
- If output is too long, summarize the important part and offer to inspect a specific section.

IMPORTANT
You are not a chatbot guessing about a project.
You are an agent with tools.
Use the tools.
Verify first.
Then answer.
"""


def safe_path(path: str = ".") -> Path:
    """
    Resolve a path safely inside WORKSPACE only.
    """
    if path is None or path.strip() == "":
        path = "."

    raw = Path(path).expanduser()

    if raw.is_absolute():
        target = raw.resolve()
    else:
        target = (WORKSPACE / raw).resolve()

    if not str(target).startswith(str(WORKSPACE)):
        raise ValueError(f"Access outside workspace is blocked: {target}")

    return target


def truncate(text: str, limit: int = MAX_TOOL_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[Output truncated to {limit} characters.]"


def is_secret_like_path(path: Path) -> bool:
    secret_names = {
        ".env",
        ".env.local",
        ".env.production",
        ".env.development",
        "id_rsa",
        "id_ed25519",
        "credentials.json",
        "secrets.json",
        "secret.json",
    }

    lowered_parts = [part.lower() for part in path.parts]

    if path.name.lower() in secret_names:
        return True

    suspicious_fragments = [
        "secret",
        "secrets",
        "token",
        "tokens",
        "credential",
        "credentials",
        "private_key",
        "apikey",
        "api_key",
    ]

    return any(fragment in part for part in lowered_parts for fragment in suspicious_fragments)


def list_files(path: str = ".") -> str:
    """List files and directories in a directory.

    Args:
        path: Directory path to list. Defaults to current directory.
    """
    try:
        p = safe_path(path)

        if not p.exists():
            return f"Path does not exist: {p}"
        if not p.is_dir():
            return f"Path is not a directory: {p}"

        entries = sorted(
            p.iterdir(),
            key=lambda x: (not x.is_dir(), x.name.lower()),
        )

        dir_count = sum(1 for entry in entries if entry.is_dir())
        file_count = len(entries) - dir_count

        lines = [
            f"Directory listing for: {p}",
            f"Entries: {len(entries)} total ({dir_count} directories, {file_count} files)",
            "",
        ]

        if not entries:
            lines.append("(empty directory)")
            return "\n".join(lines)

        for entry in entries:
            kind = "DIR " if entry.is_dir() else "FILE"
            lines.append(f"[{kind}] {entry.name}")

        return truncate("\n".join(lines))

    except Exception as e:
        return f"Error: {e}"


def read_file(path: str) -> str:
    """Read a text file.

    Args:
        path: Path to the file.
    """
    try:
        p = safe_path(path)

        if not p.exists():
            return f"File does not exist: {p}"
        if not p.is_file():
            return f"Path is not a file: {p}"

        if is_secret_like_path(p):
            return (
                f"Refusing to print possible secret file: {p.name}. "
                "I can help check that it exists or help configure safe loading."
            )

        size = p.stat().st_size
        if size > MAX_FILE_READ_BYTES:
            return (
                f"File is too large: {size} bytes. "
                "Ask for a specific section or implement chunked reading."
            )

        text = p.read_text(errors="replace")
        return truncate(text)

    except Exception as e:
        return f"Error: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a text file.

    Args:
        path: Path to the file.
        content: Text content to write.
    """
    try:
        p = safe_path(path)

        if is_secret_like_path(p):
            return f"Refusing to write possible secret file: {p.name}."

        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

        return f"Wrote file: {p}"

    except Exception as e:
        return f"Error: {e}"


def inspect_folder(path: str = ".") -> str:
    """Inspect a folder and infer what kind of project or config it is.

    Args:
        path: Directory path to inspect. Defaults to current directory.
    """
    try:
        p = safe_path(path)

        if not p.exists():
            return f"Path does not exist: {p}"
        if not p.is_dir():
            return f"Path is not a directory: {p}"

        interesting_files = [
            "README.md",
            "README",
            "AGENTS.md",
            "TODO.md",
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "Cargo.toml",
            "go.mod",
            "Makefile",
            "CMakeLists.txt",
            "docker-compose.yml",
            "compose.yml",
            "Dockerfile",
            ".git/config",
        ]

        output = [f"Inspection for: {p}", ""]

        output.append("Top-level entries:")
        entries = sorted(p.iterdir(), key=lambda x: x.name.lower())

        if not entries:
            output.append("- (empty directory)")
        else:
            for entry in entries[:120]:
                kind = "DIR " if entry.is_dir() else "FILE"
                output.append(f"- [{kind}] {entry.name}")

        output.append("\nRelevant file previews:")

        found_preview = False

        for name in interesting_files:
            file_path = p / name
            if file_path.exists() and file_path.is_file():
                found_preview = True
                output.append(f"\n--- {name} ---")

                if is_secret_like_path(file_path):
                    output.append("[Skipped possible secret file.]")
                    continue

                try:
                    text = file_path.read_text(errors="replace")
                    output.append(truncate(text, 4000))
                except Exception as e:
                    output.append(f"Could not read {name}: {e}")

        if not found_preview:
            output.append("No common project metadata files found.")

        return truncate("\n".join(output), 18_000)

    except Exception as e:
        return f"Error: {e}"


def command_is_blocked(command: str) -> str | None:
    lowered = command.lower()

    blocked_fragments = [
        "rm -rf",
        "sudo",
        "mkfs",
        "dd ",
        ":(){",
        "shutdown",
        "reboot",
        "poweroff",
        "chmod -r 777",
        "chmod -R 777",
        "chown -r",
        "chown -R",
        "git reset",
        "git clean",
        "git push",
        "git rebase",
        "git checkout",
        "git switch",
        "git stash",
        "systemctl",
        "pacman -r",
        "apt remove",
        "apt purge",
        "dnf remove",
    ]

    for bad in blocked_fragments:
        if bad.lower() in lowered:
            return bad

    return None


def run_shell(command: str) -> str:
    """Run a shell command.

    Args:
        command: Shell command to run.
    """
    blocked = command_is_blocked(command)
    if blocked:
        return f"Blocked potentially dangerous command containing: {blocked}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE,
            text=True,
            capture_output=True,
            timeout=20,
        )

        output = ""

        if result.stdout:
            output += result.stdout

        if result.stderr:
            if output:
                output += "\n"
            output += result.stderr

        if not output:
            output = f"Command completed with exit code {result.returncode}."

        return truncate(output)

    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Error: {e}"


def git_status() -> str:
    """Show git status."""
    return run_shell("git status --short")


def git_diff() -> str:
    """Show git diff."""
    return run_shell("git diff -- .")


def grep_code(pattern: str, path: str = ".") -> str:
    """Search for a pattern in files using grep.

    Args:
        pattern: Text or regex pattern to search for.
        path: Directory or file path to search in.
    """
    try:
        safe_target = safe_path(path)
        quoted_pattern = shlex.quote(pattern)
        quoted_path = shlex.quote(str(safe_target))

        command = (
            "grep -RIn "
            "--exclude-dir=.git "
            "--exclude-dir=.venv "
            "--exclude-dir=node_modules "
            "--exclude-dir=__pycache__ "
            f"{quoted_pattern} {quoted_path}"
        )

        return run_shell(command)

    except Exception as e:
        return f"Error: {e}"


def find_files(name_pattern: str = "*", path: str = ".") -> str:
    """Find files by name pattern.

    Args:
        name_pattern: Glob-style filename pattern, for example '*.c' or 'README*'.
        path: Directory path to search in.
    """
    try:
        p = safe_path(path)

        if not p.exists():
            return f"Path does not exist: {p}"
        if not p.is_dir():
            return f"Path is not a directory: {p}"

        matches = []
        for item in p.rglob(name_pattern):
            if any(part in {".git", ".venv", "node_modules", "__pycache__"} for part in item.parts):
                continue
            matches.append(item)

            if len(matches) >= 200:
                break

        if not matches:
            return f"No files found matching pattern: {name_pattern}"

        lines = [f"Files matching {name_pattern!r} under {p}:"]
        for item in matches:
            kind = "DIR " if item.is_dir() else "FILE"
            lines.append(f"[{kind}] {item.relative_to(WORKSPACE)}")

        if len(matches) >= 200:
            lines.append("[Stopped after 200 matches.]")

        return truncate("\n".join(lines))

    except Exception as e:
        return f"Error: {e}"


def run_make(target: str = "") -> str:
    """Run make with an optional target.

    Args:
        target: Optional Makefile target.
    """
    if target:
        return run_shell(f"make {shlex.quote(target)}")
    return run_shell("make")


def run_norminette(path: str = ".") -> str:
    """Run norminette on a path.

    Args:
        path: File or directory path.
    """
    try:
        safe_target = safe_path(path)
        return run_shell(f"norminette {shlex.quote(str(safe_target))}")
    except Exception as e:
        return f"Error: {e}"


def python_syntax_check(path: str = ".") -> str:
    """Run Python syntax checks with compileall.

    Args:
        path: File or directory path.
    """
    try:
        safe_target = safe_path(path)
        return run_shell(f"python -m compileall -q {shlex.quote(str(safe_target))}")
    except Exception as e:
        return f"Error: {e}"


TOOLS = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "inspect_folder": inspect_folder,
    "run_shell": run_shell,
    "git_status": git_status,
    "git_diff": git_diff,
    "grep_code": grep_code,
    "find_files": find_files,
    "run_make": run_make,
    "run_norminette": run_norminette,
    "python_syntax_check": python_syntax_check,
}


TOOL_FUNCTIONS = [
    list_files,
    read_file,
    write_file,
    inspect_folder,
    run_shell,
    git_status,
    git_diff,
    grep_code,
    find_files,
    run_make,
    run_norminette,
    python_syntax_check,
]


messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT,
    }
]


def normalize_tool_args(args):
    """
    Ollama usually returns a dict for tool arguments.
    Some models may return JSON as a string, so handle both.
    """
    if args is None:
        return {}

    if isinstance(args, dict):
        return args

    if isinstance(args, str):
        try:
            loaded = json.loads(args)
            if isinstance(loaded, dict):
                return loaded
        except json.JSONDecodeError:
            return {}

    return {}


def fallback_project_summary() -> str:
    """
    Best-effort summary when the model or tool calling fails.
    """
    folder_summary = inspect_folder(".")
    readme_summary = read_file("README.md")

    return "\n".join(
        [
            "I hit an Ollama tool-call parsing error, so here is a local best-effort summary based on the workspace:",
            "",
            "What the project appears to be:",
            "- A small local autonomous coding agent that uses `ollama`.",
            "- `agent.py` is the main entry point and contains the tool loop, workspace safety checks, and local file/shell helpers.",
            "- `run-agent.sh` activates `.venv` and starts `python agent.py`.",
            "- `README.md` documents the setup and run steps.",
            "",
            "Workspace inspection:",
            folder_summary,
            "",
            "README preview:",
            readme_summary,
        ]
    )


def run_agent(user_prompt: str) -> str:
    messages.append({"role": "user", "content": user_prompt})

    saw_tool_call = False
    last_tool_results = []

    for step in range(MAX_TOOL_LOOPS):
        try:
            response = chat(
                model=MODEL,
                messages=messages,
                tools=TOOL_FUNCTIONS,
                stream=False,
            )
        except ResponseError as e:
            error_text = str(e)

            if "XML syntax error" in error_text:
                return fallback_project_summary()

            return f"Ollama error: {error_text}"

        msg = response.get("message", {})
        messages.append(msg)

        content = msg.get("content")
        tool_calls = msg.get("tool_calls") or []

        # Normal final answer
        if not tool_calls:
            if content and content.strip():
                return content.strip()

            # If the model returns empty text after tools, recover manually.
            if saw_tool_call and last_tool_results:
                recovery_prompt = (
                    "You returned an empty answer. "
                    "Summarize the tool results clearly for the user. "
                    "Do not call tools again unless absolutely necessary."
                )
                messages.append({"role": "user", "content": recovery_prompt})
                continue

            return "[No response from model.]"

        saw_tool_call = True

        for call in tool_calls:
            function = call.get("function", {})
            name = function.get("name")
            args = normalize_tool_args(function.get("arguments", {}))

            fn = TOOLS.get(name)

            if not fn:
                result = f"Unknown tool: {name}"
            else:
                try:
                    result = fn(**args)
                except Exception as e:
                    result = f"Tool error in {name}: {e}"

            last_tool_results.append(
                {
                    "tool": name,
                    "args": args,
                    "result": str(result),
                }
            )

            # Ollama accepts tool-role messages like this.
            messages.append(
                {
                    "role": "tool",
                    "name": name,
                    "content": str(result),
                }
            )

    # Last-resort fallback instead of blank output
    if last_tool_results:
        text = ["Tool loop stopped, but here are the latest tool results:\n"]
        for item in last_tool_results[-3:]:
            text.append(f"Tool: {item['tool']}")
            text.append(f"Args: {item['args']}")
            text.append("Result:")
            text.append(item["result"][:4000])
            text.append("")
        return "\n".join(text)

    return "Stopped after too many tool calls."

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


def clear_history() -> None:
    messages.clear()
    messages.append(
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    )


def main() -> None:
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


if __name__ == "__main__":
    main()
