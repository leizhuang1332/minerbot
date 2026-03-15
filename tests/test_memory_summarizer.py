"""会话摘要器测试"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from minerbot.memory.summarizer import SessionSummarizer


class TestSessionSummarizer:

    def test_init(self):
        mock_model = MagicMock()
        
        summarizer = SessionSummarizer(mock_model)
        
        assert summarizer._model is not None
        assert summarizer._logger is not None

    @pytest.mark.asyncio
    @patch('minerbot.memory.summarizer.SessionSummary')
    async def test_summarize_success(self, mock_summary_class):
        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock()
        
        mock_model.ainvoke.return_value = MagicMock(
            content='{"topic": "项目讨论", "key_points": ["功能A", "功能B"], "decisions": [], "action_items": ["完成开发"]}'
        )
        
        mock_summary_instance = MagicMock()
        mock_summary_class.return_value = mock_summary_instance
        
        summarizer = SessionSummarizer(mock_model)
        
        messages = [
            {"role": "user", "content": "我们讨论一下项目A"},
            {"role": "assistant", "content": "好的，请说"}
        ]
        
        result = await summarizer.summarize(messages, thread_id="thread123")
        
        assert result is not None
        mock_model.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_empty_messages(self):
        mock_model = MagicMock()
        summarizer = SessionSummarizer(mock_model)
        
        with pytest.raises(ValueError):
            await summarizer.summarize([], thread_id="thread123")

    @pytest.mark.asyncio
    @patch('minerbot.memory.summarizer.SessionSummary')
    async def test_summarize_with_json_code_block(self, mock_summary_class):
        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock()
        
        mock_model.ainvoke.return_value = MagicMock(
            content='```json\n{"topic": "会议总结", "key_points": ["要点1"], "decisions": ["决定1"], "action_items": []}\n```'
        )
        
        mock_summary_instance = MagicMock()
        mock_summary_class.return_value = mock_summary_instance
        
        summarizer = SessionSummarizer(mock_model)
        
        messages = [{"role": "user", "content": "总结这次会议"}]
        
        result = await summarizer.summarize(messages, thread_id="thread456")
        
        assert result is not None

    @pytest.mark.asyncio
    @patch('minerbot.memory.summarizer.SessionSummary')
    async def test_summarize_invalid_json(self, mock_summary_class):
        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock()
        
        mock_model.ainvoke.return_value = MagicMock(
            content='这是无效的JSON响应'
        )
        
        mock_summary_instance = MagicMock()
        mock_summary_class.return_value = mock_summary_instance
        
        summarizer = SessionSummarizer(mock_model)
        
        messages = [{"role": "user", "content": "测试"}]
        
        result = await summarizer.summarize(messages, thread_id="thread789")
        
        assert result is not None

    @pytest.mark.asyncio
    @patch('minerbot.memory.summarizer.SessionSummary')
    async def test_summarize_model_exception(self, mock_summary_class):
        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock()
        
        mock_model.ainvoke.side_effect = Exception("API Error")
        
        summarizer = SessionSummarizer(mock_model)
        
        messages = [{"role": "user", "content": "测试消息"}]
        
        with pytest.raises(RuntimeError):
            await summarizer.summarize(messages, thread_id="thread000")
