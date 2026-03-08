"""LLM Configuration Loader
从YAML配置文件和环境变量加载LLM配置
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class LLMConfig:
    """LLM配置加载器"""
    
    _instance: Optional["LLMConfig"] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls) -> "LLMConfig":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self) -> None:
        """加载配置文件"""
        config_path = Path(__file__).parent.parent.parent / "config" / "llm_config.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}
        
        # 加载环境变量
        self._load_env()
    
    def _load_env(self) -> None:
        """从.env文件加载环境变量"""
        env_path = Path(__file__).parent.parent.parent / ".env"
        
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
    
    @property
    def default_provider(self) -> str:
        """获取默认Provider"""
        return self._config.get("default_provider", "minimax")
    
    @property
    def providers(self) -> Dict[str, Dict[str, Any]]:
        """获取所有Provider配置"""
        return self._config.get("providers", {})
    
    @property
    def defaults(self) -> Dict[str, Any]:
        """获取全局默认参数"""
        return self._config.get("defaults", {})
    
    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """获取指定Provider的配置"""
        providers = self.providers
        if provider_name not in providers:
            raise ValueError(f"Provider '{provider_name}' not found. Available: {list(providers.keys())}")
        
        config = providers[provider_name].copy()
        
        # 从环境变量读取API Key
        api_key_env = config.pop("api_key_env", None)
        if api_key_env:
            api_key = os.environ.get(api_key_env)
            if not api_key:
                raise ValueError(f"API key not found in environment: {api_key_env}")
            config["api_key"] = api_key
        
        # 合并默认参数
        for key, value in self.defaults.items():
            if key not in config:
                config[key] = value
        
        return config
    
    def get_current_config(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """获取当前使用的Provider配置"""
        provider = provider_name or self.default_provider
        return self.get_provider_config(provider)
    
    @classmethod
    def reload(cls) -> None:
        """重新加载配置"""
        if cls._instance:
            cls._instance._load_config()


# 全局配置实例
config = LLMConfig()
