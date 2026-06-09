from pathlib import Path


# Recommended defaults:
# - qwen3.5:9b for general local agent work
# - qwen2.5-coder:7b for coding-heavy sessions
# - qwen3:8b if qwen3.5:9b is too slow
MODEL = "qwen3.5:9b"

WORKSPACE = Path(".").resolve()

MAX_TOOL_LOOPS = 15
MAX_FILE_READ_BYTES = 80_000
MAX_TOOL_OUTPUT_CHARS = 12_000
SHOW_TOOL_CALLS = True
