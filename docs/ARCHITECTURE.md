# Architecture

Living document: it records the current design and the reasons behind it. Update it in the same PR when a decision changes. Requirements are in `docs/TASK.md`.

## Principles
- **The agent acts, the code decides facts.** LLMs understand requests, plan and explain. Prices, dates, budgets and connection checks are plain Python.
- **State, not chat history.** Every trip is a structured `TripState`. Replanning, the cart and explanations all work on it.
- **Honest data.** Real sources where possible, synthetic data where not, always labelled.
- **Deployed from day one.** Every stage ends with a working version on the server.

## Framework roles
| Framework | Role | Used for |
|---|---|---|
| LangChain | Building blocks | OpenRouter models (`ChatOpenAI` with the OpenRouter base URL), tool definitions, structured output into Pydantic models |
| LangGraph | Skeleton | Graph of stages, `TripState`, Postgres checkpointer (sessions survive restarts), `interrupt` for clarifying questions and payment confirmation, `Send` for parallel search |
| LlamaIndex | Knowledge | RAG over hotel descriptions, reviews and destination guides; hybrid search = metadata filters (city, price, pets allowed) + semantic query. Exposed to the graph as a tool |

Each framework does one job; we do not build RAG twice or keep state in two places.

## Deployment
One VPS with Docker Compose, deployed from `main` by CI/CD. CI builds the `api` image, publishes it to GitHub Container Registry tagged with the commit, writes `.env` on the server from the GitHub Environment `production`, then runs `docker compose pull && docker compose up -d` and checks `/api/health`. The server never builds code; rolling back means switching the image tag. Until a domain is bought, the site uses a free `<ip>.sslip.io` hostname so Caddy can still issue an HTTPS certificate.

- `api`: FastAPI app with the LangGraph agent; answers stream over SSE.
- `mcp-tools`: MCP server (FastMCP) with hotel, flight, weather and transfer tools, connected to the agent via `langchain-mcp-adapters`. The same tools can be reused by other MCP clients or a baseline agent.
- `postgres` with pgvector: LangGraph checkpoints, user memory across sessions and the LlamaIndex vector index. One database, one backup.
- `caddy`: reverse proxy with automatic HTTPS; serves the website from `web/` and proxies `/api` to `api`. The only service with published ports (80, 443).
- External: OpenRouter (LLMs) and Langfuse (tracing; cloud free tier first, self-hosting later if needed).

`docker-compose.yml` is the server configuration; `docker-compose.override.yml` adds local-only settings (build from source, reload, ports on `127.0.0.1`).

The public UI is protected by a login, rate limiting and a spending limit on the OpenRouter key.

## Web UI
API-first: the agent exposes a JSON + SSE API under `/api`, and the website in `web/` is a separate static frontend that calls it. Stage 1 ships a minimal chat page; the full interface (trip cards, comparison, cart) replaces it later without touching the agent. Nothing secret is ever shipped to the browser: every key stays on the server.

## TripState
```
TripState
├── profile        who travels, budget, departure city, dates, constraints, trip mood
├── assumptions    what the agent inferred itself ("departing from Moscow"), shown to the user
├── weights        what matters to this user (price, sea nearby, free cancellation, …)
├── destinations   3 candidates with reasoning, weather, price, travel time
├── options        found hotels, flights or trains, transfers
├── selection      what the user picked
├── cart           items + connection check results
└── stage          where the user is on the journey
```

## Graph
1. **Parse request.** Structured extraction of `profile` and `assumptions`, including hidden requirements ("with a child" → flights under ~5 h, no night flights, free cancellation).
2. **Ask or act.** Ask only when a missing field blocks the search (usually departure city and rough dates). Everything else is assumed and shown as editable assumptions.
3. **Inspiration.** Three contrasting destinations: the obvious one, the budget one and an unexpected one.
4. **Search and compare.** Tools called in parallel; ranking by the user's `weights`.
5. **Explain.** For each recommendation: why it fits, what was sacrificed, the risks, and who it does *not* suit.
6. **Assemble and validate.** Deterministic validator: arrival + transfer time vs check-in time, nights vs flight dates, total door-to-door cost vs budget.
7. **Cart and simulated payment** behind an `interrupt` confirmation.

**Replanning** uses field dependencies: changing `profile.dates` invalidates flights, availability and checks, but keeps the destination, weights and preferred hotel type. "Our dog is coming" re-filters only hotels and transfers. The agent says what changed and why.

## Agent patterns: where they pay off
| Pattern | Where | Verdict |
|---|---|---|
| Graph vs ReAct | Outer flow is an explicit graph; the search node runs a ReAct sub-agent that picks tools itself | Hybrid beats either alone |
| Plan-and-execute | Trip assembly: plan flight / hotel / transfer, execute in parallel with `Send` | Pays off |
| Tree-of-Thoughts | Destination choice only: branch candidates, score, keep 3 contrasting ones | Only here; elsewhere it burns tokens |
| Self-Consistency | Request parsing: 3 independent extractions, vote per field. Fields that disagree become the clarifying questions | Pays off; doubles as an uncertainty detector |
| Reflection | Critic checks explanations against the profile and honesty about downsides, max 2 rounds | Partly: numbers are checked by code, reflection is for meaning |

Every pattern sits behind a flag so its gain can be measured against a plain baseline (`baseline/`).

## Multi-agent
- **Supervisor/worker:** supervisor plus "destination scout", "hotel agent" and "transport agent" (flights, trains, transfers).
- **Debate:** at the final comparison of 2–3 options, a "budget advocate" and a "comfort advocate" argue and a judge states the trade-off. Only at that step, because it is expensive.
- **Swarm:** not used; there are no independent agents that need to negotiate without a coordinator.

## Security
- **Prompt injection via reviews:** poisoned reviews in the RAG corpus are part of our red-team set.
- **User jailbreaks** ("book it for 0 ₽"): prices at checkout always come from the database, never from model text.
- **Guardrails:** Llama Guard on input and output (via OpenRouter), NeMo Guardrails for topic boundaries later.
- **Sandbox** only if a code-executing agent (smolagents CodeAgent) is added: separate container without network.
- **Secrets:** see `CLAUDE.md`; enforced by `.claude/settings.json`, `.gitignore`, gitleaks and GitHub push protection.

## Data sources
| Data | Source | Real or mock |
|---|---|---|
| Weather by month, sea temperature | Open-Meteo (historical and marine APIs) | Real |
| Destination catalogue | Own file: flight time from Moscow/St Petersburg, visa for Russian citizens, season, typical prices | Curated |
| Flight prices | Travelpayouts / Aviasales Data API (cached prices) | Real or mock |
| Trains | No usable open API | Mock |
| Hotels | Synthetic dataset generated once and stored (price, cancellation, meals, distance to sea, pets, kids club, review summary) | Mock |
| Transfers | Distance via OSRM/OpenStreetMap → time and price by formula | Semi-real |
| Sights, guides | OpenTripMap / OpenStreetMap, Wikivoyage (CC BY-SA, attribution required) | Real |

## Evals and observability
- **Golden dataset** of 100–200 requests: vague, specific, contradictory, adversarial and multi-turn with replanning, each with expected profile fields and hard constraints.
- **Three levels:** deterministic checks in code, LLM-as-judge with a rubric, trajectory evals on traces (right tools, no restart from scratch on replanning).
- **Simulated user:** an LLM persona completes the journey to checkout; yields completion rate, number of clarifications, time to first recommendation.
- **Langfuse** traces every step; a small eval subset runs in CI on each push.
- **Optimisation:** model routing (cheap model for extraction, strong for planning), stable system prompts for prompt caching, cached tool results, batched eval runs.

## Roadmap
1. Walking skeleton, in three PRs: (a) one-node LangGraph agent on OpenRouter, FastAPI with SSE, login, rate limits, Postgres checkpoints, Langfuse, Docker Compose for local runs; (b) CI, deployment from `main` via GHCR, Caddy with HTTPS; (c) minimal website.
2. Data and tools: destination catalogue, synthetic hotels, MCP server, LlamaIndex index in pgvector.
3. Core journey to checkout: `TripState`, parsing with Self-Consistency, search, comparison, validator, cart, `interrupt`.
4. Advanced patterns: replanning, ToT for destinations, supervisor/worker, debate, reflection.
5. Security: red-team with poisoned reviews, Llama Guard, NeMo, tool-level protection.
6. Evals and optimisation: golden dataset, judge, trajectories, simulated user, routing and caching, README with before/after numbers.
