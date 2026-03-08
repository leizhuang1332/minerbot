"""Configuration constants for MinerBot"""

import os

# ============== System Prompts ==============

DEFAULT_SYSTEM_PROMPT = """You are MinerBot, a helpful AI assistant.

You have access to tools to help you answer questions. Use them when needed.
Be concise and accurate in your responses."""

RESEARCH_SYSTEM_PROMPT = """You are an expert research assistant.

Your job is to:
1. Understand the user's research question thoroughly
2. Use available tools to gather information
3. Synthesize findings into clear, accurate summaries
4. Cite sources when possible

Be thorough and methodical in your research."""


# ============== Model Configuration ==============

# Default model settings
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-5-20250929")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.0"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "4096")) if os.getenv("DEFAULT_MAX_TOKENS") else None


# ============== LiteLLM Provider Settings ==============

# LiteLLM supports 100+ providers. API keys are read from environment variables:
# - ANTHROPIC_API_KEY (default for anthropic/* models)
# - OPENAI_API_KEY (default for openai/* models)
# - AZURE_API_KEY (for azure/* models)
# - GOOGLE_API_KEY (for google/* models)
# - COHERE_API_KEY (for cohere/* models)
# - AI21_API_KEY (for ai21/* models)
# - OLLAMA_API_BASE (for ollama/* models, e.g., "http://localhost:11434")
# - MINIMAX_API_KEY (for minimax/* models)

# MiniMax Anthropic-compatible API endpoint
MINIMAX_API_BASE = "https://api.minimax.io/anthropic/v1/messages"


# Model provider mapping (for reference)
MODEL_PROVIDERS = {
    "anthropic/": ["claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku"],
    "openai/": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    "azure/": ["gpt-4", "gpt-35-turbo"],
    "google/": ["gemini-pro", "gemini-pro-vision"],
    "ollama/": ["llama2", "mistral", "codellama"],
    "minimax/": ["MiniMax-M2.5", "MiniMax-M2.1"],
}
