"""Service 模块 - 应用服务生命周期管理"""

import asyncio
import signal
import sys
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from src.app.config import Config
from src.agents import get_agent as get_agent_func
from src.llms import get_llm as get_llm_func


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
        
        # 设置信号处理
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """设置系统信号处理器"""
        if sys.platform != "win32":
            # Unix-like 系统
            loop = asyncio.get_event_loop()
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
                    result = await self._agent.ainvoke(
                        {
                            "messages": [
                                HumanMessage(content=input_data)
                            ]
                        }
                    )
                    # 提取文本内容
                    if hasattr(result, 'content'):
                        return result.content
                    return str(result)
                
                # 如果是 dict 格式，使用 agent
                result = await self._agent.ainvoke(
                    {
                        "messages": input_data
                    }
                )
                return result
        except asyncio.TimeoutError:
            print(f"请求处理超时（{timeout}秒）")
            raise
        except Exception as e:
            print(f"LLM 处理错误: {e}")
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
    
    def get_shutdown_signal(self) -> signal.Signals | None:
        """获取收到的关闭信号
        
        Returns:
            收到的信号类型，如果没有收到信号返回 None
        """
        return self._signal_received
