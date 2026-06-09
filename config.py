from pathlib import Path


# Recommended defaults:
# - qwen3.5:9b for general local agent work
# - qwen2.5-coder:7b for coding-heavy sessions
# - qwen3:8b if qwen3.5:9b is too slow
DEFAULT_MODEL = "gemma4:e4b"
MODEL = DEFAULT_MODEL

DEFAULT_WORKSPACE = Path(".").resolve()
WORKSPACE = DEFAULT_WORKSPACE

DEFAULT_MAX_TOOL_LOOPS = 15
MAX_TOOL_LOOPS = DEFAULT_MAX_TOOL_LOOPS

DEFAULT_MAX_FILE_READ_BYTES = 80_000
MAX_FILE_READ_BYTES = DEFAULT_MAX_FILE_READ_BYTES

DEFAULT_MAX_TOOL_OUTPUT_CHARS = 12_000
MAX_TOOL_OUTPUT_CHARS = DEFAULT_MAX_TOOL_OUTPUT_CHARS

DEFAULT_MAX_CONSOLE_TOOL_PREVIEW_CHARS = 1_500
MAX_CONSOLE_TOOL_PREVIEW_CHARS = DEFAULT_MAX_CONSOLE_TOOL_PREVIEW_CHARS

DEFAULT_SHOW_TOOL_CALLS = True
SHOW_TOOL_CALLS = DEFAULT_SHOW_TOOL_CALLS


def apply_runtime_config(
    model: str | None = None,
    workspace: str | Path | None = None,
    max_tool_loops: int | None = None,
    max_file_read_bytes: int | None = None,
    max_tool_output_chars: int | None = None,
    max_console_tool_preview_chars: int | None = None,
    show_tool_calls: bool | None = None,
) -> None:
    global MODEL
    global WORKSPACE
    global MAX_TOOL_LOOPS
    global MAX_FILE_READ_BYTES
    global MAX_TOOL_OUTPUT_CHARS
    global MAX_CONSOLE_TOOL_PREVIEW_CHARS
    global SHOW_TOOL_CALLS

    if model is not None:
        MODEL = model

    if workspace is not None:
        WORKSPACE = Path(workspace).expanduser().resolve()

    if max_tool_loops is not None:
        MAX_TOOL_LOOPS = max_tool_loops

    if max_file_read_bytes is not None:
        MAX_FILE_READ_BYTES = max_file_read_bytes

    if max_tool_output_chars is not None:
        MAX_TOOL_OUTPUT_CHARS = max_tool_output_chars

    if max_console_tool_preview_chars is not None:
        MAX_CONSOLE_TOOL_PREVIEW_CHARS = max_console_tool_preview_chars

    if show_tool_calls is not None:
        SHOW_TOOL_CALLS = show_tool_calls
