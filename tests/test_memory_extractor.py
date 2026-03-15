"""记忆实体提取器测试"""
import pytest
from unittest.mock import MagicMock, patch
from typing import cast

from langchain_core.messages import HumanMessage, AIMessage, AnyMessage

from minerbot.memory.extractor import EntityExtractor, ExtractedEntity


class TestEntityExtractor:

    def test_init(self):
        mock_model = MagicMock()
        
        extractor = EntityExtractor(mock_model)
        
        assert extractor._model is not None
        assert extractor._structured_model is not None
        mock_model.with_structured_output.assert_called_once()

    @pytest.mark.asyncio
    @patch('minerbot.memory.extractor.ExtractionResult')
    @patch('minerbot.memory.extractor.asyncio.to_thread')
    async def test_extract_with_entities(self, mock_to_thread, mock_result_model):
        mock_model = MagicMock()
        mock_structured_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured_model

        mock_extracted_entities = [
            ExtractedEntity(
                entity_type="person",
                name="张三",
                description="用户提到的朋友",
                metadata={"age": 30}
            ),
            ExtractedEntity(
                entity_type="context",
                name="项目开发",
                description="当前正在进行的工作项目",
                metadata={}
            )
        ]
        
        mock_result_instance = MagicMock()
        mock_result_instance.entities = mock_extracted_entities
        mock_result_model.model_validate.return_value = mock_result_instance
        
        mock_to_thread.return_value = mock_result_instance

        extractor = EntityExtractor(mock_model)
        
        messages = [
            HumanMessage(content="我的朋友张三在做项目开发"),
            AIMessage(content="听起来很有趣")
        ]
        
        result = await extractor.extract(cast(list[AnyMessage], messages), user_id="user123")
        
        assert len(result) == 2
        assert result[0].name == "张三"
        assert result[0].entity_type.value == "person"
        assert result[1].name == "项目开发"
        assert result[1].entity_type.value == "context"

    @pytest.mark.asyncio
    @patch('minerbot.memory.extractor.asyncio.to_thread')
    async def test_extract_empty_messages(self, mock_to_thread):
        mock_model = MagicMock()
        extractor = EntityExtractor(mock_model)
        
        result = await extractor.extract([], user_id="user123")
        
        assert result == []
        mock_to_thread.assert_not_called()

    @pytest.mark.asyncio
    @patch('minerbot.memory.extractor.asyncio.to_thread')
    async def test_extract_exception_handling(self, mock_to_thread):
        mock_model = MagicMock()
        mock_structured_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured_model
        
        mock_to_thread.side_effect = Exception("API Error")
        
        extractor = EntityExtractor(mock_model)
        
        messages = [HumanMessage(content="测试消息")]
        result = await extractor.extract(cast(list[AnyMessage], messages), user_id="user123")
        
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_single(self):
        mock_model = MagicMock()
        mock_structured_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured_model
        
        with patch('minerbot.memory.extractor.asyncio.to_thread') as mock_to_thread:
            mock_result_instance = MagicMock()
            mock_result_instance.entities = []
            
            mock_to_thread.return_value = mock_result_instance
            
            extractor = EntityExtractor(mock_model)
            
            message = HumanMessage(content="单条消息测试")
            result = await extractor.extract_single(message, user_id="user123")
            
            assert result == []
