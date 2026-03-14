"""自定义异常类"""


class MinerBotError(Exception):
    """基础异常"""
    pass


class ConfigurationError(MinerBotError):
    """配置错误"""
    pass


class AgentError(MinerBotError):
    """Agent 错误"""
    pass


class ToolError(MinerBotError):
    """工具执行错误"""
    pass


class SessionError(MinerBotError):
    """会话错误"""
    pass
