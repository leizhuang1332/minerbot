"""消息序列化工具模块"""
from datetime import datetime
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

if TYPE_CHECKING:
    from langchain_core.runnables.config import RunnableConfig


def serialize_messages(messages: list[Any]) -> list[dict[str, Any]]:
    """序列化消息列表为字典列表
    
    Args:
        messages: LangChain 消息列表
    
    Returns:
        序列化后的字典列表
    """
    result = []
    for msg in messages:
        msg_dict: dict[str, Any] = {"type": msg.type, "content": msg.content}
        
        if isinstance(msg, HumanMessage):
            msg_dict["type"] = "human"
        elif isinstance(msg, AIMessage):
            msg_dict["type"] = "ai"
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "name": tc.get("name"),
                        "args": tc.get("args", {}),
                        "id": tc.get("id"),
                    }
                    for tc in msg.tool_calls
                ]
        elif isinstance(msg, ToolMessage):
            msg_dict["type"] = "tool"
            msg_dict["tool_call_id"] = msg.tool_call_id
        
        if hasattr(msg, "name") and msg.name:
            msg_dict["name"] = msg.name
        
        if hasattr(msg, "additional_kwargs") and msg.additional_kwargs:
            msg_dict["additional_kwargs"] = msg.additional_kwargs
        
        result.append(msg_dict)
    
    return result


def deserialize_messages(data: list[dict[str, Any]]) -> list[Any]:
    """反序列化字典列表为消息列表
    
    Args:
        data: 序列化后的字典列表
    
    Returns:
        LangChain 消息列表
    """
    messages = []
    for msg_dict in data:
        msg_type = msg_dict.get("type", "")
        content = msg_dict.get("content", "")
        
        if msg_type == "human":
            msg = HumanMessage(content=content)
        elif msg_type == "ai":
            tool_calls = msg_dict.get("tool_calls")
            additional_kwargs = msg_dict.get("additional_kwargs", {})
            
            kwargs: dict[str, Any] = {
                "content": content,
            }
            
            if tool_calls:
                kwargs["tool_calls"] = tool_calls
            
            if additional_kwargs:
                kwargs["additional_kwargs"] = additional_kwargs
            
            msg = AIMessage(**kwargs)
        elif msg_type == "tool":
            tool_call_id = msg_dict.get("tool_call_id", "")
            msg = ToolMessage(content=content, tool_call_id=tool_call_id)
        else:
            msg = HumanMessage(content=content)
        
        if "name" in msg_dict:
            msg.name = msg_dict["name"]
        
        messages.append(msg)
    
    return messages


def get_thread_message_count(checkpointer: Any, thread_id: str) -> int:
    """获取线程的消息数量
    
    Args:
        checkpointer: LangGraph checkpointer 实例
        thread_id: 线程 ID
    
    Returns:
        消息数量
    """
    if checkpointer is None:
        return 0
    
    try:
        config: "RunnableConfig" = {"configurable": {"thread_id": thread_id}}
        checkpoint = checkpointer.get(config)
        if checkpoint is None:
            return 0
        
        if hasattr(checkpoint, "channel_values"):
            channels = checkpoint.channel_values
            if "messages" in channels:
                messages = channels["messages"]
                if isinstance(messages, list):
                    return len(messages)
        
        return 0
    except Exception:
        return 0


def get_thread_last_activity(
    checkpointer: Any,
    thread_id: str
) -> datetime | None:
    """获取线程的最后活动时间
    
    Args:
        checkpointer: LangGraph checkpointer 实例
        thread_id: 线程 ID
    
    Returns:
        最后活动时间，如果不存在则返回 None
    """
    if checkpointer is None:
        return None
    
    try:
        config: "RunnableConfig" = {"configurable": {"thread_id": thread_id}}
        
        if hasattr(checkpointer, "get"):
            checkpoint = checkpointer.get(config)
            if checkpoint is None:
                return None
            
            if hasattr(checkpoint, "ts"):
                ts = checkpoint.ts
                if ts:
                    return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            
            if hasattr(checkpoint, "metadata"):
                metadata = checkpoint.metadata
                if metadata and "ts" in metadata:
                    ts = metadata["ts"]
                    if ts:
                        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        
        return None
    except Exception:
        return None
