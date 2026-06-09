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

Or run it directly:

```bash
source .venv/bin/activate
python agent.py
```

## Notes

- The default model is configured in [`agent.py`](./agent.py).
- The agent only works inside the current workspace and is intended for local project inspection and edits.
