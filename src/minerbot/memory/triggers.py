"""记忆触发器模块

检测触发条件并触发记忆提取。
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from minerbot.config import AppConfig


class TriggerType(Enum):
    """触发类型"""
    SESSION_END = "session_end"
    MESSAGE_COUNT = "message_count"
    IDLE_TIMEOUT = "idle_timeout"


# 结束命令关键词
SESSION_END_KEYWORDS = {"quit", "exit", "结束", "q", "再见", "bye"}


@dataclass
class TriggerResult:
    """触发结果"""
    should_trigger: bool
    trigger_type: Optional[TriggerType] = None
    reason: str = ""


@dataclass
class ThreadState:
    """线程状态"""
    thread_id: str
    message_count: int = 0
    last_activity_time: datetime = field(default_factory=datetime.now)
    is_active: bool = True


class TriggerManager:
    """触发管理器
    
    检测各种触发条件并在满足条件时返回触发结果。
    支持三种触发类型：
    - SESSION_END: 用户发送结束命令
    - MESSAGE_COUNT: 消息数达到阈值
    - IDLE_TIMEOUT: 空闲超时
    """
    
    def __init__(self, config: AppConfig):
        """初始化触发管理器
        
        Args:
            config: 应用配置
        """
        self._config: AppConfig = config
        self._thread_states: dict[str, ThreadState] = {}
        self._idle_check_task: asyncio.Task[None] | None = None
        self._check_interval: int = 30
    
    @property
    def message_count_threshold(self) -> int:
        """消息数触发阈值"""
        return self._config.memory_trigger_message_count
    
    @property
    def idle_timeout_minutes(self) -> int:
        """空闲超时时间（分钟）"""
        return self._config.memory_trigger_idle_minutes
    
    def _get_or_create_thread_state(self, thread_id: str) -> ThreadState:
        """获取或创建线程状态"""
        if thread_id not in self._thread_states:
            self._thread_states[thread_id] = ThreadState(thread_id=thread_id)
        return self._thread_states[thread_id]
    
    def _check_session_end(self, session_state: dict[str, Any]) -> TriggerResult | None:
        """检查是否触发会话结束
        
        Args:
            session_state: 会话状态
            
        Returns:
            触发结果，如果不应触发则返回 None
        """
        last_message = session_state.get("last_message", "").strip().lower()
        
        # 检查是否匹配结束命令关键词
        for keyword in SESSION_END_KEYWORDS:
            if last_message == keyword or last_message.startswith(keyword + " "):
                return TriggerResult(
                    should_trigger=True,
                    trigger_type=TriggerType.SESSION_END,
                    reason=f"用户发送结束命令: {keyword}"
                )
        
        return None
    
    def _check_message_count(self, thread_state: ThreadState) -> TriggerResult | None:
        """检查是否触发消息数阈值
        
        Args:
            thread_state: 线程状态
            
        Returns:
            触发结果，如果不应触发则返回 None
        """
        if thread_state.message_count >= self.message_count_threshold:
            return TriggerResult(
                should_trigger=True,
                trigger_type=TriggerType.MESSAGE_COUNT,
                reason=f"消息数达到阈值 ({thread_state.message_count}/{self.message_count_threshold})"
            )
        
        return None
    
    def _check_idle_timeout(self, thread_state: ThreadState) -> TriggerResult | None:
        """检查是否触发空闲超时
        
        Args:
            thread_state: 线程状态
            
        Returns:
            触发结果，如果不应触发则返回 None
        """
        if not thread_state.is_active:
            return None
        
        idle_time = datetime.now() - thread_state.last_activity_time
        idle_minutes = idle_time.total_seconds() / 60
        
        if idle_minutes >= self.idle_timeout_minutes:
            return TriggerResult(
                should_trigger=True,
                trigger_type=TriggerType.IDLE_TIMEOUT,
                reason=f"空闲超时 ({idle_minutes:.1f}分钟 >= {self.idle_timeout_minutes}分钟)"
            )
        
        return None
    
    async def check_and_trigger(self, thread_id: str, session_state: dict[str, Any]) -> TriggerResult:
        """检查并触发
        
        检查所有触发条件，按优先级返回第一个满足的条件：
        1. SESSION_END (用户结束命令)
        2. MESSAGE_COUNT (消息数达到阈值)
        3. IDLE_TIMEOUT (空闲超时)
        
        Args:
            thread_id: 线程 ID
            session_state: 会话状态字典，包含:
                - last_message: 最后一条用户消息
                - message_count: 消息数（可选）
                
        Returns:
            触发结果
        """
        # 获取或创建线程状态
        thread_state = self._get_or_create_thread_state(thread_id)
        
        # 更新消息数
        if "message_count" in session_state:
            thread_state.message_count = session_state["message_count"]
        else:
            thread_state.message_count += 1
        
        # 更新最后活动时间
        thread_state.last_activity_time = datetime.now()
        
        # 检查会话结束
        session_end_result = self._check_session_end(session_state)
        if session_end_result and session_end_result.should_trigger:
            thread_state.is_active = False
            return session_end_result
        
        # 检查消息数阈值
        message_count_result = self._check_message_count(thread_state)
        if message_count_result and message_count_result.should_trigger:
            return message_count_result
        
        # 检查空闲超时
        idle_result = self._check_idle_timeout(thread_state)
        if idle_result and idle_result.should_trigger:
            thread_state.is_active = False
            return idle_result
        
        # 无触发条件
        return TriggerResult(
            should_trigger=False,
            reason="未满足任何触发条件"
        )
    
    def update_thread_state(self, thread_id: str, **kwargs: int | bool) -> None:
        """更新线程状态
        
        Args:
            thread_id: 线程 ID
            **kwargs: 要更新的字段 (message_count, is_active)
        """
        thread_state = self._get_or_create_thread_state(thread_id)
        
        if "message_count" in kwargs:
            thread_state.message_count = kwargs["message_count"]
        if "is_active" in kwargs:
            thread_state.is_active = bool(kwargs["is_active"])
        
        # 更新最后活动时间
        thread_state.last_activity_time = datetime.now()
    
    def reset_thread_state(self, thread_id: str) -> None:
        """重置线程状态
        
        Args:
            thread_id: 线程 ID
        """
        if thread_id in self._thread_states:
            self._thread_states[thread_id].message_count = 0
            self._thread_states[thread_id].last_activity_time = datetime.now()
            self._thread_states[thread_id].is_active = True
    
    def get_thread_state(self, thread_id: str) -> ThreadState | None:
        """获取线程状态
        
        Args:
            thread_id: 线程 ID
            
        Returns:
            线程状态，如果不存在则返回 None
        """
        return self._thread_states.get(thread_id)
    
    async def start_idle_monitor(self) -> None:
        """启动空闲监控任务
        
        使用 asyncio 定期检查所有活跃线程的空闲超时。
        """
        if self._idle_check_task is not None:
            return
        
        async def _idle_check_loop():
            while True:
                await asyncio.sleep(self._check_interval)
                
                now = datetime.now()
                for _, state in self._thread_states.items():
                    if not state.is_active:
                        continue
                    
                    idle_time = now - state.last_activity_time
                    idle_minutes = idle_time.total_seconds() / 60
                    
                    if idle_minutes >= self.idle_timeout_minutes:
                        state.is_active = False
        
        self._idle_check_task = asyncio.create_task(_idle_check_loop())
    
    async def stop_idle_monitor(self) -> None:
        """停止空闲监控任务"""
        if self._idle_check_task is not None:
            _: bool = self._idle_check_task.cancel()
            try:
                await self._idle_check_task
            except asyncio.CancelledError:
                pass
            self._idle_check_task = None
    
    def set_message_count_threshold(self, threshold: int) -> None:
        """动态设置消息数阈值
        
        Args:
            threshold: 新的阈值
        """
        self._config.memory_trigger_message_count = max(1, threshold)
    
    def set_idle_timeout_minutes(self, minutes: int) -> None:
        """动态设置空闲超时时间
        
        Args:
            minutes: 新的超时时间（分钟）
        """
        self._config.memory_trigger_idle_minutes = max(1, minutes)
