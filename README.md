# Small Agent

Local autonomous coding agent built on top of `ollama`.

## Requirements

- Python 3.10+
- `ollama` installed and running locally
- A model available in Ollama, for example:
  - `qwen3.5:9b`
  - `qwen2.5-coder:7b`
  - `qwen3:8b`

## Setup

Create a virtual environment and install the Python dependency:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ollama
```

If you do not already have a model pulled in Ollama, install one first:

```bash
ollama pull qwen3.5:9b
```

## Run

Start the agent with:

```bash
./run-agent.sh
```

You can also override the runtime settings from the CLI:

```bash
./run-agent.sh --model qwen2.5-coder:7b
./run-agent.sh --workspace /path/to/project
./run-agent.sh --max-tool-loops 20 --no-show-tool-calls
```

Or run it directly:

```bash
source .venv/bin/activate
python agent.py --model qwen3.5:9b
```

## Notes

- The default model is configured in [`config.py`](./config.py).
- Runtime overrides are available through CLI flags and the `/config` command.
- The agent only works inside the current workspace and is intended for local project inspection and edits.
