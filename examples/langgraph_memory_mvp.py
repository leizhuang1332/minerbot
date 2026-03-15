import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.runnables.config import RunnableConfig
from langchain_anthropic import ChatAnthropic

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.runtime import Runtime
from langgraph.store.sqlite.aio import AsyncSqliteStore
from langgraph.store.base import BaseStore


@dataclass
class Context:
    user_id: str
    user_name: str = "Anonymous"


class MemoryMVP:
    
    def __init__(self, db_path: str = "data/memory_mvp.db"):
        self.db_path: str = db_path
        self.checkpointer: AsyncSqliteSaver | None = None
        self.store: BaseStore | None = None
        self.graph: Any = None
        self.model: ChatAnthropic | None = None
        
    async def initialize(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        import aiosqlite
        conn = await aiosqlite.connect(self.db_path)
        self.checkpointer = AsyncSqliteSaver(conn)
        await self.checkpointer.setup()
        
        store_conn = await aiosqlite.connect(self.db_path)
        self.store = AsyncSqliteStore(store_conn)
        await self.store.setup()
        
        self.model = ChatAnthropic(model_name="claude-sonnet-4-20250514")
        
    async def create_graph(self):
        
        async def call_model(state: MessagesState, runtime: Runtime[Context]):
            user_id = runtime.context.user_id
            user_name = runtime.context.user_name
            
            messages = state.get("messages", [])
            
            namespace = (user_id, "profile")
            memory_text = ""
            if runtime.store:
                try:
                    memories = await runtime.store.asearch(namespace, limit=3)
                    if memories:
                        memory_text = "\n".join([f"- {m.value.get('key', 'unknown')}: {m.value.get('value', '')}" 
                                                for m in memories])
                except Exception:
                    memory_text = ""
            
            system_msg = f"""你是一个友好的 AI 助手。
当前用户: {user_name} (ID: {user_id})
"""
            if memory_text:
                system_msg += f"\n用户档案:\n{memory_text}"
            
            last_msg = ""
            if messages:
                last_msg = str(messages[-1].content) if hasattr(messages[-1], 'content') else str(messages[-1])
            if "remember" in last_msg.lower() or "记住" in last_msg:
                memory_key = "user_preference"
                memory_value = last_msg
                if runtime.store:
                    await runtime.store.aput(namespace, memory_key, {
                        "value": memory_value,
                        "created_at": datetime.now().isoformat()
                    })
            
            if self.model:
                response = self.model.invoke(
                    [{"role": "system", "content": system_msg}] + messages
                )
                return {"messages": [response]}
            return {"messages": []}
        
        builder = StateGraph(MessagesState, context_schema=Context)
        builder.add_node("call_model", call_model)
        builder.add_edge(START, "call_model")
        
        self.graph = builder.compile(
            checkpointer=self.checkpointer,
            store=self.store
        )
        
    async def test_short_term_memory(self):
        
        thread_id = "test_thread_1"
        config = RunnableConfig(
            configurable={
                "thread_id": thread_id,
                "metadata": {"test": "short_term_memory"}
            }
        )
        
        if self.graph:
            async for chunk in self.graph.astream(
                {"messages": [("user", "你好，我叫 Bob")]},
                config=config,
                context=Context(user_id="user_1", user_name="Bob")
            ):
                for output in chunk.values():
                    if isinstance(output, dict) and "messages" in output:
                        msg = output["messages"][-1]
                        content = getattr(msg, "content", str(msg)) if hasattr(msg, "content") else str(msg)
                        print(f"    AI: {content[:100]}...")
            
            state = self.graph.get_state(config)
            
            async for chunk in self.graph.astream(
                {"messages": [("user", "我刚才说我叫什么？")]},
                config=config,
                context=Context(user_id="user_1", user_name="Bob")
            ):
                for output in chunk.values():
                    if isinstance(output, dict) and "messages" in output:
                        msg = output["messages"][-1]
                        content = getattr(msg, "content", str(msg)) if hasattr(msg, "content") else str(msg)
                        print(f"    AI: {content[:200]}...")
            
            history = list(self.graph.get_state_history(config))
        
    async def test_long_term_memory(self):
        
        user_id = "user_2"
        namespace = (user_id, "profile")
        
        if self.store:
            await self.store.aput(namespace, "name", {"value": "Alice", "type": "name"})
            await self.store.aput(namespace, "favorite_color", {"value": "blue", "type": "preference"})
            await self.store.aput(namespace, "hobby", {"value": "reading", "type": "interest"})
            
            results = await self.store.asearch(namespace)
            
            item = await self.store.aget(namespace, "name")
            if item:
                print(f"    name: {item.value}")
                
            await self.store.adelete(namespace, "hobby")
            results = await self.store.asearch(namespace)
        
    async def test_thread_management(self):
        
        threads = ["thread_a", "thread_b", "thread_c"]
        
        if self.graph:
            for thread_id in threads:
                config = RunnableConfig(
                    configurable={"thread_id": thread_id}
                )
                async for chunk in self.graph.astream(
                    {"messages": [("user", f"这是线程 {thread_id} 的消息")]},
                    config=config,
                    context=Context(user_id=f"user_{thread_id}", user_name=thread_id)
                ):
                    for output in chunk.values():
                        if isinstance(output, dict) and "messages" in output:
                            print(f"    AI: 已回复")
            
            for thread_id in threads:
                config = RunnableConfig(configurable={"thread_id": thread_id})
                try:
                    state = self.graph.get_state(config)
                    print(f"    线程 {thread_id}: {len(state.values.get('messages', []))} 条消息")
                except Exception as e:
                    print(f"    线程 {thread_id}: 获取失败 ({e})")
                
    async def test_state_operations(self):
        
        thread_id = "test_state_ops"
        config = RunnableConfig(configurable={"thread_id": thread_id})
        
        if self.graph:
            async for chunk in self.graph.astream(
                {"messages": [("user", "你好")]},
                config=config,
                context=Context(user_id="user_test", user_name="TestUser")
            ):
                pass
                
            state = self.graph.get_state(config)
            
            new_config = self.graph.update_state(
                config,
                values={"messages": [("user", "这是手动添加的消息")]},
                as_node="call_model"
            )
            
            state = self.graph.get_state(new_config)
        
    async def cleanup(self):
        if self.checkpointer:
            await self.checkpointer.conn.close()


async def run_demo():
    
    print("=" * 60)
    print("LangGraph 记忆功能 MVP")
    print("=" * 60)
    
    mvp = MemoryMVP()
    
    try:
        await mvp.initialize()
        await mvp.create_graph()
        
        await mvp.test_short_term_memory()
        await mvp.test_long_term_memory()
        await mvp.test_thread_management()
        await mvp.test_state_operations()
        
        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await mvp.cleanup()


def main():
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
