"""FastAPI application factory.

Run with: uvicorn app.api.main:create_app --factory
A factory (instead of a module-level `app`) lets tests build the app with a fake
model and an in-memory checkpointer, without settings from the environment.
"""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from starlette.middleware.sessions import SessionMiddleware

from app.api import auth, chat
from app.api.rate_limit import RateLimiter
from app.config import Settings, get_settings
from app.graph.builder import build_graph
from app.llm import build_chat_model
from app.observability import build_langfuse

SESSION_MAX_AGE_SECONDS = 7 * 24 * 3600


async def open_postgres_checkpointer(
    settings: Settings, stack: AsyncExitStack
) -> AsyncPostgresSaver:
    """Postgres checkpointer on a small connection pool.

    The pool reconnects if Postgres restarts; `setup()` creates the checkpoint
    tables on first start and is a no-op afterwards.
    """
    pool = AsyncConnectionPool(
        conninfo=settings.database_url,
        max_size=5,
        open=False,
        # Settings required by the LangGraph Postgres checkpointer.
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        check=AsyncConnectionPool.check_connection,
    )
    await pool.open(wait=True, timeout=30)
    stack.push_async_callback(pool.close)
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    return checkpointer


def create_app(
    settings: Settings | None = None,
    llm: BaseChatModel | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            saver = checkpointer or await open_postgres_checkpointer(settings, stack)
            langfuse = build_langfuse(settings)
            if langfuse is not None:
                stack.callback(langfuse.shutdown)  # flush pending traces on shutdown

            app.state.settings = settings
            app.state.graph = build_graph(llm or build_chat_model(settings), saver)
            app.state.chat_limiter = RateLimiter(settings.chat_rate_limit_per_minute)
            app.state.login_limiter = RateLimiter(settings.login_rate_limit_per_minute)
            yield

    app = FastAPI(
        title="TravelAIAgent",
        lifespan=lifespan,
        # Interactive API docs only for local development.
        docs_url="/api/docs" if settings.is_local else None,
        openapi_url="/api/openapi.json" if settings.is_local else None,
        redoc_url=None,
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret.get_secret_value(),
        session_cookie="travel_session",
        max_age=SESSION_MAX_AGE_SECONDS,
        same_site="lax",
        https_only=not settings.is_local,
    )

    @app.get("/api/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(chat.router)
    return app
