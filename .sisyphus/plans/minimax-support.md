# MiniMax模型支持实现计划

## TL;DR

> **快速摘要**：在MinerBot项目中添加MiniMax模型支持，通过扩展配置和模型工厂函数实现与Anthropic端点风格兼容的MiniMax API集成。

> **交付成果**：
> - 扩展的AppConfig配置类（支持MINIMAX_API_KEY和MINIMAX_BASE_URL）
> - 修改后的Agent工厂（使用ChatAnthropic+base_url支持MiniMax）
> - 集成测试用例

> **预计工作量**：短
> **并行执行**：是 - 3个wave，6个任务
> **关键路径**：Task 1 → Task 2 → Task 3 → Task 6

---

## 上下文

### 原始请求
基于现有项目源码，分析并实现对Minimax模型的支持。已知Minimax模型兼容Anthropic端点风格，其基础URL为https://api.minimaxi.com/anthropic，且.env环境变量文件中已配置MINIMAX_API_KEY。

### 访谈总结
**关键讨论**：
- MiniMax API端点已确认为: `https://api.minimaxi.com/anthropic`
- 模型优先级: MiniMax优先（如果MINIMAX_API_KEY存在则使用，否则回退到Anthropic）
- 测试策略: 集成测试（真实API调用）

**研究结果**：
- MiniMax提供与Anthropic兼容的API
- 支持的模型: MiniMax-M2.5, MiniMax-M2.1等
- 上下文窗口: 128K tokens

### Metis审查
**识别的差距**（已解决）：
- 需要创建模型工厂函数避免代码重复
- 需要更新.env.example配置文件
- 需要确保向后兼容性

---

## 工作目标

### 核心目标
在MinerBot项目中实现MiniMax模型支持，使其能够：
1. 通过MINIMAX_API_KEY环境变量进行身份验证
2. 使用兼容Anthropic风格的端点进行API调用
3. 在MiniMax不可用时优雅地回退到Anthropic

### 具体交付物
- 修改后的配置类（src/minerbot/config.py）
- 模型工厂模块（src/minerbot/agent/models.py）
- 更新后的Agent工厂（src/minerbot/agent/factory.py）
- 集成测试文件（tests/test_minimax_integration.py）

### 完成定义
- [ ] MINIMAX_API_KEY可以从环境变量正确读取
- [ ] Agent可以使用MiniMax模型创建
- [ ] 当MINIMAX_API_KEY不存在时回退到Anthropic
- [ ] 集成测试验证完整流程

### 必须有
- MiniMax API集成
- 环境变量配置支持
- 错误处理与日志
- 向后兼容（现有Anthropic用户无需修改）

### 必须没有（Guardrails）
- 不添加其他模型支持（OpenAI/Gemini等）
- 不添加成本追踪功能
- 不修改CLI界面

---

## 验证策略

### 测试决策
- **基础设施存在**: 是
- **自动化测试**: 是 - 集成测试
- **框架**: pytest
- **测试方法**: 真实API调用测试

### QA策略
每个任务必须包含agent执行的QA场景。

---

## 执行策略

### 并行执行Wave

```
Wave 1 (立即开始 - 配置):
├── Task 1: 扩展AppConfig添加MiniMax配置字段
└── Task 2: 更新.env.example配置文件

Wave 2 (Wave 1后 - 核心模块):
├── Task 3: 修改Agent工厂支持模型路由（使用ChatAnthropic+base_url）
├── Task 4: 添加错误处理和日志记录
└── Task 5: 编写MiniMax集成测试

Wave 3 (Wave 2后 - 验证):
└── Task 6: 运行测试并验证
```

### 依赖矩阵
- Task 1: — — 2, 3
- Task 2: 1 — 3
- Task 3: 2 — 4, 5
- Task 4: 3 — 5
- Task 5: 4 — 6
- Task 6: 5 — —

---

## TODOs

- [x] 1. 扩展AppConfig添加MiniMax配置字段

  **What to do**:
  - 在config.py中添加minimax_api_key、minimax_base_url、minimax_model等字段
  - 修改from_env()方法读取MINIMAX_API_KEY等环境变量
  - 修改validate()方法支持MiniMax优先级验证
  - 添加model_provider字段用于控制使用哪个模型

  **Must NOT do**:
  - 不删除现有的Anthropic相关配置

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 简单的配置扩展任务
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Tasks 3, 4, 5
  - **Blocked By**: None

  **References**:
  - `src/minerbot/config.py:8-34` - 现有AppConfig结构

  **Acceptance Criteria**:
  - [ ] 1. AppConfig包含minimax_api_key字段
  - [ ] 1. AppConfig.from_env()读取MINIMAX_API_KEY
  - [ ] 1. validate()检查至少一个API key存在

  **QA Scenarios**:

  Scenario: 配置正确读取MiniMax API Key
    Tool: Bash
    Preconditions: .env文件包含MINIMAX_API_KEY
    Steps:
      1. 设置环境变量 MINIMAX_API_KEY=test-key
      2. 运行 Python: from minerbot.config import AppConfig; config = AppConfig.from_env()
      3. 验证 config.minimax_api_key == "test-key"
    Expected Result: 成功读取API key
    Evidence: .sisyphus/evidence/task-1-config-read.txt

  Scenario: 验证至少需要一个API key
    Tool: Bash
    Preconditions: 无API key环境变量
    Steps:
      1. 清除所有API key环境变量
      2. 运行验证并捕获异常
    Expected Result: 抛出ValueError
    Evidence: .sisyphus/evidence/task-1-validation.txt

  **Commit**: YES
  - Message: feat(config): add MiniMax configuration fields
  - Files: src/minerbot/config.py
  - Pre-commit: uv run pytest tests/test_config.py

---

- [x] 2. 更新.env.example配置文件

  **What to do**:
  - 在.env.example中添加MiniMax相关配置项
  - 保持现有Anthropic配置

  **Must NOT do**:
  - 不删除现有配置项

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 简单的配置文档更新
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `.env.example` - 现有配置模板

  **Acceptance Criteria**:
  - [ ] .env.example包含MINIMAX_API_KEY
  - [ ] .env.example包含MINIMAX_BASE_URL

  **QA Scenarios**:

  Scenario: 验证配置文件包含MiniMax项
    Tool: Bash
    Preconditions: N/A
    Steps:
      1. 读取.env.example
      2. 检查包含MINIMAX_API_KEY
    Expected Result: 文件包含所需配置项
    Evidence: .sisyphus/evidence/task-2-env-example.txt

  **Commit**: YES
  - Message: docs: update .env.example with MiniMax config
  - Files: .env.example

---

- [x] 3. 修改Agent工厂支持模型路由

  **What to do**:
  - 在config.py中添加minimax_base_url字段（默认: https://api.minimaxi.com/anthropic）
  - 修改agent/factory.py中的create_agent函数
  - 当minimax_api_key存在时，使用ChatAnthropic并设置base_url参数
  - 实现逻辑：如果配置了MINIMAX_API_KEY则使用MiniMax端点，否则回退到Anthropic

  示例代码结构:
  ```python
  from langchain_anthropic import ChatAnthropic
  
  def create_agent(config: AppConfig, ...):
      if config.minimax_api_key:
          model = ChatAnthropic(
              model_name=config.minimax_model,
              base_url=config.minimax_base_url,  # https://api.minimaxi.com/anthropic
              api_key=config.minimax_api_key,
              ...
          )
      else:
          model = ChatAnthropic(...)
  ```

  **Must NOT do**:
  - 不删除现有的Anthropic回退逻辑
  - 不创建新的客户端类

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要修改现有工厂函数和配置
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 4, 5
  - **Blocked By**: Task 2

  **References**:
  - `src/minerbot/config.py:8-34` - 现有AppConfig结构
  - `src/minerbot/agent/factory.py:32-36` - 现有ChatAnthropic实例化

  **Acceptance Criteria**:
  - [ ] factory.py支持base_url参数
  - [ ] 当MINIMAX_API_KEY存在时使用MiniMax端点
  - [ ] 回退到Anthropic逻辑正常工作

  **QA Scenarios**:

  Scenario: 使用MiniMax端点创建Agent
    Tool: Bash
    Preconditions: MINIMAX_API_KEY已设置
    Steps:
      1. 设置环境变量 MINIMAX_API_KEY=test-key
      2. 导入并调用create_agent_with_session
      3. 验证模型使用了正确的base_url
    Expected Result: Agent使用MiniMax端点
    Evidence: .sisyphus/evidence/task-3-minimax-agent.txt

  **Commit**: YES
  - Message: feat(factory): add MiniMax routing in agent creation
  - Files: src/minerbot/agent/factory.py

---

- [x] 4. 添加错误处理和日志记录

  **What to do**:
  - 在factory.py中添加异常处理
  - 添加适当的日志记录
  - 处理API连接错误

  **Must NOT do**:
  - 不添加过度复杂的错误处理

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 添加错误处理是常规任务
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 5
  - **Blocked By**: Task 3

  **References**:
  - `src/minerbot/exceptions.py` - 现有异常类
  - `src/minerbot/logging_config.py` - 日志配置

  **Acceptance Criteria**:
  - [ ] API错误被正确捕获
  - [ ] 日志记录正常工作
  - [ ] 错误消息清晰有用

  **QA Scenarios**:

  Scenario: 无效API key时错误处理
    Tool: Bash
    Preconditions: 使用无效API key
    Steps:
      1. 设置无效的MINIMAX_API_KEY
      2. 尝试创建Agent
      3. 验证错误被正确捕获
    Expected Result: 抛出明确的错误
    Evidence: .sisyphus/evidence/task-4-error-handling.txt

  **Commit**: YES
  - Message: feat(error): add error handling for MiniMax
  - Files: src/minerbot/agent/factory.py

---

- [x] 5. 编写MiniMax集成测试

  **What to do**:
  - 创建tests/test_minimax_integration.py
  - 测试完整的Agent创建和对话流程
  - 测试回退逻辑

  **Must NOT do**:
  - 不修改现有测试文件

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 集成测试需要完整的系统交互
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 6
  - **Blocked By**: Task 4

  **References**:
  - `tests/test_config.py` - 现有测试模式

  **Acceptance Criteria**:
  - [ ] 集成测试文件创建
  - [ ] 测试通过（当API可用时）

  **QA Scenarios**:

  Scenario: 完整集成测试
    Tool: Bash
    Preconditions: MINIMAX_API_KEY可用
    Steps:
      1. 运行 pytest tests/test_minimax_integration.py
    Expected Result: 测试通过或跳过（如果API不可用）
    Evidence: .sisyphus/evidence/task-5-integration-test.txt

  **Commit**: YES
  - Message: test: add MiniMax integration tests
  - Files: tests/test_minimax_integration.py

---

- [x] 6. 运行测试并验证

  **What to do**:
  - 运行所有相关测试
  - 验证MiniMax功能正常工作

  **Must NOT do**:
  - 不修改通过的测试

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 验证任务
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: Task 5

  **Acceptance Criteria**:
  - [ ] pytest运行成功
  - [ ] 所有MiniMax相关测试通过

  **QA Scenarios**:

  Scenario: 运行完整测试套件
    Tool: Bash
    Preconditions: 所有代码已实现
    Steps:
      1. 运行 pytest tests/
    Expected Result: 所有测试通过
    Evidence: .sisyphus/evidence/task-6-test-run.txt

  **Commit**: YES
  - Message: test: verify MiniMax integration
  - Files: N/A

---

## 最终验证Wave

> 2个review agents运行并行。都必须批准。

- [x] F1. **代码质量审查** — `unspecified-high`
  运行tsc/类型检查和lint。审查所有更改的文件。检查：导入未使用，代码风格一致，错误处理适当。
  Output: `Lint [PASS/FAIL] | Tests [N pass/N fail] | VERDICT: APPROVE/REJECT`

- [x] F2. **功能完整性检查** — `quick`
  验证所有任务完成。检查配置文件、客户端、工厂函数、测试文件存在。
  Output: `Files [N/N] | VERDICT: APPROVE/REJECT`

---

## 提交策略

- **1**: `feat(config): add MiniMax configuration fields` — src/minerbot/config.py
- **2**: `docs: update .env.example with MiniMax config` — .env.example
- **3**: `feat(factory): add MiniMax routing in agent creation` — src/minerbot/agent/factory.py
- **4**: `feat(error): add error handling for MiniMax` — src/minerbot/agent/factory.py
- **5**: `test: add MiniMax integration tests` — tests/test_minimax_integration.py
- **6**: `test: verify MiniMax integration` — N/A

---

## 成功标准

### 验证命令
```bash
uv run pytest tests/test_minimax_integration.py -v
```

### 最终检查清单
- [ ] 所有"必须有"已实现
- [ ] 所有测试通过
- [ ] MiniMax模型可以正常对话
- [ ] 向后兼容性保持
