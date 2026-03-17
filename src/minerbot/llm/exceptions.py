"""LLM 模块异常定义"""


class LLMFactoryError(Exception):
    """工厂基础异常"""
    pass


class UnsupportedProviderError(LLMFactoryError):
    """不支持的提供商异常"""
    pass


class InvalidConfigError(LLMFactoryError):
    """无效配置异常"""
    pass


class ModelNotSupportedError(LLMFactoryError):
    """模型不支持异常"""
    pass
