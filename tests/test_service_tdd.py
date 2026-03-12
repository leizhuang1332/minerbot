"""Service 模块 TDD 测试

验证 src/app/service.py 中的 bug 修复：
1. run 方法不再有完全重复的代码块
2. stream_run 方法逻辑正确（不再有多个 else 分支）
3. _memory_manager 属性已定义
4. 没有重复的函数定义
5. 没有不可达代码
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch


class TestServiceBugs:
    """测试 Service 类的 bug 修复"""

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = MagicMock()
        config.service_config = {"timeout": 60.0}
        config.agent_config = {"system_prompt": "你是一个助手"}
        return config

    def test_memory_manager_is_defined(self, mock_config):
        """测试 _memory_manager 已定义"""
        from src.app.service import Service
        
        service = Service(mock_config)
        
        # 检查是否有 _memory_manager 属性
        assert hasattr(service, '_memory_manager'), "_memory_manager 属性未定义"

    def test_no_completely_duplicate_run_code(self, mock_config):
        """测试 run 方法中没有完全重复的代码块"""
        from src.app.service import Service
        import inspect
        
        source = inspect.getsource(Service.run)
        
        # 查找是否有完全重复的代码块（通过查找连续的重复行）
        lines = source.split('\n')
        prev_line = ""
        duplicate_count = 0
        
        for line in lines:
            stripped = line.strip()
            # 检测连续重复的非空行（至少5个字符以上）
            if stripped and len(stripped) > 20 and stripped == prev_line:
                duplicate_count += 1
            prev_line = stripped if stripped else prev_line
        
        # 如果有完全重复的代码，duplicate_count > 0
        assert duplicate_count == 0, f"run 方法中有完全重复的代码块 ({duplicate_count} 处)"

    def test_stream_run_valid_syntax(self, mock_config):
        """测试 stream_run 方法语法正确（没有多个 else 分支）"""
        from src.app.service import Service
        import inspect
        
        # 确保可以成功获取源码（没有语法错误）
        source = inspect.getsource(Service.stream_run)
        assert source is not None
        
        # 检查只有一个 if 和一个 else
        if_count = source.count('if isinstance(input_data, str):')
        else_count = source.count('else:')
        
        assert if_count == 1, f"应该只有1个if判断，实际有{if_count}个"
        assert else_count == 1, f"应该只有1个else分支，实际有{else_count}个"

    def test_no_duplicate_function_definitions(self):
        """测试没有重复的函数定义"""
        from src.app.service import Service
        import inspect
        
        source = inspect.getsource(Service)
        
        # 检查 wait_for_shutdown 只定义一次
        wait_count = source.count('async def wait_for_shutdown(self)')
        assert wait_count == 1, f"wait_for_shutdown 应该定义1次，实际{wait_count}次"
        
        # 检查 get_shutdown_signal 只定义一次
        get_signal_count = source.count('def get_shutdown_signal(self)')
        assert get_signal_count == 1, f"get_shutdown_signal 应该定义1次，实际{get_signal_count}次"

    def test_no_unreachable_code_in_stream_run(self):
        """测试 stream_run 中没有不可达代码"""
        from src.app.service import Service
        import inspect
        
        source = inspect.getsource(Service.stream_run)
        
        # 检查 try-except 之后没有额外代码
        lines = source.split('\n')
        in_except = False
        found_code_after_except = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if 'except' in stripped and 'as' in stripped:
                in_except = True
            elif in_except:
                # 检查是否是 raise 之后的非缩进代码
                if stripped and not stripped.startswith('#') and not stripped.startswith(' ') and not stripped.startswith('\t'):
                    # 检查是否是另一个 except 或函数定义
                    if stripped.startswith('def ') or stripped.startswith('async def ') or stripped.startswith('@'):
                        found_code_after_except = True
                        break
        
        assert not found_code_after_except, "stream_run 方法中存在不可达代码"


class TestServiceFunctionality:
    """测试 Service 类的功能（修复后）"""

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = MagicMock()
        config.service_config = {"timeout": 60.0}
        config.agent_config = {"system_prompt": "你是一个助手"}
        return config

    def test_service_initialization(self, mock_config):
        """测试 Service 正确初始化"""
        from src.app.service import Service
        
        service = Service(mock_config)
        
        assert service._config == mock_config
        assert service._running is False
        assert service._llm is None
        assert service._agent is None
        assert hasattr(service, '_memory_manager')

    @pytest.mark.asyncio
    async def test_start_service(self, mock_config):
        """测试服务启动"""
        from src.app.service import Service
        from src.llms import get_llm
        from src.agents import get_agent
        
        mock_llm = MagicMock()
        mock_agent = MagicMock()
        
        with patch.object(get_llm, '__call__', return_value=mock_llm), \
             patch.object(get_agent, '__call__', return_value=mock_agent):
            
            service = Service(mock_config)
            await service.start()
            
            assert service.is_running is True
            assert service.llm is not None
            assert service.agent is not None

    @pytest.mark.asyncio
    async def test_run_not_running_raises_error(self, mock_config):
        """测试服务未运行时 run 抛出错误"""
        from src.app.service import Service
        
        service = Service(mock_config)
        
        with pytest.raises(RuntimeError, match="服务未运行"):
            await service.run("test")

    @pytest.mark.asyncio
    async def test_stop_not_running(self, mock_config):
        """测试服务未运行时 stop 不报错"""
        from src.app.service import Service
        
        service = Service(mock_config)
        
        # 不应该抛出异常
        await service.stop()
        
        assert service.is_running is False

    def test_build_messages_with_history_empty(self, mock_config):
        """测试空历史消息"""
        from src.app.service import Service
        
        service = Service(mock_config)
        
        messages = service._build_messages_with_history()
        
        assert messages == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
