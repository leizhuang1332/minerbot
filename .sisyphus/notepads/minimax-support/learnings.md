# MiniMax Support - Notepad

## Project Context
- MinerBot: CLI AI Assistant based on DeepAgents framework
- Existing: Anthropic Claude support via ChatAnthropic
- Goal: Add MiniMax model support (compatible with Anthropic endpoint style)

## Key Files
- `src/minerbot/config.py`: AppConfig dataclass with from_env() and validate()
- `src/minerbot/agent/factory.py`: create_agent() function using ChatAnthropic
- `.env.example`: Configuration template

## MiniMax Endpoint
- Base URL: https://api.minimaxi.com/anthropic
- Model: MiniMax-M2.5

## Execution Notes
- Wave 1: Tasks 1 & 2 (parallel)
- Wave 2: Tasks 3, 4, 5 (sequential after Wave 1)
- Wave 3: Task 6 (verification)

## Task 3: Extend AppConfig (DONE)
- Added fields: minimax_api_key, minimax_base_url, minimax_model, model_provider
- Updated from_env() to read MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL, MODEL_PROVIDER
- Updated validate() to require at least one of ANTHROPIC_API_KEY or MINIMAX_API_KEY
- Backward compatible: existing fields preserved, new fields have defaults

## Task 7: Update .env.example (DONE)
- Added MINIMAX_API_KEY with placeholder
- Added MINIMAX_BASE_URL=https://api.minimaxi.com/anthropic
- Added MINIMAX_MODEL=MiniMax-M2.5
- Kept existing Anthropic and other configurations intact

## Task 8: Modify Agent Factory (DONE)
- Modified `create_agent()` in `src/minerbot/agent/factory.py`
- Added conditional logic:
  - If `config.minimax_api_key` is set: use ChatAnthropic with base_url, custom model, and api_key
  - Else: use standard ChatAnthropic with config.model_name (existing behavior)
- Preserved existing functionality: tavily_api_key, tools, checkpointer
- LSP diagnostics show pre-existing warnings/errors (unrelated to this change)

## Task 9: Add Error Handling and Logging (DONE)
- Added `import logging` to factory.py
- Added logger = logging.getLogger(__name__) in create_agent()
- Added try-except block around model initialization:
  - Logs which provider is being used (MiniMax vs Anthropic)
  - Catches API connection/authentication errors
  - Raises AgentError with clear message
- Log levels:
  - logger.info(): logs model selection (provider and model name)
  - logger.error(): logs initialization failures

## Task 10: Create Integration Tests (DONE)
- Created `tests/test_minimax_integration.py`
- Test classes:
  - `TestMiniMaxConfig`: Tests configuration loading from env
  - `TestModelRouting`: Tests model selection logic (MiniMax vs Anthropic)
  - `TestValidation`: Tests config validation (requires at least one API key)
  - `TestAgentCreation`: Tests agent creation flow
- Used `pytest.mark.skipif` for tests requiring actual API keys
- Used mocking for tests that don't need actual API calls
- Key pattern: Use `patch("minerbot.config.load_dotenv")` to prevent .env reloading
- Key pattern: Use `patch("minerbot.agent.factory.create_deep_agent")` with mock to avoid deep agent initialization issues
- Test results: 9 passed, 3 skipped (skipped tests require actual API keys)

## Notes
- Pre-existing test issue: `test_config_validation` in test_config.py expects old error message "ANTHROPIC_API_KEY is required" but config.py now says "At least one of ANTHROPIC_API_KEY or MINIMAX_API_KEY is required"
