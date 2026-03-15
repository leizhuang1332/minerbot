"""会话摘要模块"""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from minerbot.types import SessionSummary

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = """你是一个会话摘要专家。请分析以下对话内容，生成结构化的摘要。

## 要求
1. 识别会话的主要话题(topic)
2. 提取关键要点(key_points)，最多5条
3. 记录达成的决定(decisions)，最多5条
4. 列出需要执行的操作项(action_items)，最多5条

## 输出格式
请以JSON格式输出，包含以下字段：
- topic: string - 会话的主要话题
- key_points: array[string] - 关键要点列表
- decisions: array[string] - 达成的决定列表
- action_items: array[string] - 需要执行的操作项列表

## 对话内容
{messages}

请直接输出JSON，不要包含其他内容。"""


class SessionSummarizer:
    """会话摘要生成器"""
    
    def __init__(self, model: ChatAnthropic) -> None:
        self._model: ChatAnthropic = model
        self._logger: logging.Logger = logging.getLogger(__name__)
    
    def _format_messages(self, messages: list[dict[str, Any]]) -> str:
        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")
        return "\n\n".join(formatted)
    
    def _create_summary_prompt(self, messages: list[dict[str, Any]]) -> list[SystemMessage | HumanMessage]:
        formatted_messages = self._format_messages(messages)
        prompt = SUMMARIZE_PROMPT.format(messages=formatted_messages)
        
        return [
            SystemMessage(content="你是一个专业的会话摘要助手，负责提取对话的关键信息。"),
            HumanMessage(content=prompt)
        ]
    
    async def summarize(
        self,
        messages: list[dict[str, Any]],
        thread_id: str
    ) -> SessionSummary:
        if not messages:
            raise ValueError("消息列表不能为空")
        
        prompt_messages = self._create_summary_prompt(messages)
        
        try:
            response = await self._model.ainvoke(prompt_messages)
            
            raw_content = response.content
            
            if isinstance(raw_content, str):
                content = raw_content
            elif isinstance(raw_content, list):
                text_parts = []
                for item in raw_content:
                    if isinstance(item, str):
                        text_parts.append(item)
                    elif isinstance(item, dict):
                        text_parts.append(str(item.get("text", "")))
                content = "".join(text_parts)
            else:
                content = str(raw_content)
            
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            try:
                summary_data = json.loads(content)
            except json.JSONDecodeError as e:
                self._logger.warning(f"JSON 解析失败，尝试提取: {e}")
                summary_data = self._extract_json_from_response(content)
            
            now = datetime.now(timezone.utc).isoformat()
            
            return SessionSummary(
                thread_id=thread_id,
                topic=summary_data.get("topic", "未识别的话题"),
                key_points=summary_data.get("key_points", []),
                decisions=summary_data.get("decisions", []),
                action_items=summary_data.get("action_items", []),
                created_at=now
            )
            
        except Exception as e:
            self._logger.error(f"生成摘要失败: {e}")
            raise RuntimeError(f"生成摘要失败: {e}") from e
    
    def _extract_json_from_response(self, content: str) -> dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        return {
            "topic": "无法解析的话题",
            "key_points": [],
            "decisions": [],
            "action_items": []
        }
