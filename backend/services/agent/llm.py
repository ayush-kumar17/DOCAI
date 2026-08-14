"""
LLM Factory

Returns the right LLM based on config.
Supports Gemini (free tier) and OpenAI.

Why abstract this?
- Easy to switch providers
- Easy to add fallback logic
- Config-driven, not hardcoded
"""

from functools import lru_cache
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache()
def get_llm():
    """
    Return configured LLM instance.
    Cached — only created once per process.

    Prefers Gemini if GOOGLE_API_KEY is set.
    Falls back to OpenAI if OPENAI_API_KEY is set.
    Raises if neither is configured.
    """
    if settings.LLM_PROVIDER == "gemini" and settings.GOOGLE_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI

        logger.info(f"Using Gemini: {settings.LLM_MODEL}")
        return ChatGoogleGenerativeAI(
            model              = settings.LLM_MODEL,
            google_api_key     = settings.GOOGLE_API_KEY,
            temperature        = 0.1,     # low temp for factual answers
            convert_system_message_to_human = True,
        )

    if settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI

        model = settings.LLM_MODEL if settings.LLM_PROVIDER == "openai" else "gpt-4o-mini"
        logger.info(f"Using OpenAI: {model}")
        return ChatOpenAI(
            model       = model,
            api_key     = settings.OPENAI_API_KEY,
            temperature = 0.1,
            streaming   = True,
        )

    raise RuntimeError(
        "No LLM configured. Set GOOGLE_API_KEY or OPENAI_API_KEY in .env"
    )