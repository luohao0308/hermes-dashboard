"""LLM client for openai-agents-python."""

import os
from functools import lru_cache
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

# Clear proxy env vars to avoid SOCKS intercept issues
for _k in list(os.environ.keys()):
    if 'proxy' in _k.lower():
        del os.environ[_k]


def _get_api_key(provider: str = "deepseek") -> str:
    """Resolve API key from hermes config."""
    import os as _os
    env_var = f"{provider.upper()}_API_KEY"
    # Try environment variable first
    key = _os.environ.get(env_var)
    if key:
        return key
    # Fallback: read from hermes .env file
    hermes_env = _os.path.expanduser("~/.hermes/.env")
    if _os.path.exists(hermes_env):
        with open(hermes_env) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{env_var}="):
                    key = line.split("=", 1)[1].strip()
                    if key and key != "***":
                        return key
    raise ValueError(f"{env_var} not found in env or ~/.hermes/.env")


@lru_cache
def get_model():
    """Get configured OpenAIChatCompletionsModel for DeepSeek (cached)."""
    api_key = _get_api_key("deepseek")
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
        timeout=60.0,
        max_retries=2,
    )
    return OpenAIChatCompletionsModel(
        model="deepseek-v4-flash",
        openai_client=client,
    )
