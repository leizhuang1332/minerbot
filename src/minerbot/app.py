"""Main application entry point for MinerBot"""

import sys
import asyncio
from typing import Any

from minerbot.core.agent import AgentSingleton


class Application:
    """Main application class for MinerBot"""
    
    def __init__(self):
        self.agent: Any | None = None
        self.running: bool = False
    
    async def initialize(self) -> None:
        """Initialize application components."""
        print("Initializing application...")
        
        # Initialize agent singleton
        self.agent = AgentSingleton.get_instance()
        config = AgentSingleton.get_config()
        if config:
            print(f"Agent initialized with model: {config[0]}")
        
        # TODO: Initialize MessageBus
        # TODO: Initialize ChannelManager
        
        print("Application initialized successfully")
    
    async def run(self) -> None:
        """Run the application main loop."""
        if not self.agent:
            await self.initialize()
        
        self.running = True
        print("\nAgent is ready. Type 'exit' to quit.")
        
        while self.running:
            try:
                # Get user input asynchronously
                user_input = await asyncio.to_thread(input, "> ")
                
                if user_input.lower() == "exit":
                    self.running = False
                    break
                
                if not user_input.strip():
                    continue
                
                # Process input using the agent
                print("\nThinking...")
                result = self.agent.invoke({
                    "messages": [{"role": "user", "content": user_input}]
                })
                
                # Extract and print response
                response = result["messages"][-1].content
                print(f"\nAgent: {response}\n")
                
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                print(f"\nError: {str(e)}\n")
        
        print("\nApplication exited")
    
    async def shutdown(self) -> None:
        """Shutdown the application and clean up resources."""
        print("\nShutting down application...")
        
        # Reset agent singleton to free memory
        AgentSingleton.reset()
        self.agent = None
        
        # TODO: Shutdown MessageBus
        # TODO: Shutdown ChannelManager
        
        print("Application shutdown complete")


async def main() -> None:
    """Main entry point for the application."""
    app = Application()
    try:
        await app.initialize()
        await app.run()
    finally:
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())