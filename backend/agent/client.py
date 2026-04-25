"""MiniMax client for openai-agents-python."""

import os
from functools import lru_cache
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

# Clear proxy env vars to avoid SOCKS intercept issues
for _k in list(os.environ.keys()):
    if 'proxy' in _k.lower():
        del os.environ[_k]


def _get_minimax_api_key() -> str:
    """Resolve MiniMax API key from hermes config."""
    import os as _os
    # Try environment variable first
    key = _os.environ.get("MINIMAX_API_KEY")
    if key:
        return key
    # Fallback: read from hermes .env file
    hermes_env = _os.path.expanduser("~/.hermes/.env")
    if _os.path.exists(hermes_env):
        with open(hermes_env) as f:
            for line in f:
                line = line.strip()
                if line.startswith("MINIMAX_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    if key and key != "***":
                        return key
    raise ValueError("MINIMAX_API_KEY not found in env or ~/.hermes/.env")


@lru_cache
def get_model():
    """Get configured OpenAIChatCompletionsModel for MiniMax (cached)."""
    api_key = _get_minimax_api_key()
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.minimax.chat/v1",
        timeout=60.0,
        max_retries=2,
    )
    return OpenAIChatCompletionsModel(
        model="MiniMax-M2.7-highspeed",
        openai_client=client,
    )
