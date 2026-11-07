# FastAPI Inventory and LLM Agent

A CSV-backed API and a Python CLI agent with a manually implemented tool loop. No agent framework is used; the OpenAI SDK only calls the model. [Documentación en español](README.es.md).

**Quick start:** the API is in [api/app.py](api/app.py) and the agent is in [agent.py](agent.py). After installing dependencies, run `python -m uvicorn api.app:app --host 127.0.0.1 --port 8000` in one terminal. In another, configure the key, host and model as described below, then run `python agent.py`. Keep the API running while using the agent.

## Install

Requires Linux (`fcntl` file locking), Python 3.10+ and an OpenAI or compatible-provider key for a model supporting function tools. Run from the project root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run

Start the API first in terminal 1:

```bash
source .venv/bin/activate
export INVENTORY_ALERT_THRESHOLD=10
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
```

Interactive documentation: http://127.0.0.1:8000/docs. Stop with `Ctrl+C`.

In terminal 2, enter the key without saving it in source code or shell history, then start the agent:

```bash
source .venv/bin/activate
read -rsp "OPENAI_API_KEY: " OPENAI_API_KEY
printf '\n'
export OPENAI_API_KEY
export OPENAI_MODEL=gpt-4o-mini
export INVENTORY_API_URL=http://127.0.0.1:8000
python agent.py
```

The agent checks API availability before accepting input. Model calls need Internet access and may incur charges. Enter `salir`, `exit` or `quit`, press `Ctrl+C`, or send EOF to exit.

Try: “Add 20 kg of rice”, “Remove 3 kg of rice”, “Show inventory”, or “Which products have fewer than 5 units?”.

## Use the 4Geeks Host

After entering your 4Geeks key into `OPENAI_API_KEY` using the `read` command above, set the destination and list the models available to your key:

```bash
export OPENAI_BASE_URL=https://llm.4geeks.ai/v1
python -c "from openai import OpenAI; print('\n'.join(model.id for model in OpenAI().models.list()))"
```

The following model was verified in this project. If your key does not have access to it, choose another listed model supporting tools:

```bash
export OPENAI_MODEL="madrid-spain/openrouter/deepseek/deepseek-v4-flash"
python agent.py
```

`OPENAI_API_KEY` keeps its name because the OpenAI-compatible SDK is used, but its value must be your 4Geeks key. Never share or print it. A 401 means this host rejected the credentials; a model error may mean the ID is incorrect or not enabled. To return to OpenAI, run `unset OPENAI_BASE_URL` and configure an OpenAI key and authorized model.

## Endpoints

| Method | Path | Input | Success |
| --- | --- | --- | --- |
| GET | `/inventory` | None | 200, all products |
| POST | `/inventory` | `{"name":"Rice","quantity":20,"unit":"kg"}` | 201, product with `id` |
| PATCH | `/inventory/{product_id}` | `{"delta":-3}` | 200, updated product |
| GET | `/inventory/alerts` | Optional `?threshold=5` | 200, products below the threshold |

Quantities and deltas are integers, not fractions. Names and units must not be blank and stock cannot be negative. The threshold defaults to 10; set `INVENTORY_ALERT_THRESHOLD` before API startup or override per request with `threshold`. The comparison is strictly less than.

Errors include a descriptive `detail`: 404 for missing IDs, 409 for insufficient stock, 422 for invalid input, and 500 for inventory storage failures.

## Agent and Storage

Observe (input and history) → Think (LLM request) → Act (HTTP tools) → Update (results linked through `tool_call_id`) → Repeat. All calls are processed and the loop ends when the model returns a response without pending tools. Each turn allows at most 20 LLM requests. Mutations are not automatically retried; a connection failure warns the model to inspect inventory before repeating an operation.

History is in memory for the current session only. Files are located in the project root regardless of the working directory:

- `products.csv`: `id,name,quantity,unit`; created on first inventory access. IDs are incremental, updates use a process-shared lock and atomic file replacement.
- `conversation_log.csv`: `actor,message,tool_call,timestamp`; append-only across sessions with UTC ISO 8601 timestamps. Actors are `user`, `agent`, `tool_call` and `tool_result`. Tool metadata is JSON encoded within CSV fields.

Generated CSV files and credential files are excluded from Git. Logs may contain private data; restrict file access. This exercise API has no authentication and should remain bound to localhost.

### Contributors

This template was built as part of the [4Geeks Python Resources](https://4geeks.com/technology/python) for learning at [4Geeks.com](https://4geeks.com) by [Alejandro Sanchez](https://twitter.com/alesanchezr) and [many other contributors](https://github.com/4GeeksAcademy/python-hello/graphs/contributors).
