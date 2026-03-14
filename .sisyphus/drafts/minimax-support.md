# Draft: MiniMax模型支持实现计划

## 需求确认 (已确认)

用户要求：
1. 分析现有代码中模型集成的架构与接口规范
2. 实现Minimax模型的适配器模块，确保与Anthropic端点风格兼容
3. 配置模型路由与初始化逻辑，正确读取MINIMAX_API_KEY环境变量
4. 添加必要的错误处理与日志记录
5. 编写单元测试验证Minimax模型的功能完整性与兼容性

## 项目现有架构分析

### 核心文件结构
- `src/minerbot/config.py` - 配置管理，使用AppConfig类
- `src/minerbot/agent/factory.py` - Agent工厂，使用langchain-anthropic
- `src/minerbot/types.py` - 类型定义
- `src/minerbot/exceptions.py` - 异常类

### 现有集成模式
1. 使用`ChatAnthropic`作为模型客户端
2. 通过`create_deep_agent`创建agent
3. 配置通过环境变量读取

### 测试框架
- pytest
- 测试文件位于tests/目录

## 技术方案 (已确认)

### MiniMax API配置
- 基础URL: https://api.minimaxi.com/anthropic
- API Key: MINIMAX_API_KEY (已配置在.env)
- 优先级: MiniMax优先

### 实现方案
由于MiniMax兼容Anthropic端点风格，可以创建一个自定义的LangChain客户端来支持。
