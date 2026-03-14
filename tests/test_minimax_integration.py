"""MiniMax 集成测试"""
import os
import pytest
from unittest.mock import patch, MagicMock

from minerbot.config import AppConfig
from minerbot.agent.factory import create_agent
from minerbot.exceptions import AgentError


# 检查 API 密钥是否可用
HAS_ANTHROPIC_KEY = bool(os.getenv("ANTHROPIC_API_KEY"))
HAS_MINIMAX_KEY = bool(os.getenv("MINIMAX_API_KEY"))


class TestMiniMaxConfig:
    """测试 MiniMax 配置加载"""

    def test_config_loads_minimax_from_env(self):
        """测试从环境变量加载 MiniMax 配置"""
        with patch("minerbot.config.load_dotenv"):
            os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
            os.environ["MINIMAX_API_KEY"] = "test-minimax-key"
            os.environ["MINIMAX_BASE_URL"] = "https://api.minimaxi.com/anthropic"
            os.environ["MINIMAX_MODEL"] = "MiniMax-M2.5"
            
            config = AppConfig.from_env()
            
            assert config.minimax_api_key == "test-minimax-key"
            assert config.minimax_base_url == "https://api.minimaxi.com/anthropic"
            assert config.minimax_model == "MiniMax-M2.5"

    def test_config_minimax_defaults(self):
        """测试 MiniMax 配置默认值"""
        with patch("minerbot.config.load_dotenv") as mock_load_dotenv:
            mock_load_dotenv.return_value = None
            os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
            os.environ.pop("MINIMAX_API_KEY", None)
            
            config = AppConfig.from_env()
            
            assert config.minimax_base_url == "https://api.minimaxi.com/anthropic"
            assert config.minimax_model == "MiniMax-M2.5"
            assert config.minimax_api_key is None


class TestModelRouting:
    """测试模型路由逻辑"""

    @pytest.mark.skipif(not HAS_MINIMAX_KEY, reason="需要 MINIMAX_API_KEY")
    def test_uses_minimax_when_api_key_set(self):
        """测试当设置了 MINIMAX_API_KEY 时使用 MiniMax"""
        config = AppConfig.from_env()
        
        with patch("minerbot.agent.factory.ChatAnthropic") as mock_model:
            mock_instance = MagicMock()
            mock_model.return_value = mock_instance
            
            agent = create_agent(config)
            
            # 验证使用了 MiniMax 配置
            mock_model.assert_called_once()
            call_kwargs = mock_model.call_args.kwargs
            assert call_kwargs["model_name"] == config.minimax_model
            assert call_kwargs["base_url"] == config.minimax_base_url
            assert call_kwargs["api_key"] == config.minimax_api_key

    @pytest.mark.skipif(not HAS_ANTHROPIC_KEY, reason="需要 ANTHROPIC_API_KEY")
    def test_fallback_to_anthropic_when_no_minimax_key(self):
        """测试当没有 MINIMAX_API_KEY 时回退到 Anthropic"""
        with patch("minerbot.config.load_dotenv"):
            os.environ.pop("MINIMAX_API_KEY", None)
            
            config = AppConfig.from_env()
            
            with patch("minerbot.agent.factory.ChatAnthropic") as mock_model, \
                 patch("minerbot.agent.factory.create_deep_agent") as mock_create:
                mock_instance = MagicMock()
                mock_model.return_value = mock_instance
                mock_create.return_value = MagicMock()
                
                agent = create_agent(config)
                
                mock_model.assert_called_once()
                call_kwargs = mock_model.call_args.kwargs
                assert call_kwargs["model_name"] == config.model_name
                assert "base_url" not in call_kwargs
                assert call_kwargs["api_key"] == config.anthropic_api_key

    def test_model_selection_logic_with_minimax_key(self):
        """测试模型选择逻辑 - 有 MiniMax Key"""
        with patch("minerbot.config.load_dotenv"):
            os.environ["ANTHROPIC_API_KEY"] = "test-anthropic"
            os.environ["MINIMAX_API_KEY"] = "test-minimax"
            
            config = AppConfig.from_env()
            
            with patch("minerbot.agent.factory.ChatAnthropic") as mock_model, \
                 patch("minerbot.agent.factory.create_deep_agent") as mock_create:
                mock_model.return_value = MagicMock()
                mock_create.return_value = MagicMock()
                
                create_agent(config)
                
                call_kwargs = mock_model.call_args.kwargs
                assert call_kwargs["model_name"] == "MiniMax-M2.5"

    def test_model_selection_logic_without_minimax_key(self):
        """测试模型选择逻辑 - 无 MiniMax Key"""
        with patch("minerbot.config.load_dotenv"):
            os.environ["ANTHROPIC_API_KEY"] = "test-anthropic"
            os.environ.pop("MINIMAX_API_KEY", None)
            
            config = AppConfig.from_env()
            
            with patch("minerbot.agent.factory.ChatAnthropic") as mock_model, \
                 patch("minerbot.agent.factory.create_deep_agent") as mock_create:
                mock_model.return_value = MagicMock()
                mock_create.return_value = MagicMock()
                
                create_agent(config)
                
                call_kwargs = mock_model.call_args.kwargs
                assert call_kwargs["model_name"] == config.model_name


class TestValidation:
    """测试配置验证"""

    def test_validation_requires_at_least_one_api_key(self):
        """测试验证 - 至少需要一个 API Key"""
        # 清除所有 API Key
        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig(anthropic_api_key="", minimax_api_key=None)
            
            with pytest.raises(ValueError, match="At least one of ANTHROPIC_API_KEY or MINIMAX_API_KEY is required"):
                config.validate()

    def test_validation_passes_with_anthropic_key(self):
        """测试验证 - 只有 Anthropic Key 通过"""
        config = AppConfig(anthropic_api_key="test-key", minimax_api_key=None)
        
        config.validate()  # 应该不抛出异常

    def test_validation_passes_with_minimax_key(self):
        """测试验证 - 只有 MiniMax Key 通过"""
        config = AppConfig(anthropic_api_key="", minimax_api_key="test-key")
        
        config.validate()  # 应该不抛出异常


class TestAgentCreation:
    """测试 Agent 创建流程"""

    def test_create_agent_with_minimax_config(self):
        """测试使用 MiniMax 配置创建 Agent"""
        with patch("minerbot.config.load_dotenv"):
            os.environ["ANTHROPIC_API_KEY"] = "test-anthropic"
            os.environ["MINIMAX_API_KEY"] = "test-minimax"
            
            config = AppConfig.from_env()
            
            with patch("minerbot.agent.factory.create_deep_agent") as mock_create:
                mock_create.return_value = MagicMock()
                
                agent = create_agent(config)
                
                mock_create.assert_called_once()

    def test_create_agent_fallback_config(self):
        """测试使用回退配置创建 Agent"""
        with patch("minerbot.config.load_dotenv"):
            os.environ["ANTHROPIC_API_KEY"] = "test-anthropic"
            os.environ.pop("MINIMAX_API_KEY", None)
            
            config = AppConfig.from_env()
            
            with patch("minerbot.agent.factory.create_deep_agent") as mock_create:
                mock_create.return_value = MagicMock()
                
                agent = create_agent(config)
                
                mock_create.assert_called_once()

    @pytest.mark.skipif(not (HAS_ANTHROPIC_KEY or HAS_MINIMAX_KEY), reason="需要至少一个 API Key")
    def test_create_agent_raises_on_model_init_failure(self):
        """测试模型初始化失败时抛出 AgentError"""
        with patch("minerbot.config.load_dotenv"):
            os.environ["ANTHROPIC_API_KEY"] = "test-key"
            os.environ.pop("MINIMAX_API_KEY", None)
            
            config = AppConfig.from_env()
            
            with patch("minerbot.agent.factory.ChatAnthropic") as mock_model:
                mock_model.side_effect = Exception("Connection error")
                
                with pytest.raises(AgentError, match="模型初始化失败"):
                    create_agent(config)
