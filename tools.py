import shlex
import subprocess
from pathlib import Path

from config import MAX_FILE_READ_BYTES, MAX_TOOL_OUTPUT_CHARS, WORKSPACE


def truncate(text: str, limit: int = MAX_TOOL_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[Output truncated to {limit} characters.]"


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
