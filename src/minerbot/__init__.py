"""MinerBot - AI Assistant built with LangChain DeepAgents"""

from minerbot.core import create_agent, create_research_agent, chat
from minerbot.core.agent import AgentSingleton
from minerbot.app import Application

__version__ = "0.1.0"
__all__ = ["create_agent", "create_research_agent", "chat", "AgentSingleton", "Application"]
