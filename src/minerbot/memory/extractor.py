"""记忆实体提取器模块

使用 LLM 从消息中提取实体信息。
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from pydantic import BaseModel, Field

from minerbot.types import EntityType, MemoryEntity

logger = logging.getLogger(__name__)


class ExtractedEntity(BaseModel):
    """LLM 提取的实体结构"""
    entity_type: str = Field(description="实体类型: person, location, event, relationship, context")
    name: str = Field(description="实体名称")
    description: str = Field(description="实体描述")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class ExtractionResult(BaseModel):
    """实体提取结果"""
    entities: list[ExtractedEntity] = Field(default_factory=list, description="提取的实体列表")


ENTITY_EXTRACTION_SCHEMA = {
    "title": "EntityExtraction",
    "description": "从对话消息中提取的实体列表",
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "description": "提取的实体列表",
            "items": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "实体类型: person, location, event, relationship, context",
                        "enum": ["person", "location", "event", "relationship", "context"]
                    },
                    "name": {
                        "type": "string",
                        "description": "实体名称"
                    },
                    "description": {
                        "type": "string",
                        "description": "实体描述"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "额外元数据",
                        "additionalProperties": True
                    }
                },
                "required": ["entity_type", "name", "description"]
            }
        }
    },
    "required": ["entities"]
}


EXTRACTION_PROMPT_TEMPLATE = """你是一个实体提取专家。从以下对话消息中提取有价值的实体信息。

实体类型说明：
- person: 人物，包括用户、提及的其他人等
- location: 地点，包括城市、国家、地址等
- event: 事件，包括会议、约定、节日等
- relationship: 关系，包括人际关系、工作关系等
- context: 上下文，包括话题、主题、项目等

提取要求：
1. 只提取明确提到的实体，不要推测
2. 每个实体需要有名称和描述
3. 从用户消息中提取与用户相关的实体
4. 关系类型要说明涉及哪些实体

用户ID: {user_id}

对话消息:
{messages}

请提取所有相关的实体信息，以JSON格式输出。
"""


class EntityExtractor:
    """记忆实体提取器
    
    使用 LLM 从对话消息中提取实体信息。
    """
    
    def __init__(self, model: ChatAnthropic):
        """初始化实体提取器
        
        Args:
            model: ChatAnthropic 模型实例
        """
        self._model: ChatAnthropic = model
        self._structured_model = model.with_structured_output(
            ExtractionResult,
            method="json_schema"
        )
        logger.info("EntityExtractor 初始化完成")
    
    def _serialize_messages(self, messages: list[AnyMessage]) -> str:
        """将消息序列化为字符串
        
        Args:
            messages: LangChain 消息列表
            
        Returns:
            格式化的消息字符串
        """
        lines: list[str] = []
        
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "用户"
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
            elif isinstance(msg, AIMessage):
                role = "助手"
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
            else:
                role = type(msg).__name__
                content = str(msg.content)
            
            lines.append(f"{role}: {content}")
        
        return "\n\n".join(lines)
    
    def _convert_to_memory_entity(self, extracted: ExtractedEntity, user_id: str) -> MemoryEntity:
        """将提取的实体转换为 MemoryEntity
        
        Args:
            extracted: 提取的实体
            user_id: 用户ID
            
        Returns:
            MemoryEntity 实例
        """
        try:
            entity_type = EntityType(extracted.entity_type)
        except ValueError:
            entity_type = EntityType.CONTEXT
        
        return MemoryEntity(
            id=str(uuid.uuid4()),
            entity_type=entity_type,
            name=extracted.name,
            description=extracted.description,
            metadata={
                "user_id": user_id,
                **extracted.metadata
            },
            created_at=datetime.now(timezone.utc).isoformat()
        )
    
    async def extract(self, messages: list[AnyMessage], user_id: str) -> list[MemoryEntity]:
        """从消息中提取实体
        
        Args:
            messages: LangChain 消息列表 (HumanMessage, AIMessage 等)
            user_id: 用户ID
            
        Returns:
            提取的实体列表
        """
        if not messages:
            logger.warning("没有消息可供提取")
            return []
        
        serialized = self._serialize_messages(messages)
        
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            user_id=user_id,
            messages=serialized
        )
        
        logger.debug(f"开始提取实体，用户ID: {user_id}")
        
        try:
            raw_result = await asyncio.to_thread(
                self._structured_model.invoke,
                prompt
            )
            result = ExtractionResult.model_validate(raw_result)
            
            entities: list[MemoryEntity] = [
                self._convert_to_memory_entity(extracted, user_id)
                for extracted in result.entities
            ]
            
            logger.info(f"成功提取 {len(entities)} 个实体")
            return entities
            
        except Exception as e:
            logger.error(f"实体提取失败: {e}")
            return []
    
    async def extract_single(self, message: AnyMessage, user_id: str) -> list[MemoryEntity]:
        """从单条消息中提取实体
        
        Args:
            message: LangChain 消息
            user_id: 用户ID
            
        Returns:
            提取的实体列表
        """
        return await self.extract([message], user_id)
