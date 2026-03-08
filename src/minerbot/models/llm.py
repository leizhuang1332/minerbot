"""LLM model initialization using LiteLLM"""


from langchain_litellm import ChatLiteLLM

# Model provider mapping - maps prefixes to LiteLLM model identifiers
MODEL_PROVIDER_MAP = {
    "claude": "anthropic/",  # Claude models
    "gpt": "openai/",        # OpenAI models
    "azure/": "azure/",      # Azure OpenAI
    "gemini": "google/",      # Google models
    "ollama/": "ollama/",    # Ollama local models
    "minimax": "minimax/",   # MiniMax models
}


# MiniMax Anthropic-compatible API endpoint
MINIMAX_ANTHROPIC_API_BASE = "https://api.minimax.io/anthropic/v1/messages"


def _get_litellm_model(model_name: str) -> str:
    """Convert model name to LiteLLM format.

    Args:
        model_name: Original model name (e.g., "claude-sonnet-4-5-20250929")

    Returns:
        LiteLLM formatted model name (e.g., "anthropic/claude-sonnet-4-5-20250929")
    """
    # Check if model already has a provider prefix (contains "/")
    if "/" in model_name:
        # Already has prefix, return as-is
        return model_name

    # Default: treat as Anthropic model
    if "claude" in model_name.lower():
        return f"anthropic/{model_name}"

    # Default: treat as OpenAI model for gpt models
    if "gpt" in model_name.lower():
        return f"openai/{model_name}"

    # Default: treat as Google model for gemini
    if "gemini" in model_name.lower():
        return f"google/{model_name}"

    # Default: treat as MiniMax model
    if "minimax" in model_name.lower():
        return f"minimax/{model_name}"

    # Default fallback to anthropic
    return f"anthropic/{model_name}"


def _is_minimax_model(model_name: str) -> bool:
    """Check if the model is a MiniMax model."""
    return (
        model_name.lower().startswith("minimax")
        or model_name.startswith("minimax/")
    )


def get_model(
    model_name: str = "claude-sonnet-4-5-20250929",
    temperature: float = 0.0,
    max_tokens: int | None = None,
    api_base: str | None = None,
) -> ChatLiteLLM:
    """Initialize the LLM model using LiteLLM.

    LiteLLM supports 100+ LLM providers including:
    - OpenAI (gpt-4o, gpt-4-turbo, etc.)
    - Anthropic (claude-3-5-sonnet, claude-3-opus, etc.)
    - Azure OpenAI
    - Google (gemini-pro, etc.)
    - Ollama (local models)
    - MiniMax (M2.5, M2.1, etc.)
    - And many more...

    Args:
        model_name: Model identifier. Examples:
            - "claude-sonnet-4-5-20250929" -> Anthropic
            - "openai/gpt-4o" -> OpenAI
            - "azure/gpt-4" -> Azure OpenAI
            - "gemini-pro" -> Google
            - "ollama/llama2" -> Ollama
            - "MiniMax-M2.5" -> MiniMax (Anthropic-compatible)
            - "minimax/MiniMax-M2.5" -> MiniMax
        temperature: Sampling temperature. Defaults to 0.
        max_tokens: Maximum tokens to generate. Optional.
        api_base: Custom API base URL. Optional.

    Returns:
        Initialized ChatLiteLLM model

    Environment Variables:
        Supported providers require respective API keys:
        - ANTHROPIC_API_KEY (for anthropic/*)
        - OPENAI_API_KEY (for openai/*)
        - AZURE_API_KEY (for azure/*)
        - GOOGLE_API_KEY (for google/*)
        - OLLAMA_API_BASE (for ollama/*)
        - MINIMAX_API_KEY (for minimax/*)
    """
    # Convert model name to LiteLLM format
    litellm_model = _get_litellm_model(model_name)

    # Build kwargs for ChatLiteLLM
    kwargs = {
        "model": litellm_model,
        "temperature": temperature,
    }

    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    # Set custom_llm_provider and api_base for special cases
    if model_name.startswith("azure/"):
        kwargs["custom_llm_provider"] = "azure"
    elif model_name.startswith("ollama/"):
        kwargs["custom_llm_provider"] = "ollama"
    elif _is_minimax_model(model_name):
        kwargs["custom_llm_provider"] = "minimax"

    # For MiniMax, use Anthropic-compatible API endpoint
    if _is_minimax_model(model_name):
        if api_base:
            kwargs["api_base"] = api_base
        else:
            kwargs["api_base"] = MINIMAX_ANTHROPIC_API_BASE
    if model_name.startswith("azure/") or _is_minimax_model(model_name):
        kwargs["custom_llm_provider"] = "azure"
    elif model_name.startswith("ollama/"):
        kwargs["custom_llm_provider"] = "ollama"

    # For MiniMax, use Anthropic-compatible API endpoint
    if _is_minimax_model(model_name):
        if api_base:
            kwargs["api_base"] = api_base
        else:
            kwargs["api_base"] = MINIMAX_ANTHROPIC_API_BASE

    return ChatLiteLLM(**kwargs)


def get_model_info(model_name: str) -> dict[str, str]:
    """Get information about a model.

    Args:
        model_name: Model identifier

    Returns:
        Dictionary with model info (provider, model_id, etc.)
    """
    litellm_model = _get_litellm_model(model_name)

    parts = litellm_model.split("/", 1)
    provider = parts[0] if len(parts) > 1 else "anthropic"
    model_id = parts[1] if len(parts) > 1 else parts[0]

    return {
        "provider": provider,
        "model_id": model_id,
        "litellm_name": litellm_model,
    }
