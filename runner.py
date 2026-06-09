import json

from ollama import ResponseError, chat

from config import (
    MAX_CONSOLE_TOOL_PREVIEW_CHARS,
    MAX_TOOL_LOOPS,
    MODEL,
    SHOW_TOOL_CALLS,
)
from prompts import SYSTEM_PROMPT
from tools import TOOL_FUNCTIONS, TOOLS, inspect_folder, read_file, truncate


messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT,
    }
]
session_summary = ""

SUMMARY_SYSTEM_PROMPT = """
You maintain a short rolling summary for a local coding agent session.

Rules:
- Keep it factual and concise.
- Only include verified information from the conversation.
- Prefer bullets.
- Mention the user goal, important files, decisions, constraints, and open questions.
- Keep it under 8 bullets and avoid redundant wording.
- If there is no useful context yet, return an empty string.
""".strip()


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


def build_chat_messages() -> list[dict]:
    payload = [messages[0]]

    if session_summary.strip():
        payload.append(
            {
                "role": "system",
                "content": (
                    "SESSION SUMMARY (informational context only):\n"
                    f"{session_summary.strip()}"
                ),
            }
        )

    payload.extend(messages[1:])
    return payload


def render_message_excerpt(history: list[dict], limit: int = 16) -> str:
    excerpt = history[-limit:]
    lines = []

    for item in excerpt:
        role = item.get("role", "unknown")
        name = item.get("name")
        content = str(item.get("content", "")).strip()

        header = role
        if name:
            header = f"{role}:{name}"

        if len(content) > 700:
            content = content[:700] + "…"

        lines.append(f"{header}: {content}")

    return "\n".join(lines)


def update_session_summary() -> None:
    global session_summary

    history = messages[1:]
    if not history:
        session_summary = ""
        return

    summary_prompt = [
        {
            "role": "system",
            "content": SUMMARY_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                "Current summary:\n"
                f"{session_summary.strip() or '(none)'}\n\n"
                "Recent conversation:\n"
                f"{render_message_excerpt(history)}\n\n"
                "Write the updated concise session summary."
            ),
        },
    ]

    try:
        response = chat(
            model=MODEL,
            messages=summary_prompt,
            stream=False,
        )
        summary_text = response.get("message", {}).get("content", "").strip()
        session_summary = summary_text
    except Exception:
        pass


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
            "- `agent.py` is now a thin entry point that launches `cli.py`.",
            "- `cli.py` handles the terminal loop and user commands.",
            "- `runner.py` contains the Ollama chat loop and tool-call handling.",
            "- `tools.py` contains the workspace safety checks and local file/shell helpers.",
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
    total_prompt_tokens = 0
    total_completion_tokens = 0
    final_text = None

    for step in range(MAX_TOOL_LOOPS):
        try:
            response = chat(
                model=MODEL,
                messages=build_chat_messages(),
                tools=TOOL_FUNCTIONS,
                stream=False,
            )
        except ResponseError as e:
            error_text = str(e)

            if "XML syntax error" in error_text:
                return fallback_project_summary()

            return f"Ollama error: {error_text}"

        prompt_tokens = int(response.get("prompt_eval_count") or 0)
        completion_tokens = int(response.get("eval_count") or 0)
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens
        print(
            f"[token usage] in={prompt_tokens} out={completion_tokens} "
            f"(total in={total_prompt_tokens} out={total_completion_tokens})"
        )

        msg = response.get("message", {})
        messages.append(msg)

        content = msg.get("content")
        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            if content and content.strip():
                final_text = content.strip()
                break

            if saw_tool_call and last_tool_results:
                recovery_prompt = (
                    "You returned an empty answer. "
                    "Summarize the tool results clearly for the user. "
                    "Do not call tools again unless absolutely necessary."
                )
                messages.append({"role": "user", "content": recovery_prompt})
                continue

            final_text = "[No response from model.]"
            break

        saw_tool_call = True

        for call in tool_calls:
            function = call.get("function", {})
            name = function.get("name")
            args = normalize_tool_args(function.get("arguments", {}))

            if SHOW_TOOL_CALLS:
                print(f"[tool call] {name} {json.dumps(args, ensure_ascii=True)}")

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

            if SHOW_TOOL_CALLS:
                print(
                    "[tool result] "
                    f"{truncate(str(result), MAX_CONSOLE_TOOL_PREVIEW_CHARS)}"
                )

            messages.append(
                {
                    "role": "tool",
                    "name": name,
                    "content": str(result),
                }
            )

    if final_text is not None:
        update_session_summary()
        return final_text

    if last_tool_results:
        text = ["Tool loop stopped, but here are the latest tool results:\n"]
        for item in last_tool_results[-3:]:
            text.append(f"Tool: {item['tool']}")
            text.append(f"Args: {item['args']}")
            text.append("Result:")
            text.append(
                truncate(item["result"], MAX_CONSOLE_TOOL_PREVIEW_CHARS)
            )
            text.append("")
        update_session_summary()
        return "\n".join(text)

    update_session_summary()
    return "Stopped after too many tool calls."


def clear_history() -> None:
    global session_summary
    messages.clear()
    messages.append(
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    )
    session_summary = ""
