# TravelAIAgent

An AI travel agent that turns one free-form message ("somewhere warm in November, not expensive, with a child, no long flights") into a complete trip plan and walks the traveller to a simulated checkout. Built with LangGraph, LangChain and LlamaIndex; started for the Ostrovok hackathon track "O!дин запрос".

- What the agent must do: [docs/TASK.md](docs/TASK.md)
- How it is built and why: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Status

**Stage 1, walking skeleton.** A one-node LangGraph agent answers through an OpenRouter model, streams the answer over SSE, keeps conversations in Postgres (they survive restarts) and traces runs to Langfuse. The API is protected by a login and rate limits.

Not yet: trip search, hotels, tickets, the cart (stages 2–3), the website (stage 1, next PRs) and deployment from `main` (stage 1, next PR).

## Run locally with Docker

Requirements: Docker with the Compose plugin.

1. Create your local settings and fill them in:
   ```bash
   cp .env.example .env
   ```
   Generate the secrets with `openssl rand -hex 32`. `.env` is gitignored; never commit it.
2. Start the agent and the database:
   ```bash
   docker compose up --build
   ```
3. Check that it is up:
   ```bash
   curl http://localhost:8000/api/health
   ```
4. Talk to the agent. Interactive API docs: http://localhost:8000/api/docs. Or with curl (this makes a real, paid LLM call):
   ```bash
   curl -c cookies.txt -H 'Content-Type: application/json' \
     -d '{"username": "<APP_USERNAME>", "password": "<APP_PASSWORD>"}' \
     http://localhost:8000/api/login

   curl -N -b cookies.txt -H 'Content-Type: application/json' \
     -d '{"thread_id": "'"$(python3 -c 'import uuid; print(uuid.uuid4())')"'", "message": "Somewhere warm in November with a kid"}' \
     http://localhost:8000/api/chat
   ```

`docker-compose.override.yml` is loaded automatically for local runs: it builds the image from source, reloads code on changes and exposes ports on `127.0.0.1` only. The server runs `docker-compose.yml` alone.

## Develop without Docker for the app

```bash
uv sync                              # install dependencies
docker compose up -d postgres        # database still in Docker
# in .env: POSTGRES_HOST=localhost and APP_ENV=local
uv run uvicorn app.api.main:create_app --factory --reload
```

## Tests and checks

```bash
uv run pytest                                         # offline: fake model, no keys
uv run ruff check --fix . && uv run ruff format .     # lint and format
uvx pre-commit install                                # once per clone: secret scan and lint on commit
```

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/health` | no | Liveness check |
| POST | `/api/login` | no | `{"username", "password"}`, sets a signed session cookie |
| POST | `/api/logout` | no | Clears the session |
| GET | `/api/me` | yes | Current user |
| POST | `/api/chat` | yes | `{"thread_id": "<uuid>", "message"}`; SSE events `token`, `done`, `error` |
| GET | `/api/threads/{thread_id}` | yes | Conversation history |

## Configuration

All settings are environment variables, read only in `app/config.py`. `.env.example` lists them and marks which ones are secrets. Production values live in GitHub (Environment `production`) and reach the server through CI/CD.

## License

MIT
