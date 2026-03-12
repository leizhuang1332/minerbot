"""Memory Manager Module

提供长期记忆管理功能，包括消息存储和会话持久化。
"""
import asyncio
import atexit

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class Message:
    """单条消息
    
    Attributes:
        role: 消息角色 ("user" | "assistant")
        content: 消息内容
        timestamp: 消息时间戳
    """
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass 
class Conversation:
    """对话对象
    
    Attributes:
        id: 对话唯一标识
        messages: 消息列表
        created_at: 创建时间
        last_active: 最后活跃时间
        dirty: 是否有未保存的修改
    """
    id: str
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    dirty: bool = False  # 是否有未保存的修改


class MemoryManager:
    """长期记忆管理器
    
    采用后台异步 + 批量写入策略：
    1. 消息先添加到内存缓冲区
    2. 达到批量阈值或定时触发时写入文件
    3. 程序退出时强制保存
    
    Attributes:
        memory_dir: 记忆存储根目录
        batch_size: 批量写入阈值
        flush_interval: 定时刷新间隔（秒）
    """
    
    def __init__(
        self, 
        memory_dir: str = "memory",
        batch_size: int = 10,        # 批量写入阈值
        flush_interval: float = 30.0  # 定时刷新间隔（秒）
    ):
        """初始化
        
        Args:
            memory_dir: 记忆存储根目录
            batch_size: 达到此数量的消息后触发写入
            flush_interval: 定时写入间隔（秒）
        """
        self._memory_dir = Path(memory_dir)
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        
        # 后台异步写入相关
        self._message_queue: asyncio.Queue[Message] = asyncio.Queue()
        self._background_task: Optional[asyncio.Task[None]] = None
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._current_conversation: Optional[Conversation] = None
        
        # 注册退出时的同步刷新
        atexit.register(self._sync_flush_on_exit)
    
    # ========== 后台写入控制 ==========
    
    async def start(self) -> None:
        """启动后台写入任务"""
        self._shutdown_event.clear()
        self._background_task = asyncio.create_task(self._background_writer())
    
    async def stop(self) -> None:
        """停止后台任务并保存所有数据"""
        self._shutdown_event.set()
        
        if self._background_task:
            # 先保存当前数据
            await self._flush_to_file()
            # 等待后台任务结束
            await self._background_task
    
    def _sync_flush_on_exit(self) -> None:
        """同步刷新（退出时调用）"""
        # 同步版本的保存逻辑
        if self._current_conversation and self._current_conversation.dirty:
            try:
                self._save_to_file_sync()
            except Exception as e:
                print(f"退出时保存记忆失败: {e}")
    
    # ========== 核心方法 ==========
    
    def load_conversation(self, conversation_id: str = "default") -> Conversation:
        """加载对话历史"""
        file_path = self._get_conversation_file(conversation_id)
        
        if not file_path.exists():
            conversation = Conversation(id=conversation_id)
            self._current_conversation = conversation
            return conversation
        
        conversation = self._parse_markdown_file(file_path)
        conversation.id = conversation_id
        self._current_conversation = conversation
        return conversation
    
    async def add_message(self, role: str, content: str) -> None:
        """添加消息（异步，不阻塞）"""
        if self._current_conversation is None:
            self._current_conversation = Conversation(id="default")
        
        message = Message(role=role, content=content)
        self._current_conversation.messages.append(message)
        self._current_conversation.last_active = datetime.now()
        self._current_conversation.dirty = True
        
        # 不直接写入文件，而是添加到队列
        await self._message_queue.put(message)
    
    def get_messages(self) -> List[Message]:
        """获取当前对话的所有消息"""
        if self._current_conversation is None:
            return []
        return self._current_conversation.messages
    
    # ========== 后台写入逻辑 ==========
    
    async def _background_writer(self) -> None:
        """后台写入协程"""
        last_flush_time = datetime.now()
        pending_messages: List[Message] = []
        
        while not self._shutdown_event.is_set():
            try:
                # 等待新消息，有超时
                try:
                    message = await asyncio.wait_for(
                        self._message_queue.get(),
                        timeout=1.0
                    )
                    pending_messages.append(message)
                except asyncio.TimeoutError:
                    pass
                
                # 检查是否需要写入
                now = datetime.now()
                time_since_flush = (now - last_flush_time).total_seconds()
                
                # 达到批量阈值 或 达到定时间隔
                if (len(pending_messages) >= self._batch_size or 
                    time_since_flush >= self._flush_interval):
                    
                    if pending_messages:
                        await self._flush_to_file()
                        pending_messages = []
                        last_flush_time = now
                        
            except Exception as e:
                print(f"后台写入错误: {e}")
                await asyncio.sleep(1)
        
        # 关闭前最后的保存
        if pending_messages:
            await self._flush_to_file()
    
    async def _flush_to_file(self) -> None:
        """将内存数据刷新到文件"""
        if self._current_conversation is None:
            return
            
        if not self._current_conversation.dirty:
            return
        
        # 在线程池中执行文件 IO，避免阻塞事件循环
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_to_file_sync)
        
        self._current_conversation.dirty = False
    
    def _save_to_file_sync(self) -> None:
        """同步保存到文件"""
        if self._current_conversation is None:
            return
            
        file_path = self._get_conversation_file(self._current_conversation.id)
        markdown_content = self._conversation_to_markdown(self._current_conversation)
        file_path.write_text(markdown_content, encoding="utf-8")
    
    # ========== 辅助方法 ==========
    
    def _get_date_dir(self, date: Optional[datetime] = None) -> Path:
        """获取日期目录"""
        date = date or datetime.now()
        date_dir = self._memory_dir / date.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir
    
    def _get_conversation_file(self, conversation_id: str = "default") -> Path:
        """获取对话文件路径"""
        date_dir = self._get_date_dir()
        return date_dir / f"conversation_{conversation_id}.md"
    
    def _parse_markdown_file(self, file_path: Path) -> Conversation:
        """解析 Markdown 文件"""
        content = file_path.read_text(encoding="utf-8")
        messages = []
        
        lines = content.split("\n")
        current_role = None
        current_content = []
        current_time = None
        
        for line in lines:
            line = line.rstrip()
            
            if line.startswith("### 用户 ") or line.startswith("### 助手 "):
                if current_role and current_content:
                    messages.append(Message(
                        role=current_role,
                        content="\n".join(current_content),
                        timestamp=current_time or datetime.now()
                    ))
                
                if "用户" in line:
                    current_role = "user"
                else:
                    current_role = "assistant"
                
                try:
                    time_str = line.split("(")[1].split(")")[0]
                    current_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                except:
                    current_time = datetime.now()
                
                current_content = []
            elif current_role:
                current_content.append(line)
        
        if current_role and current_content:
            messages.append(Message(
                role=current_role,
                content="\n".join(current_content),
                timestamp=current_time or datetime.now()
            ))
        
        return Conversation(
            id="default",
            messages=messages
        )
    
    def _conversation_to_markdown(self, conversation: Conversation) -> str:
        """将 Conversation 对象转换为 Markdown 格式"""
        lines = ["# 对话记录", ""]
        
        lines.append(f"- **创建时间**: {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **最后活跃**: {conversation.last_active.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **消息数量**: {len(conversation.messages)}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 对话历史")
        lines.append("")
        
        for msg in conversation.messages:
            role_label = "用户" if msg.role == "user" else "助手"
            lines.append(f"### {role_label} ({msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
            lines.append("")
            lines.append(msg.content)
            lines.append("")
        
        return "\n".join(lines)
