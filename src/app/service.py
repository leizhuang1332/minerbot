"""Service 模块 - 应用服务生命周期管理"""

import asyncio
import signal
import sys
from typing import Any, Callable, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

from src.app.config import Config
from src.agents import get_agent as get_agent_func
from src.llms import get_llm as get_llm_func


def extract_stream_text(token) -> str:
    """从流式响应中提取文本
    
    处理 MiniMax 模型的 thinking + text 结构。
    
    Args:
        token: AIMessage token 对象
        
    Returns:
        提取的文本内容
    """
    if hasattr(token, 'content') and isinstance(token.content, list):
        texts = []
        for item in token.content:
            if isinstance(item, dict):
                if 'text' in item:
                    texts.append(item['text'])
        return ''.join(texts)
    elif hasattr(token, 'content') and token.content:
        return str(token.content)
    elif hasattr(token, 'text') and token.text:
        return str(token.text)
    return ''


class Service:
    """应用服务类
    
    管理 LLM 和 Agent 的生命周期，提供优雅的启动和停止机制。
    
    Example:
        config = Config.load()
        service = Service(config)
        
        await service.start()
        # ... 使用 service.run() 处理请求 ...
        await service.stop()
    """
    
    def __init__(self, config: Config) -> None:
        """初始化服务
        
        Args:
            config: 应用配置实例
        """
        self._config: Config = config
        self._llm: BaseChatModel | None = None
        self._agent: Any = None
        self._running: bool = False
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._signal_received: signal.Signals | None = None
        
        # 从配置获取超时设置
        service_cfg = config.service_config
        self._timeout: float = service_cfg.get("timeout", 60.0)
        
        # 初始化内存管理器
        self._memory_manager = self._init_memory_manager()
        
        # 设置信号处理
        self._setup_signal_handlers()
    
    def _init_memory_manager(self) -> Optional[Any]:
        """初始化内存管理器
        
        Returns:
            内存管理器实例
        """
        # 默认返回 None，如果没有配置内存管理器
        # 可以根据需要扩展为实际的内存管理器
        return None
    
    def _setup_signal_handlers(self) -> None:
        """设置系统信号处理器"""
        if sys.platform != "win32":
            # Unix-like 系统
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None
            
            if loop:
                for sig in (signal.SIGINT, signal.SIGTERM):
                    try:
                        loop.add_signal_handler(
                            sig,
                            lambda s=sig: asyncio.create_task(self._handle_signal(s))
                        )
                    except NotImplementedError:
                        # 某些平台不支持 add_signal_handler
                        pass
    
    async def _handle_signal(self, sig: signal.Signals) -> None:
        """处理系统信号
        
        Args:
            sig: 收到的信号
        """
        self._signal_received = sig
        print(f"\n收到信号 {sig.name}，正在优雅关闭...")
        await self.stop()
    
    @property
    def is_running(self) -> bool:
        """检查服务是否正在运行
        
        Returns:
            是否正在运行
        """
        return self._running
    
    @property
    def llm(self) -> BaseChatModel | None:
        """获取 LLM 实例
        
        Returns:
            LLM 实例
        """
        return self._llm
    
    @property
    def agent(self) -> Any:
        """获取 Agent 实例
        
        Returns:
            Agent 实例
        """
        return self._agent
    
    async def start(self) -> None:
        """启动服务
        
        初始化 LLM 和 Agent 实例。
        
        Raises:
            RuntimeError: 如果服务已经在运行
        """
        if self._running:
            raise RuntimeError("服务已经在运行")
        
        print("正在启动服务...")
        
        try:
            # 初始化 LLM
            print("正在初始化 LLM...")
            self._llm = get_llm_func()
            print(f"LLM 初始化完成: {type(self._llm).__name__}")
            
            # 初始化 Agent
            print("正在初始化 Agent...")
            agent_config = self._config.agent_config
            self._agent = get_agent_func(
                llm=self._llm,
                system_prompt=agent_config.get("system_prompt", "你是一个助手"),
            )
            print(f"Agent 初始化完成: {type(self._agent).__name__}")
            
            self._running = True
            self._shutdown_event.clear()
            print("服务启动成功")
            
        except Exception as e:
            print(f"服务启动失败: {e}")
            # 确保清理已初始化的资源
            await self._cleanup_resources()
            raise
    
    async def run(self, input_data: Any, timeout: float | None = None) -> Any:
        """运行 LLM 处理请求
        
        Args:
            input_data: 输入数据（字符串）
            timeout: 超时时间（秒），默认为配置中的超时时间
            
        Returns:
            LLM 的处理结果
            
        Raises:
            asyncio.TimeoutError: 请求超时
            RuntimeError: 服务未运行
        """
        if not self._running:
            raise RuntimeError("服务未运行，请先调用 start()")
        
        timeout = timeout or self._timeout
        
        try:
            async with asyncio.timeout(timeout):
                if isinstance(input_data, str):
                    # 添加用户消息到长期记忆
                    if self._memory_manager is not None:
                        await self._memory_manager.add_message("user", input_data)  # type: ignore[union-attr]
                    
                    # 构建完整的消息列表（历史消息 + 当前输入）
                    all_messages = self._build_messages_with_history()
                    all_messages.append(HumanMessage(content=input_data))
                    result = await self._agent.ainvoke(
                        {
                            "messages": all_messages
                        }
                    )
                else:
                    # 如果是 dict 格式，使用 agent
                    result = await self._agent.ainvoke(
                        {
                            "messages": input_data
                        }
                    )
                
                # 提取文本内容
                if hasattr(result, 'content'):
                    return result.content
                return str(result)
        except asyncio.TimeoutError:
            print(f"请求处理超时（{timeout}秒）")
            raise
        except Exception as e:
            print(f"LLM 处理错误: {e}")
            raise
    
    async def stream_run(
        self,
        input_data: Any,
        callback: Optional[Callable[[str], None]] = None,
        timeout: float | None = None
    ) -> str:
        """流式运行 LLM 处理请求（打字机效果）
        
        Args:
            input_data: 输入数据（字符串）
            callback: 可选的回调函数，每收到一个 chunk 时调用
            timeout: 超时时间（秒），默认为配置中的超时时间
            
        Returns:
            完整的响应文本
            
        Raises:
            asyncio.TimeoutError: 请求超时
            RuntimeError: 服务未运行
        """
        if not self._running:
            raise RuntimeError("服务未运行，请先调用 start()")
        
        timeout = timeout or self._timeout
        full_response = []
        
        try:
            async with asyncio.timeout(timeout):
                if isinstance(input_data, str):
                    # 添加用户消息到长期记忆
                    if self._memory_manager is not None:
                        await self._memory_manager.add_message("user", input_data)  # type: ignore[union-attr]
                    
                    # 构建完整的消息列表（历史消息 + 当前输入）
                    messages = self._build_messages_with_history()
                    messages.append(HumanMessage(content=input_data))
                else:
                    messages = input_data
                
                # 使用 stream_mode="messages" 进行流式响应
                for chunk in self._agent.stream(
                    {"messages": messages},
                    stream_mode="messages",
                ):
                    token, metadata = chunk
                    
                    # 提取文本（处理 MiniMax 的 thinking + text 结构）
                    text = extract_stream_text(token)
                    
                    if text:
                        full_response.append(text)
                        
                        # 如果有回调函数，调用它
                        if callback:
                            callback(text)
                
                return ''.join(full_response)
                
        except asyncio.TimeoutError:
            print(f"请求处理超时（{timeout}秒）")
            raise
        except Exception as e:
            print(f"LLM 流式处理错误: {e}")
            raise
    
    async def stop(self) -> None:
        """停止服务
        
        优雅地停止服务，清理所有资源。
        """
        if not self._running:
            return
        
        print("正在停止服务...")
        
        try:
            await self._cleanup_resources()
        finally:
            self._running = False
            self._shutdown_event.set()
            print("服务已停止")
    
    async def _cleanup_resources(self) -> None:
        """清理资源"""
        # 清理 Agent
        if self._agent is not None:
            try:
                if hasattr(self._agent, "clear"):
                    self._agent.clear()
                print("Agent 资源已清理")
            except Exception as e:
                print(f"清理 Agent 资源时出错: {e}")
            finally:
                self._agent = None
        
        # 清理 LLM
        if self._llm is not None:
            try:
                print("LLM 资源已清理")
            except Exception as e:
                print(f"清理 LLM 资源时出错: {e}")
            finally:
                self._llm = None
    
    async def wait_for_shutdown(self) -> None:
        """等待关闭事件
        
        阻塞直到收到关闭信号或手动调用 stop()。
        """
        await self._shutdown_event.wait()
    
    def _build_messages_with_history(self) -> list[Any]:
        """构建包含历史消息的消息列表
        
        从长期记忆中获取历史消息，并转换为 LangChain 消息格式。
        
        Returns:
            消息列表（AIMessage 和 HumanMessage）
        """
        all_messages: list[Any] = []
        
        if self._memory_manager is not None:
            history_messages = self._memory_manager.get_messages()  # type: ignore[union-attr]
            for msg in history_messages:
                if msg.role == "user":
                    all_messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    all_messages.append(AIMessage(content=msg.content))
        
        return all_messages
    
    def get_shutdown_signal(self) -> signal.Signals | None:
        """获取收到的关闭信号
        
        Returns:
            收到的信号类型，如果没有收到信号返回 None
        """
        return self._signal_received
