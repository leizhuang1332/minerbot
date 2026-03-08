# MinerBot

AI Assistant built with LangChain DeepAgents

## Setup

```bash
# Install dependencies
uv sync

# Copy environment variables
cp .env.example .env

# Edit .env with your API keys
```

## Usage

```python
from minerbot import create_agent

agent = create_agent()
result = agent.invoke({"messages": [{"role": "user", "content": "Your question"}]})
print(result["messages"][-1].content)
```
