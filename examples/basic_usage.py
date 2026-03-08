"""Basic usage examples for MinerBot"""

from minerbot import create_agent, create_research_agent, chat


def basic_chat():
    """Simple chat example."""
    agent = create_agent()
    response = chat(agent, "Hello, what can you do?")
    print(response)


def research_example():
    """Research agent example."""
    agent = create_research_agent()
    response = chat(agent, "What are the latest developments in AI agents?")
    print(response)


def custom_agent():
    """Custom agent with specific prompt."""
    agent = create_agent(
        system_prompt="You are a Python expert. Help users write clean code.",
    )
    response = chat(agent, "How do I create a decorator in Python?")
    print(response)


if __name__ == "__main__":
    basic_chat()
