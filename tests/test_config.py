"""配置测试"""
import os
import pytest
from minerbot.config import AppConfig


def test_config_default_values():
    """测试配置默认值"""
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    
    config = AppConfig.from_env()
    
    assert config.anthropic_api_key == "test-key"
    assert config.model_name == "claude-sonnet-4-6"
    assert config.temperature == 0.7
    assert config.max_tokens == 4096
    assert config.sqlite_db_path == "data/minerbot.db"


def test_config_validation():
    """测试配置验证"""
    config = AppConfig(anthropic_api_key="")
    
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
        config.validate()


def test_config_with_tavily():
    """测试 Tavily 配置"""
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    os.environ["TAVILY_API_KEY"] = "tavily-test"
    
    config = AppConfig.from_env()
    
    assert config.tavily_api_key == "tavily-test"
