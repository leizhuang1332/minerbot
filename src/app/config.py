"""应用配置加载器
从YAML配置文件加载应用服务配置和Agent配置
"""
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class Config:
    """应用配置加载器"""
    
    _instance: Optional["Config"] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self) -> None:
        """加载配置文件"""
        config_path = Path(__file__).parent.parent.parent / "config" / "app_config.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}
        
        # 验证必需的配置节
        self._validate()
    
    def _validate(self) -> None:
        """验证配置完整性"""
        required_sections = ["service", "agent"]
        
        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"Required config section '{section}' is missing in app_config.yaml")
    
    @classmethod
    def load(cls) -> "Config":
        """加载配置（返回单例实例）"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @property
    def service_config(self) -> Dict[str, Any]:
        """获取服务配置"""
        return self._config.get("service", {})
    
    @property
    def agent_config(self) -> Dict[str, Any]:
        """获取Agent配置"""
        return self._config.get("agent", {})
    
    @classmethod
    def reload(cls) -> None:
        """重新加载配置"""
        if cls._instance:
            cls._instance._load_config()


# 全局配置实例
config = Config()
