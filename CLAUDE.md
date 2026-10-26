# TravelAIAgent

AI travel agent that turns one free-form message ("somewhere warm in November, cheap, with a kid, no long flights") into a complete trip: destination, hotel, transport and transfers, then walks the user to a simulated checkout. Started for the Ostrovok hackathon track "O!дин запрос", maintained as a deployed pet project.

Read on demand, not every session:
- `docs/TASK.md`: the hackathon task and requirements. Read before changing agent behaviour.
- `docs/ARCHITECTURE.md`: architecture and the reasoning behind decisions. Read before adding modules.

## Working with the user
- The user is new to AI engineering. Talk to them in **Russian**. Write code, comments, commit messages and docs in **English**.
- Before any non-trivial change (new module, architecture change, or more than ~3 files), post a short plan with 1–2 alternatives and their trade-offs, then wait for approval.
- After a change, summarise in a few lines: what changed, why, and how to verify it.
- When you introduce a new concept (a LangGraph feature, a pattern like Reflection), explain it in one or two sentences.
- Prefer simple, readable code over clever code.

## Secrets: non-negotiable
Secrets live only in the local `.env` file and in GitHub Actions Secrets. You never see their values and never need to.

- NEVER read, open, print, search or copy `.env` or `.env.*`. The only exception is `.env.example`, which holds variable names with empty values.
- NEVER run commands that expose the environment: `env`, `printenv`, `set`, `echo $SOME_KEY`, or code that prints `os.environ`.
- NEVER ask the user to paste a key, token or password into the chat.
- NEVER hardcode secrets, tokens or credentialed URLs in code, tests, docs, notebooks or commit messages.
- Application code reads configuration only through `app/config.py` (pydantic-settings). To add a variable: add a field there (secrets get no default), add the name with an empty value to `.env.example`, and mention it in your summary so the user can set it.
- Tests never use real keys: fake values (`sk-test-...`) via `monkeypatch`, fake chat models from `langchain_core` instead of real LLMs.
- CI/CD workflows reference secrets only as `${{ secrets.NAME }}`.
- Stage files by explicit path. Never use `git add -A`, `git add .` or `git commit -a`. Check `git status` and `git diff --cached` before every commit.
- If a secret is exposed anywhere (tool output, diff, commit): stop, tell the user immediately and recommend rotating the key. Do not rewrite git history without approval.

These rules are enforced by `.claude/settings.json` (deny rules), `.gitignore`, a gitleaks pre-commit hook and GitHub push protection. Never weaken or bypass any of them, for example with `--no-verify`.

## Ask before you
- Make any real call to a paid API (LLMs via OpenRouter, paid search, etc.). The default is mocked.
- Change deployment or CI: `Dockerfile`, `docker-compose*.yml`, `deploy/`, `.github/workflows/`.
- Delete files, datasets or database data, or write destructive migrations.

Adding dependencies is fine: use `uv add <pkg>` (or `uv add --dev <pkg>`) and say why in your summary.

## Commands
- Install: `uv sync`
- Tests: `uv run pytest`
- Lint and format: `uv run ruff check --fix . && uv run ruff format .`
- Pre-commit hooks, once per fresh clone (every cloud session starts from a fresh clone): `uvx pre-commit install`
- Run the app: see `README.md`

## Stack
Python 3.12 · uv · LangGraph (orchestration, state, checkpoints) · LangChain (OpenRouter models, tools, structured output) · LlamaIndex (RAG over hotels, reviews, guides) · FastAPI + Gradio · Postgres + pgvector · Langfuse (tracing) · MCP server for tools.

## Layout
- `app/graph/`: LangGraph nodes, `TripState`, graph assembly
- `app/agents/`: supervisor and worker agents
- `app/rag/`: LlamaIndex ingestion and query engines
- `app/validators/`: budget, dates and connection checks (pure Python)
- `app/api/`, `app/ui/`: FastAPI, Gradio, Telegram bot
- `mcp_tools/`: MCP server with hotel, flight, weather and transfer tools
- `data/`: synthetic data generators and destination catalogue
- `evals/`: golden dataset, LLM-as-judge, simulated user
- `tests/`: mirrors `app/`

## Architecture rules
- `TripState` is the single source of truth for a trip. Nodes read and update it; they do not re-derive facts from chat history.
- Money, dates and connections (arrival → transfer → check-in) are computed in plain Python in `app/validators/`, never by the LLM. The LLM only explains the results.
- Prices at checkout always come from data and tools, never from model output.
- Replanning ("two days later", "smaller budget") updates only the affected `TripState` fields and re-runs only dependent nodes. Never restart the search from scratch.
- LLM output that feeds `TripState` uses structured output (Pydantic models), not free-text parsing.
- Mocked or synthetic data is labelled as such (`source="mock"`), so the UI can say so honestly.

## Git workflow
- One branch per task: `feat/…`, `fix/…`, `docs/…`, `chore/…`. Never commit to `main` directly.
- Conventional Commits: `feat: add hotel search tool`.
- Before committing, `uv run ruff check .` and `uv run pytest` must pass.
- Open a PR into `main`. The user reviews and merges. Merging into `main` deploys to the user's server via CI/CD.

## Testing
- Tests are required for validators, tools and graph nodes.
- Tests run offline with no keys; LLM and HTTP calls are mocked.

## Keeping this file current
Update this file in the same PR when commands, layout or rules change. Keep it under ~150 lines and move details into `docs/`.
