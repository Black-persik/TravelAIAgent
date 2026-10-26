"""Chat model factory: OpenRouter through LangChain's OpenAI-compatible client."""

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import Settings


def build_chat_model(settings: Settings, *, model: str | None = None) -> BaseChatModel:
    """Return a chat model served by OpenRouter.

    `model` defaults to the strong model; pass `settings.llm_model_fast` for cheap tasks.
    """
    return ChatOpenAI(
        model=model or settings.llm_model_smart,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        temperature=0.3,
        timeout=60,
        max_retries=2,
        # Optional OpenRouter attribution header: shows the app name in OpenRouter stats.
        default_headers={"X-Title": "TravelAIAgent"},
    )
