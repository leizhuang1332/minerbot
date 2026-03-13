"""Agent Factory
Agent 工厂类，支持灵活的 LLM 传入和全局单例模式
"""
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

# Runtime imports
from langchain_core.language_models import BaseChatModel

# Type imports
if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    
    # DeepAgents types
    try:
        from deepagents import CompiledStateGraph
    except ImportError:
        CompiledStateGraph = Any
    
    try:
        from deepagents.backends import StateBackend
    except ImportError:
        StateBackend = Any
    
    try:
        from deepagents.middleware import Middleware
    except ImportError:
        Middleware = Any

# Local imports
from .config import AgentConfig

# Type alias
AgentType = Any  # CompiledStateGraph or similar
LLMType = Union["BaseChatModel", str, None]


class AgentFactoryError(Exception):
    """Agent 工厂异常基类"""
    pass


class LLMNotAvailableError(AgentFactoryError):
    """LLM 不可用异常"""
    pass


class DeepAgentsNotAvailableError(AgentFactoryError):
    """DeepAgents 不可用异常"""
    pass


class AgentFactory:
    """Agent 工厂类
    
    管理 Agent 实例的创建和全局缓存。支持两种模式:
    1. 每次创建新实例 (create_agent)
    2. 全局单例模式 (get_agent / get_or_create)
    
    全局单例判定规则:
    - llm 模型名称相同
    - system_prompt 完全相同
    - backend 类型和根目录相同 (如果配置)
    - tools 列表相同 (如果配置)
    
    Example:
        # 方式1: 创建新实例 (每次返回新 Agent)
        agent1 = factory.create_agent(config)
        agent2 = factory.create_agent(config)
        # agent1 is not agent2  # True
        
        # 方式2: 全局单例 (相同配置返回同一实例)
        agent1 = factory.get_agent(config)
        agent2 = factory.get_agent(config)
        # agent1 is agent2  # True
        
        # 方式3: 获取或创建 (优先返回缓存)
        agent = factory.get_or_create(config)
    """
    
    _instance: Optional["AgentFactory"] = None
    _global_cache: Dict[str, AgentType] = {}
    _initialized: bool = False
    
    def __new__(cls) -> "AgentFactory":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """初始化工厂"""
        if not AgentFactory._initialized:
            self._local_cache: Dict[str, AgentType] = {}
            AgentFactory._initialized = True
    

    
    def _resolve_llm(self, llm: LLMType) -> "BaseChatModel":
        """解析 LLM 参数
        
        支持:
        - None: 使用默认 LLM
        - str: provider 名称，从 src.llms 获取
        - BaseChatModel: 直接使用
        
        Args:
            llm: LLM 参数
            
        Returns:
            BaseChatModel 实例
            
        Raises:
            LLMNotAvailableError: 无法获取 LLM
        """
        if llm is None:
            # 尝试使用默认 LLM
            try:
                from src.llms import get_llm
                return get_llm()
            except ImportError:
                raise LLMNotAvailableError(
                    "LLM not provided and src.llms is not available. "
                    "Please provide an LLM instance or install src.llms."
                )
        
        if isinstance(llm, str):
            # 使用 provider 名称获取 LLM
            try:
                from src.llms import get_llm
                return get_llm(provider=llm)
            except ImportError:
                raise LLMNotAvailableError(
                    f"Failed to get LLM for provider '{llm}'. "
                    "Please provide a valid LLM instance."
                )
        
        # 已经是 BaseChatModel
        return llm
    
    def _create_agent_instance(self, config: AgentConfig) -> AgentType:
        print(f"创建 Agent 实例_create_agent_instance: {config}")
        """创建 Agent 实例
        
        使用 DeepAgents SDK 创建 Agent。
        
        Args:
            config: Agent 配置
            
        Returns:
            Agent 实例 (CompiledStateGraph)
            
        Raises:
            DeepAgentsNotAvailableError: DeepAgents 不可用
        """
        try:
            from deepagents import create_deep_agent
        except ImportError as e:
            raise DeepAgentsNotAvailableError(
                f"Failed to import deepagents: {e}. "
                "Please ensure deepagents is installed."
            )
        
        # 解析 LLM
        llm = self._resolve_llm(config.llm)
        
        # 构建参数
        create_kwargs: Dict[str, Any] = {}
        
        # 设置模型 - 优先使用 resolved LLM 实例
        if isinstance(llm, BaseChatModel):
            create_kwargs['model'] = llm  # 传递完整的 LLM 实例
        elif config.model:
            create_kwargs['model'] = config.model
        elif isinstance(config.llm, str):
            create_kwargs['model'] = config.llm
        
        # 设置系统提示词
        if config.system_prompt:
            # DeepAgents 使用 system_prompt 参数
            create_kwargs['system_prompt'] = config.system_prompt
        
        # 设置 backend
        if config.backend is not None:
            create_kwargs['backend'] = config.backend
        
        # 设置 middleware
        if config.middleware:
            create_kwargs['middleware'] = config.middleware
        
        # 设置 tools
        if config.tools:
            create_kwargs['tools'] = config.tools
        # 设置 checkpointer (短期记忆/对话历史持久化)
        if config.checkpointer is not None:
            create_kwargs['checkpointer'] = config.checkpointer

        # 设置 store (长期记忆存储)
        if config.store is not None:
            create_kwargs['store'] = config.store

        # 合并 extra 参数
        create_kwargs.update(config.extra)
        
        # 创建 Agent
        try:
            agent = create_deep_agent(**create_kwargs)
            return agent
        except Exception as e:
            raise AgentFactoryError(f"Failed to create agent: {e}") from e
    
    def create_agent(
        self,
        config: Optional[AgentConfig] = None,
        *,
        llm: LLMType = None,
        system_prompt: str = "你是一个助手",
        backend: Any = None,
        middleware: Optional[List[Any]] = None,
        tools: Optional[List[Any]] = None,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> AgentType:
        """创建新的 Agent 实例
        
        每次调用都会创建新的 Agent 实例，不使用缓存。
        
        Args:
            config: AgentConfig 对象 (可选)
            llm: LLM 实例或 provider 名称 (可选)
            system_prompt: 系统提示词 (可选)
            backend: 后端存储 (可选)
            middleware: 中间件列表 (可选)
            tools: 工具列表 (可选)
            model: 模型名称 (可选)
            **kwargs: 额外参数
            
        Returns:
            新的 Agent 实例
            
        Example:
            # 使用 config 对象
            config = AgentConfig(llm=get_llm(), system_prompt="你是一个助手")
            agent = factory.create_agent(config)
            
            # 使用便捷参数
            agent = factory.create_agent(
                llm="minimax",
                system_prompt="你是一个助手"
            )
        """
        # 合并参数创建配置
        if config is None:
            config = AgentConfig(
                llm=llm,
                system_prompt=system_prompt,
                backend=backend,
                middleware=middleware or [],
                tools=tools or [],
                model=model,
                extra=kwargs
            )
        elif llm is not None or system_prompt != "你是一个助手" or backend is not None:
            # 如果提供了额外参数，创建新的 config
            config = config.merge(
                llm=llm if llm is not None else config.llm,
                system_prompt=system_prompt if system_prompt != "你是一个助手" else config.system_prompt,
                backend=backend if backend is not None else config.backend,
                middleware=middleware if middleware is not None else config.middleware,
                tools=tools if tools is not None else config.tools,
                model=model if model is not None else config.model,
                extra=kwargs
            )
        
        return self._create_agent_instance(config)
    
    def get_agent(
        self,
        config: Optional[AgentConfig] = None,
        *,
        llm: LLMType = None,
        system_prompt: str = "你是一个助手",
        backend: Any = None,
        middleware: Optional[List[Any]] = None,
        tools: Optional[List[Any]] = None,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> AgentType:
        """获取全局单例 Agent
        
        相同配置 (llm + system_prompt) 下只返回一个 Agent 实例。
        
        Args:
            config: AgentConfig 对象 (可选)
            llm: LLM 实例或 provider 名称 (可选)
            system_prompt: 系统提示词 (可选)
            backend: 后端存储 (可选)
            middleware: 中间件列表 (可选)
            tools: 工具列表 (可选)
            model: 模型名称 (可选)
            **kwargs: 额外参数
            
        Returns:
            Agent 实例 (全局单例)
            
        Example:
            # 相同配置返回同一实例
            agent1 = factory.get_agent(llm="minimax", system_prompt="你是一个助手")
            agent2 = factory.get_agent(llm="minimax", system_prompt="你是一个助手")
            # agent1 is agent2  # True
        """
        # 创建或合并配置
        if config is None:
            config = AgentConfig(
                llm=llm,
                system_prompt=system_prompt,
                backend=backend,
                middleware=middleware or [],
                tools=tools or [],
                model=model,
                extra=kwargs
            )
        
        # 获取配置哈希
        config_hash = config.to_hash()
        
        # 检查全局缓存
        if config_hash in AgentFactory._global_cache:
            return AgentFactory._global_cache[config_hash]
        
        # 创建新实例并缓存
        agent = self._create_agent_instance(config)
        AgentFactory._global_cache[config_hash] = agent
        
        return agent
    
    def get_or_create(
        self,
        config: Optional[AgentConfig] = None,
        *,
        llm: LLMType = None,
        system_prompt: str = "你是一个助手",
        backend: Any = None,
        middleware: Optional[List[Any]] = None,
        tools: Optional[List[Any]] = None,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> AgentType:
        """获取或创建 Agent
        
        相当于 get_agent，但语义上更强调"获取或创建"。
        
        Args:
            config: AgentConfig 对象 (可选)
            llm: LLM 实例或 provider 名称 (可选)
            system_prompt: 系统提示词 (可选)
            backend: 后端存储 (可选)
            middleware: 中间件列表 (可选)
            tools: 工具列表 (可选)
            model: 模型名称 (可选)
            **kwargs: 额外参数
            
        Returns:
            Agent 实例
        """
        return self.get_agent(
            config=config,
            llm=llm,
            system_prompt=system_prompt,
            backend=backend,
            middleware=middleware,
            tools=tools,
            model=model,
            **kwargs
        )
    

    

    



# 全局工厂实例
_factory: Optional[AgentFactory] = None


def get_factory() -> AgentFactory:
    """获取全局 AgentFactory 实例"""
    global _factory
    if _factory is None:
        _factory = AgentFactory()
    return _factory


# 便捷函数




def get_agent(
    llm: LLMType = None,
    system_prompt: str = "你是一个助手",
    *,
    backend: Any = None,
    middleware: Optional[List[Any]] = None,
    tools: Optional[List[Any]] = None,
    model: Optional[str] = None,
    **kwargs: Any
) -> AgentType:
    """获取全局单例 Agent
    
    相同配置 (llm + system_prompt) 下只返回一个 Agent 实例。
    
    Args:
        llm: LLM 实例或 provider 名称
        system_prompt: 系统提示词
        backend: 后端存储 (可选)
        middleware: 中间件列表 (可选)
        tools: 工具列表 (可选)
        model: 模型名称 (可选)
        **kwargs: 额外参数
        
    Returns:
        Agent 实例 (全局单例)
        
    Example:
        # 相同配置返回同一实例
        agent1 = get_agent("minimax", "你是一个助手")
        agent2 = get_agent("minimax", "你是一个助手")
        # agent1 is agent2  # True
    """
    factory = get_factory()
    return factory.get_agent(
        llm=llm,
        system_prompt=system_prompt,
        backend=backend,
        middleware=middleware,
        tools=tools,
        model=model,
        **kwargs
    )


def get_or_create_agent(
    llm: LLMType = None,
    system_prompt: str = "你是一个助手",
    *,
    backend: Any = None,
    middleware: Optional[List[Any]] = None,
    tools: Optional[List[Any]] = None,
    model: Optional[str] = None,
    **kwargs: Any
) -> AgentType:
    """获取或创建 Agent
    
    相当于 get_agent，但语义上更强调"获取或创建"。
    
    Args:
        llm: LLM 实例或 provider 名称
        system_prompt: 系统提示词
        backend: 后端存储 (可选)
        middleware: 中间件列表 (可选)
        tools: 工具列表 (可选)
        model: 模型名称 (可选)
        **kwargs: 额外参数
        
    Returns:
        Agent 实例
    """
    factory = get_factory()
    return factory.get_or_create(
        llm=llm,
        system_prompt=system_prompt,
        backend=backend,
        middleware=middleware,
        tools=tools,
        model=model,
        **kwargs
    )


# 别名
get_or_create = get_or_create_agent
