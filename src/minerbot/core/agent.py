"""Agent factory - creates DeepAgent instances"""

from typing import Any, Optional, Tuple

from minerbot.models import get_model
from .config import DEFAULT_SYSTEM_PROMPT, RESEARCH_SYSTEM_PROMPT


class AgentSingleton:
    _instance: Any = None
    _config: Tuple[str, str, bool] | None = None
    
    @classmethod
    def get_instance(
        cls,
        model_name: str = "claude-sonnet-4-5-20250929",
        system_prompt: str | None = None,
        enable_search: bool = True,
    ) -> Any:
        """Get or create a singleton DeepAgent instance.
        
        Args:
            model_name: Model to use (default: Claude Sonnet 4.5)
            system_prompt: Custom system prompt
            enable_search: Whether to enable web search tool
        
        Returns:
            Compiled DeepAgent instance
        """
        from deepagents import create_deep_agent
        from minerbot.tools import get_search_tool
        
        # Handle default prompt
        if system_prompt is None:
            system_prompt = DEFAULT_SYSTEM_PROMPT
        
        # Create configuration key
        new_config = (model_name, system_prompt, enable_search)
        
        # Reuse existing agent if configuration hasn't changed
        if cls._instance is not None and cls._config == new_config:
            return cls._instance
        
        # Get model
        model = get_model(model_name)
        
        # Build tools list
        tools = []
        
        if enable_search:
            search_tool = get_search_tool()
            if search_tool:
                tools.append(search_tool)
        
        # Create agent
        agent = create_deep_agent(
            model=model,
            tools=tools if tools else None,
            system_prompt=system_prompt,
        )
        
        # Update instance and configuration
        cls._instance = agent
        cls._config = new_config
        
        return agent
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance."""
        cls._instance = None
        cls._config = None
    
    @classmethod
    def get_config(cls) -> Tuple[str, str, bool] | None:
        """Get current configuration."""
        return cls._config


def create_agent(
    model_name: str = "claude-sonnet-4-5-20250929",
    system_prompt: str | None = None,
    enable_search: bool = True,
) -> Any:
    """Wrapper for backward compatibility."""
    return AgentSingleton.get_instance(model_name, system_prompt, enable_search)


def create_research_agent(
    model_name: str = "claude-sonnet-4-5-20250929",
) -> Any:
    """Create a research-focused DeepAgent.
    
    Args:
        model_name: Model to use
    
    Returns:
        Compiled DeepAgent optimized for research
    """
    return create_agent(
        model_name=model_name,
        system_prompt=RESEARCH_SYSTEM_PROMPT,
        enable_search=True,
    )


def chat(agent: Any, message: str) -> str:
    """Simple chat interface.
    
    Args:
        agent: DeepAgent instance
        message: User message
    
    Returns:
        Agent response text
    """
    result = agent.invoke({"messages": [{"role": "user", "content": message}]})
    return result["messages"][-1].content


if __name__ == "__main__":
    # Quick test
    agent = create_agent()
    response = chat(agent, "What is LangChain DeepAgents?")
    print(response)
