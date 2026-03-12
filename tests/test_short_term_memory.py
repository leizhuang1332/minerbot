"""短期记忆功能测试"""

import pytest
from unittest.mock import MagicMock, patch


class TestAgentConfigMemoryFields:
    """测试 AgentConfig 的 checkpointer 和 store 字段"""
    
    def test_checkpointer_field_exists(self):
        """测试 checkpointer 字段存在"""
        from src.agents.config import AgentConfig
        config = AgentConfig()
        assert hasattr(config, 'checkpointer')
        assert config.checkpointer is None
    
    def test_store_field_exists(self):
        """测试 store 字段存在"""
        from src.agents.config import AgentConfig
        config = AgentConfig()
        assert hasattr(config, 'store')
        assert config.store is None
    
    def test_with_checkpointer_method(self):
        """测试 with_checkpointer 方法"""
        from src.agents.config import AgentConfig
        mock_checkpointer = MagicMock()
        config = AgentConfig().with_checkpointer(mock_checkpointer)
        assert config.checkpointer is mock_checkpointer
    
    def test_with_store_method(self):
        """测试 with_store 方法"""
        from src.agents.config import AgentConfig
        mock_store = MagicMock()
        config = AgentConfig().with_store(mock_store)
        assert config.store is mock_store
    
    def test_to_dict_includes_memory_fields(self):
        """测试 to_dict 包含记忆字段"""
        from src.agents.config import AgentConfig
        config = AgentConfig(checkpointer="cp", store="st")
        d = config.to_dict()
        assert 'checkpointer' in d
        assert 'store' in d


class TestSessionManager:
    """测试 SessionManager 会话管理"""
    
    def test_create_session(self):
        """测试创建会话"""
        from src.memory import SessionManager
        sm = SessionManager()
        session = sm.create_session("test_client")
        
        assert session.id is not None
        assert session.client_id == "test_client"
        assert session.created_at is not None
    
    def test_get_session(self):
        """测试获取会话"""
        from src.memory import SessionManager
        sm = SessionManager()
        session = sm.create_session("test_client")
        
        retrieved = sm.get_session(session.id)
        assert retrieved is not None
        assert retrieved.id == session.id
    
    def test_get_or_create_session_same_client(self):
        """测试同一 client_id 获取相同会话"""
        from src.memory import SessionManager
        sm = SessionManager()
        
        s1 = sm.get_or_create_session("client_001")
        s2 = sm.get_or_create_session("client_001")
        
        assert s1.id == s2.id
    
    def test_get_or_create_session_different_client(self):
        """测试不同 client_id 创建不同会话"""
        from src.memory import SessionManager
        sm = SessionManager()
        
        s1 = sm.get_or_create_session("client_001")
        s2 = sm.get_or_create_session("client_002")
        
        assert s1.id != s2.id
    
    def test_generate_thread_id_with_conversation(self):
        """测试生成 thread_id（带 conversation_id）"""
        from src.memory import SessionManager
        sm = SessionManager()
        
        thread_id = sm.generate_thread_id("dingtalk_123", "session_001")
        assert thread_id == "dingtalk_123_session_001"
    
    def test_generate_thread_id_without_conversation(self):
        """测试生成 thread_id（无 conversation_id）"""
        from src.memory import SessionManager
        sm = SessionManager()
        
        thread_id = sm.generate_thread_id("dingtalk_123")
        assert thread_id == "dingtalk_123_default"
    
    def test_update_activity(self):
        """测试更新会话活跃时间"""
        from src.memory import SessionManager
        sm = SessionManager()
        
        session = sm.create_session("test_client")
        old_time = session.last_active
        
        # 稍微等待以确保时间变化
        import time
        time.sleep(0.01)
        
        sm.update_activity(session.id)
        
        assert session.last_active > old_time
    
    def test_delete_session(self):
        """测试删除会话"""
        from src.memory import SessionManager
        sm = SessionManager()
        
        session = sm.create_session("test_client")
        sm.delete_session(session.id)
        
        assert sm.get_session(session.id) is None


class TestServiceMemoryIntegration:
    """测试 Service 层的短期记忆集成"""
    
    def test_service_has_session_manager(self):
        """测试 Service 有 session_manager"""
        from src.app.config import Config
        from src.app.service import Service
        from unittest.mock import MagicMock
        
        # Mock Config
        mock_config = MagicMock(spec=Config)
        mock_config.service_config = {"timeout": 60.0}
        mock_config.agent_config = {"system_prompt": "test"}
        
        with patch('src.app.service.get_agent_func'):
            service = Service(mock_config)
            
            assert hasattr(service, '_session_manager')
            assert service._session_manager is not None
    
    def test_service_has_checkpointer(self):
        """测试 Service 有 checkpointer"""
        from src.app.config import Config
        from src.app.service import Service
        from unittest.mock import MagicMock
        
        mock_config = MagicMock(spec=Config)
        mock_config.service_config = {"timeout": 60.0}
        mock_config.agent_config = {"system_prompt": "test"}
        
        with patch('src.app.service.get_agent_func'):
            service = Service(mock_config)
            
            assert hasattr(service, '_checkpointer')
            assert service._checkpointer is not None
    
    def test_extract_session_id_from_string(self):
        """测试从字符串提取 session_id"""
        from src.app.service import Service
        from src.app.config import Config
        from unittest.mock import MagicMock
        
        mock_config = MagicMock(spec=Config)
        mock_config.service_config = {"timeout": 60.0}
        mock_config.agent_config = {"system_prompt": "test"}
        
        with patch('src.app.service.get_agent_func'):
            service = Service(mock_config)
            
            # 字符串输入应返回 "default"
            session_id = service._get_or_create_session_id("hello")
            assert session_id == "default"
    
    def test_extract_session_id_from_dict(self):
        """测试从字典提取 session_id"""
        from src.app.service import Service
        from src.app.config import Config
        from unittest.mock import MagicMock
        
        mock_config = MagicMock(spec=Config)
        mock_config.service_config = {"timeout": 60.0}
        mock_config.agent_config = {"system_prompt": "test"}
        
        with patch('src.app.service.get_agent_func'):
            service = Service(mock_config)
            
            # 带 conversation_id
            session_id = service._get_or_create_session_id({
                "client_id": "dingtalk_123",
                "conversation_id": "session_001"
            })
            assert session_id == "dingtalk_123_session_001"
            
            # 不带 conversation_id
            session_id = service._get_or_create_session_id({
                "client_id": "dingtalk_456"
            })
            assert session_id == "dingtalk_456_default"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
