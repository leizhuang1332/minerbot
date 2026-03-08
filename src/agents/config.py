"""Agent Configuration
Agent 配置数据类，支持灵活的 LLM 和系统提示词配置
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

# Type imports - avoid circular dependency at runtime
if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    # DeepAgents types (may not be installed yet)
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

# Type alias
LLMType = Union["BaseChatModel", str, None]
MiddlewareType = Any
BackendType = Any
ToolsType = List[Any]


@dataclass(frozen=True)
class AgentConfig:
    """Agent 配置数据类
    
    用于配置 Agent 实例的创建参数。支持灵活的 LLM 传入方式
    和自定义系统提示词。
    
    Attributes:
        llm: LangChain 兼容的 LLM 实例或 provider 名称字符串
        system_prompt: 系统提示词
        backend: DeepAgents 后端存储 (可选)
        middleware: 中间件列表 (可选)
        tools: 工具列表 (可选)
        model: 模型名称，覆盖 llm 中的模型 (可选)
        extra: 额外配置参数 (可选)
    
    Example:
        # 使用 LLM 实例
        config = AgentConfig(
            llm=get_llm(),
            system_prompt="你是一个助手"
        )
        
        # 使用 provider 名称字符串
        config = AgentConfig(
            llm="minimax",
            system_prompt="你是一个助手"
        )
        
        # 完整配置
        config = AgentConfig(
            llm=get_llm(),
            system_prompt="你是一个助手",
            backend=FilesystemBackend(root_dir="."),
            middleware=[FilesystemMiddleware()],
            tools=[get_weather, calculate]
        )
    """
    
    llm: LLMType = None
    system_prompt: str = "你是一个助手"
    backend: BackendType = None
    middleware: List[MiddlewareType] = field(default_factory=list)
    tools: ToolsType = field(default_factory=list)
    model: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """验证配置参数"""
        # 确保 middleware 和 tools 是不可变类型（用于哈希）
        if not isinstance(self.middleware, (list, tuple)):
            object.__setattr__(self, 'middleware', list(self.middleware) if self.middleware else [])
        if not isinstance(self.tools, (list, tuple)):
            object.__setattr__(self, 'tools', list(self.tools) if self.tools else [])
    
    @property
    def model_name(self) -> Optional[str]:
        """获取模型名称
        
        优先级: model > llm.model (如果 llm 是 BaseChatModel)
        """
        if self.model:
            return self.model
        
        # 尝试从 llm 实例获取模型名称
        if self.llm and hasattr(self.llm, 'model'):
            return getattr(self.llm, 'model', None)
        
        # 如果 llm 是字符串，直接返回
        if isinstance(self.llm, str):
            return self.llm
        
        return None
    
    @property
    def provider_name(self) -> Optional[str]:
        """获取 provider 名称
        
        如果 llm 是字符串，返回该字符串作为 provider 名称
        """
        if isinstance(self.llm, str):
            return self.llm
        return None
    
    def to_hash(self) -> str:
        """生成配置哈希值
        
        用于全局单例判定。两个配置被认为是"相同"当且仅当
        它们的哈希值完全相同。
        
        哈希考虑因素:
        - llm 模型名称
        - system_prompt
        - backend 类型和根目录 (如果存在)
        - tools 列表 (如果存在)
        """
        # 收集用于哈希的数据
        hash_data = {
            'model': self.model_name or '',
            'system_prompt': self.system_prompt,
            'model_explicit': self.model or '',
        }
        
        # 添加 backend 信息 (如果存在)
        if self.backend is not None:
            backend_info = {}
            if hasattr(self.backend, 'root_dir'):
                backend_info['root_dir'] = str(self.backend.root_dir)
            if hasattr(self.backend, '__class__'):
                backend_info['class'] = self.backend.__class__.__name__
            hash_data['backend'] = backend_info
        
        # 添加 tools 信息 (如果存在)
        if self.tools:
            tool_names = []
            for tool in self.tools:
                if hasattr(tool, 'name'):
                    tool_names.append(tool.name)
                elif callable(tool):
                    tool_names.append(tool.__class__.__name__ if hasattr(tool, '__class__') else str(tool))
            hash_data['tools'] = sorted(tool_names)
        
        # 生成哈希
        json_str = json.dumps(hash_data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    def __eq__(self, other: object) -> bool:
        """比较两个配置是否相等"""
        if not isinstance(other, AgentConfig):
            return NotImplemented
        return self.to_hash() == other.to_hash()
    
    def __hash__(self) -> int:
        """返回配置哈希的整数值"""
        return int(self.to_hash()[:16], 16)
    
    def with_llm(self, llm: LLMType) -> "AgentConfig":
        """创建新的配置，替换 LLM"""
        return AgentConfig(
            llm=llm,
            system_prompt=self.system_prompt,
            backend=self.backend,
            middleware=self.middleware.copy(),
            tools=self.tools.copy(),
            model=self.model,
            extra=self.extra.copy()
        )
    
    def with_system_prompt(self, system_prompt: str) -> "AgentConfig":
        """创建新的配置，替换系统提示词"""
        return AgentConfig(
            llm=self.llm,
            system_prompt=system_prompt,
            backend=self.backend,
            middleware=self.middleware.copy(),
            tools=self.tools.copy(),
            model=self.model,
            extra=self.extra.copy()
        )
    
    def with_backend(self, backend: BackendType) -> "AgentConfig":
        """创建新的配置，替换后端"""
        return AgentConfig(
            llm=self.llm,
            system_prompt=self.system_prompt,
            backend=backend,
            middleware=self.middleware.copy(),
            tools=self.tools.copy(),
            model=self.model,
            extra=self.extra.copy()
        )
    
    def with_middleware(self, middleware: List[MiddlewareType]) -> "AgentConfig":
        """创建新的配置，替换中间件"""
        return AgentConfig(
            llm=self.llm,
            system_prompt=self.system_prompt,
            backend=self.backend,
            middleware=middleware,
            tools=self.tools.copy(),
            model=self.model,
            extra=self.extra.copy()
        )
    
    def with_tools(self, tools: ToolsType) -> "AgentConfig":
        """创建新的配置，替换工具列表"""
        return AgentConfig(
            llm=self.llm,
            system_prompt=self.system_prompt,
            backend=self.backend,
            middleware=self.middleware.copy(),
            tools=tools,
            model=self.model,
            extra=self.extra.copy()
        )
    
    def with_model(self, model: str) -> "AgentConfig":
        """创建新的配置，替换模型名称"""
        return AgentConfig(
            llm=self.llm,
            system_prompt=self.system_prompt,
            backend=self.backend,
            middleware=self.middleware.copy(),
            tools=self.tools.copy(),
            model=model,
            extra=self.extra.copy()
        )

        """创建新的配置，替换工具列表"""
        return AgentConfig(
            llm=self.llm,
            system_prompt=self.system_prompt,
            backend=self.backend,
            middleware=self.middleware.copy(),
            tools=tools,
            model=self.model,
            extra=self.extra.copy()
        )
    
    def merge(self, **kwargs: Any) -> "AgentConfig":
        """创建新的配置，合并额外参数"""
        return AgentConfig(
            llm=kwargs.get('llm', self.llm),
            system_prompt=kwargs.get('system_prompt', self.system_prompt),
            backend=kwargs.get('backend', self.backend),
            middleware=kwargs.get('middleware', self.middleware.copy()),
            tools=kwargs.get('tools', self.tools.copy()),
            model=kwargs.get('model', self.model),
            extra={**self.extra, **kwargs.get('extra', {})}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'llm': self.llm,
            'system_prompt': self.system_prompt,
            'backend': self.backend,
            'middleware': self.middleware,
            'tools': self.tools,
            'model': self.model,
            'extra': self.extra,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        """从字典创建"""
        return cls(
            llm=data.get('llm'),
            system_prompt=data.get('system_prompt', "你是一个助手"),
            backend=data.get('backend'),
            middleware=data.get('middleware', []),
            tools=data.get('tools', []),
            model=data.get('model'),
            extra=data.get('extra', {}),
        )
    
    @classmethod
    def from_defaults(cls, **kwargs: Any) -> "AgentConfig":
        """使用默认参数创建配置
        
        所有参数都是可选的，未提供的参数将使用默认值。
        
        Example:
            config = AgentConfig.from_defaults(
                llm="minimax",
                system_prompt="你是一个助手"
            )
        """
        return cls(
            llm=kwargs.get('llm'),
            system_prompt=kwargs.get('system_prompt', "你是一个助手"),
            backend=kwargs.get('backend'),
            middleware=kwargs.get('middleware', []),
            tools=kwargs.get('tools', []),
            model=kwargs.get('model'),
            extra=kwargs.get('extra', {}),
        )


# Type alias for easier imports
AgentConfigType = AgentConfig
