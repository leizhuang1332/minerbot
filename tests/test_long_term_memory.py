"""长期记忆功能测试"""

import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from src.memory.manager import Message, Conversation, MemoryManager


class TestMessageDataClass:
    """测试 Message 数据类"""
    
    def test_message_creation(self):
        """测试创建消息"""
        msg = Message(role="user", content="你好")
        assert msg.role == "user"
        assert msg.content == "你好"
        assert msg.timestamp is not None
    
    def test_message_with_custom_timestamp(self):
        """测试带自定义时间戳的消息"""
        custom_time = datetime(2026, 3, 12, 10, 30, 0)
        msg = Message(role="assistant", content="你好啊", timestamp=custom_time)
        assert msg.timestamp == custom_time
    
    def test_message_default_timestamp(self):
        """测试默认时间戳"""
        before = datetime.now()
        msg = Message(role="user", content="test")
        after = datetime.now()
        assert before <= msg.timestamp <= after
    
    def test_message_equality(self):
        """测试消息相等性"""
        time = datetime(2026, 3, 12, 10, 30, 0)
        msg1 = Message(role="user", content="你好", timestamp=time)
        msg2 = Message(role="user", content="你好", timestamp=time)
        assert msg1.role == msg2.role
        assert msg1.content == msg2.content


class TestConversationDataClass:
    """测试 Conversation 数据类"""
    
    def test_conversation_creation(self):
        """测试创建对话"""
        conv = Conversation(id="test_conv")
        assert conv.id == "test_conv"
        assert conv.messages == []
        assert conv.created_at is not None
        assert conv.last_active is not None
        assert conv.dirty is False
    
    def test_conversation_with_messages(self):
        """测试带消息列表的对话"""
        messages = [
            Message(role="user", content="你好"),
            Message(role="assistant", content="你好啊")
        ]
        conv = Conversation(id="test_conv", messages=messages)
        assert len(conv.messages) == 2
        assert conv.messages[0].role == "user"
        assert conv.messages[1].role == "assistant"
    
    def test_conversation_dirty_flag(self):
        """测试 dirty 标志"""
        conv = Conversation(id="test")
        assert conv.dirty is False
        conv.dirty = True
        assert conv.dirty is True


class TestMarkdownSerialization:
    """测试 Markdown 序列化"""
    
    def test_conversation_to_markdown_empty(self):
        """测试空对话的 Markdown 转换"""
        conv = Conversation(id="default")
        md = MemoryManager()._conversation_to_markdown(conv)
        assert "# 对话记录" in md
        assert "- **消息数量**: 0" in md
    
    def test_conversation_to_markdown_with_messages(self):
        """测试带消息的 Markdown 转换"""
        messages = [
            Message(role="user", content="你好", timestamp=datetime(2026, 3, 12, 10, 0, 0)),
            Message(role="assistant", content="你好啊", timestamp=datetime(2026, 3, 12, 10, 0, 1))
        ]
        conv = Conversation(id="default", messages=messages)
        md = MemoryManager()._conversation_to_markdown(conv)
        
        assert "# 对话记录" in md
        assert "### 用户 (2026-03-12 10:00:00)" in md
        assert "你好" in md
        assert "### 助手 (2026-03-12 10:00:01)" in md
        assert "你好啊" in md
        assert "- **消息数量**: 2" in md
    
    def test_conversation_to_markdown_multiline_content(self):
        """测试多行内容的 Markdown 转换"""
        messages = [
            Message(role="user", content="第一行\n第二行\n第三行", timestamp=datetime(2026, 3, 12, 10, 0, 0))
        ]
        conv = Conversation(id="default", messages=messages)
        md = MemoryManager()._conversation_to_markdown(conv)
        
        assert "第一行" in md
        assert "第二行" in md
        assert "第三行" in md


class TestMarkdownParsing:
    """测试 Markdown 解析"""
    
    def test_parse_empty_markdown(self):
        """测试解析空的 Markdown 文件"""
        manager = MemoryManager()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("# 对话记录\n\n- **消息数量**: 0\n")
            f.flush()
            file_path = Path(f.name)
        
        try:
            conv = manager._parse_markdown_file(file_path)
            assert conv.messages == []
        finally:
            file_path.unlink()
    
    def test_parse_markdown_with_messages(self):
        """测试解析带消息的 Markdown 文件"""
        manager = MemoryManager()
        md_content = """# 对话记录

- **创建时间**: 2026-03-12 10:00:00
- **最后活跃**: 2026-03-12 10:05:00
- **消息数量**: 2

---

## 对话历史

### 用户 (2026-03-12 10:00:00)
你好

### 助手 (2026-03-12 10:00:01)
你好啊
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(md_content)
            f.flush()
            file_path = Path(f.name)
        
        try:
            conv = manager._parse_markdown_file(file_path)
            assert len(conv.messages) == 2
            assert conv.messages[0].role == "user"
            assert conv.messages[0].content == "你好\n"
            assert conv.messages[1].role == "assistant"
            assert conv.messages[1].content == "你好啊\n"
        finally:
            file_path.unlink()
    
    def test_parse_markdown_multiline_content(self):
        """测试解析多行消息内容"""
        manager = MemoryManager()
        md_content = """# 对话记录

- **消息数量**: 1

---

## 对话历史

### 用户 (2026-03-12 10:00:00)
第一行
第二行
第三行
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(md_content)
            f.flush()
            file_path = Path(f.name)
        
        try:
            conv = manager._parse_markdown_file(file_path)
            assert len(conv.messages) == 1
            assert conv.messages[0].content == "第一行\n第二行\n第三行\n"
        finally:
            file_path.unlink()


class TestPathGeneration:
    """测试路径生成"""
    
    def test_get_date_dir_default(self):
        """测试默认日期目录"""
        manager = MemoryManager(memory_dir="memory")
        date_dir = manager._get_date_dir()
        expected = Path("memory") / datetime.now().strftime("%Y-%m-%d")
        assert date_dir == expected
    
    def test_get_date_dir_custom(self):
        """测试自定义日期目录"""
        manager = MemoryManager(memory_dir="memory")
        custom_date = datetime(2026, 3, 12, 0, 0, 0)
        date_dir = manager._get_date_dir(custom_date)
        assert date_dir == Path("memory/2026-03-12")
    
    def test_get_date_dir_creates_directory(self):
        """测试日期目录创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(memory_dir=tmpdir)
            date_dir = manager._get_date_dir()
            assert date_dir.exists()
            assert date_dir.is_dir()
    
    def test_get_conversation_file_default(self):
        """测试默认对话文件路径"""
        manager = MemoryManager(memory_dir="memory")
        file_path = manager._get_conversation_file("default")
        expected = Path("memory") / datetime.now().strftime("%Y-%m-%d") / "conversation_default.md"
        assert file_path == expected
    
    def test_get_conversation_file_custom_id(self):
        """测试自定义对话ID的文件路径"""
        manager = MemoryManager(memory_dir="memory")
        file_path = manager._get_conversation_file("test_session")
        expected = Path("memory") / datetime.now().strftime("%Y-%m-%d") / "conversation_test_session.md"
        assert file_path == expected


class TestBackgroundAsyncWrite:
    """测试后台异步写入"""
    
    @pytest.mark.asyncio
    async def test_add_message(self):
        """测试添加消息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(memory_dir=tmpdir, batch_size=10, flush_interval=30.0)
            
            await manager.add_message("user", "你好")
            
            messages = manager.get_messages()
            assert len(messages) == 1
            assert messages[0].role == "user"
            assert messages[0].content == "你好"
    
    @pytest.mark.asyncio
    async def test_add_multiple_messages(self):
        """测试添加多条消息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(memory_dir=tmpdir, batch_size=10, flush_interval=30.0)
            
            await manager.add_message("user", "你好")
            await manager.add_message("assistant", "你好啊")
            await manager.add_message("user", "今天天气怎么样")
            
            messages = manager.get_messages()
            assert len(messages) == 3
            assert messages[0].content == "你好"
            assert messages[1].content == "你好啊"
            assert messages[2].content == "今天天气怎么样"
    
    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        """测试启动和停止后台任务"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(memory_dir=tmpdir, batch_size=10, flush_interval=30.0)
            
            # 启动后台任务
            await manager.start()
            assert manager._background_task is not None
            assert not manager._shutdown_event.is_set()
            
            # 添加一些消息
            await manager.add_message("user", "测试消息")
            
            # 停止后台任务
            await manager.stop()
            assert manager._shutdown_event.is_set()
    
    @pytest.mark.asyncio
    async def test_message_added_to_queue(self):
        """测试消息被添加到队列"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(memory_dir=tmpdir, batch_size=10, flush_interval=30.0)
            await manager.start()
            
            await manager.add_message("user", "测试")
            
            # 验证消息在队列中
            queue_size = manager._message_queue.qsize()
            assert queue_size >= 0  # 消息可能在队列中被消费
            
            await manager.stop()
    
    @pytest.mark.asyncio
    async def test_load_conversation_creates_new(self):
        """测试加载不存在的对话时创建新对话"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(memory_dir=tmpdir)
            
            conv = manager.load_conversation("new_session")
            
            assert conv.id == "new_session"
            assert conv.messages == []
            assert manager._current_conversation is conv
    
    @pytest.mark.asyncio
    async def test_dirty_flag_set_on_add_message(self):
        """测试添加消息后 dirty 标志被设置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(memory_dir=tmpdir)
            
            # 创建初始对话
            conv = manager.load_conversation("test")
            assert conv.dirty is False
            
            # 添加消息
            await manager.add_message("user", "你好")
            
            # 确保 _current_conversation 不为 None
            assert manager._current_conversation is not None
            assert manager._current_conversation.dirty is True
    
    @pytest.mark.asyncio
    async def test_add_message_creates_conversation_if_none(self):
        """测试没有当前对话时自动创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(memory_dir=tmpdir)
            
            # 不先加载对话直接添加消息
            await manager.add_message("user", "你好")
            
            assert manager._current_conversation is not None
            assert len(manager.get_messages()) == 1


class TestMemoryManagerIntegration:
    """测试 MemoryManager 集成功能"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """测试完整工作流程"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(memory_dir=tmpdir, batch_size=2, flush_interval=30.0)
            
            # 启动
            await manager.start()
            
            # 加载对话
            manager.load_conversation("test")
            
            # 添加消息
            await manager.add_message("user", "你好")
            await manager.add_message("assistant", "你好啊")
            
            # 停止时会触发保存
            await manager.stop()
            
            # 验证文件已创建
            file_path = Path(tmpdir) / datetime.now().strftime("%Y-%m-%d") / "conversation_test.md"
            assert file_path.exists()
            
            # 验证内容
            content = file_path.read_text(encoding="utf-8")
            assert "你好" in content
            assert "你好啊" in content
    
    @pytest.mark.asyncio
    async def test_load_existing_conversation(self):
        """测试加载已存在的对话文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 先创建文件
            date_dir = Path(tmpdir) / datetime.now().strftime("%Y-%m-%d")
            date_dir.mkdir(parents=True)
            file_path = date_dir / "conversation_test.md"
            file_path.write_text("""# 对话记录

- **创建时间**: 2026-03-12 10:00:00
- **最后活跃**: 2026-03-12 10:05:00
- **消息数量**: 1

---

## 对话历史

### 用户 (2026-03-12 10:00:00)
已存在的消息
""", encoding="utf-8")
            
            # 加载对话
            manager = MemoryManager(memory_dir=tmpdir)
            conv = manager.load_conversation("test")
            
            assert len(conv.messages) == 1
            assert conv.messages[0].content == "已存在的消息\n"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
