# LLM 工厂模式实现计划

## TL;DR

> **快速摘要**：根据设计文档实现 LLM 工厂模式，支持通过 YAML 配置文件和环境变量管理多提供商 LLM 实例创建，包括 Anthropic、OpenAI、MiniMax、Google 四个提供商。
> 
> **交付物**：
> - LLM 模块目录结构 (src/minerbot/llm/)
> - 配置模型、异常定义、提供商基类
> - 四个提供商实现类
> - 工厂类核心实现
> - 修复 super_agent.py 硬编码 API Key 安全问题
> 
> **预估工作量**：中等
> **并行执行**：是 - 多波次
> **关键路径**：创建目录结构 → 实现核心类 → 实现提供商 → 改造 super_agent

---

## 背景

### 原始需求
根据 `docs/llm-factory-design.md` 实现 LLM 工厂模式，支持通过配置文件设置模型参数并根据模型名称自动创建对应实例。

### 讨论总结
**关键决策**：
- 项目背景：minerbot - 基于 LangChain + DeepAgents 的 CLI AI 助手
- 包含 4 个提供商：Anthropic, OpenAI, MiniMax, Google
- 用户确认：不包含单元测试，但需要修复硬编码 API Key 问题
- 使用 YAML 配置文件 + 环境变量

**研究结果**：
- pyproject.toml 已有 langchain-openai>=1.1.10
- 需要添加 langchain-google-genai 用于 Google 提供商
- super_agent.py 第 24-28 行存在硬编码 API Key（严重安全问题）

### Metis 评审
**已解决的问题**：
- 测试代码从计划中移除（用户确认不需要）
- 添加了安全验证：硬编码 API Key 必须被移除
- 明确了错误消息规范
- 确认了范围边界

---

## 工作目标

### 核心目标
实现 LLM 工厂模式，支持通过配置文件和环境变量管理多提供商 LLM 实例创建。

### 具体交付物
- `src/minerbot/llm/__init__.py` - 导出工厂函数和配置类
- `src/minerbot/llm/config.py` - LLM 配置模型（Pydantic）
- `src/minerbot/llm/factory.py` - 工厂模式核心实现
- `src/minerbot/llm/exceptions.py` - 异常定义
- `src/minerbot/llm/providers/__init__.py` - 提供商目录
- `src/minerbot/llm/providers/base.py` - BaseLLMProvider 抽象基类
- `src/minerbot/llm/providers/anthropic.py` - Anthropic 提供商
- `src/minerbot/llm/providers/openai.py` - OpenAI 提供商
- `src/minerbot/llm/providers/google.py` - Google 提供商
- `src/minerbot/llm/providers/minimax.py` - MiniMax 提供商
- 更新 `src/agent/super_agent.py` - 使用工厂模式并移除硬编码 API Key
- 更新 `pyproject.toml` - 添加 langchain-google-genai 依赖
- 更新 `config/llm.yaml` - 如需要

### 完成定义
- [ ] 所有模块文件创建完成，语法正确
- [ ] super_agent.py 中无硬编码 API Key
- [ ] LLMFactory 可以从配置文件加载配置
- [ ] LLMFactory.create_llm_instance() 可以成功创建各提供商实例
- [ ] 错误消息清晰，包含支持的提供商列表

### 必须包含
- 四个提供商实现（Anthropic, OpenAI, MiniMax, Google）
- YAML 配置文件加载功能
- 环境变量集成
- 清晰的错误消息

### 禁止包含（边界）
- 单元测试代码（用户确认不需要）
- 数据库层修改
- Agent 逻辑修改（除了使用工厂）
- 新增环境变量（仅使用 .env.example 中已有的）
- CLI 入口点修改

---

## 验证策略

### 测试决策
- **基础设施存在**：是（pytest 作为 dev 依赖）
- **自动化测试**：否（用户确认不需要）
- **代理执行 QA**：每个任务完成后使用 `python -c` 验证模块可导入

### QA 策略
每个任务完成后必须运行验证：
- Python 模块导入测试
- 配置文件加载测试
- 错误场景验证

---

## 执行策略

### 并行执行波次

```
Wave 1（立即开始 - 基础结构）：
├── Task 1: 创建 src/minerbot/llm/ 目录结构 [quick]
├── Task 2: 实现 exceptions.py 异常定义 [quick]
├── Task 3: 实现 config.py 配置模型 [quick]
└── Task 4: 实现 providers/base.py 基类 [quick]

Wave 2（Wave 1 后 - 提供商实现，最大并行）：
├── Task 5: 实现 anthropic.py 提供商 [quick]
├── Task 6: 实现 openai.py 提供商 [quick]
├── Task 7: 实现 minimax.py 提供商 [quick]
├── Task 8: 实现 google.py 提供商 [quick]
└── Task 9: 实现 providers/__init__.py [quick]

Wave 3（Wave 2 后 - 核心工厂）：
├── Task 10: 实现 factory.py 工厂类 [quick]
└── Task 11: 实现 llm/__init__.py 导出模块 [quick]

Wave 4（Wave 3 后 - 集成与修复）：
├── Task 12: 更新 pyproject.toml 添加 Google 依赖 [quick]
├── Task 13: 改造 super_agent.py 使用工厂并修复硬编码 API Key [quick]
└── Task 14: 更新 config/llm.yaml 配置 [quick]

Wave 5（Wave 4 后 - 验证）：
├── Task 15: 整体集成验证 [quick]
└── Task 16: 代码清理与验证 [quick]
```

### 依赖矩阵
- **1-4**: — — 5-11, 1
- **5-9**: 4 — 10, 2
- **10-11**: 5, 6, 7, 8, 9 — 12-14, 3
- **12-14**: 10, 11 — 15, 3
- **15-16**: 12, 13, 14 — —

---

## 任务清单

> 每个任务必须包含：推荐代理配置 + 并行信息 + QA 场景

- [x] 1. 创建 src/minerbot/llm/ 目录结构

  **工作内容**：
  - 创建目录 src/minerbot/llm/
  - 创建目录 src/minerbot/llm/providers/
  - 创建空 __init__.py 文件

  **禁止包含**：
  - 不创建测试文件

  **推荐代理配置**：
  - 类别：quick
  - 原因：简单目录结构创建
  - 技能：不需要特殊技能

  **并行化**：
  - 可并行运行：是
  - 并行组：Wave 1（与任务 2, 3, 4）
  - 阻塞：无
  - 被阻塞：无

  **引用**：
  - src/minerbot/agent/ - 参考现有目录结构

  **验收标准**：
  - [ ] 目录 src/minerbot/llm/ 存在
  - [ ] 目录 src/minerbot/llm/providers/ 存在

  **QA 场景**：

  场景：验证目录创建成功
    工具：Bash
    步骤：
      1. `ls -la src/minerbot/llm/`
      2. `ls -la src/minerbot/llm/providers/`
    预期结果：目录存在且包含 __init__.py 文件
    证据：.sisyphus/evidence/task-1-dir-structure.{ext}

- [x] 2. 实现 exceptions.py 异常定义

  **工作内容**：
  - 创建 LLMFactoryError 基类
  - 创建 UnsupportedProviderError
  - 创建 InvalidConfigError
  - 创建 ModelNotSupportedError

  **禁止包含**：
  - 不添加业务相关异常

  **推荐代理配置**：
  - 类别：quick
  - 原因：简单异常类定义

  **并行化**：
  - 可并行运行：是
  - 并行组：Wave 1（与任务 1, 3, 4）
  - 阻塞：无
  - 被阻塞：无

  **引用**：
  - docs/llm-factory-design.md:132-149 - 设计文档中的异常定义

  **验收标准**：
  - [ ] 文件 src/minerbot/llm/exceptions.py 存在
  - [ ] 包含 4 个异常类
  - [ ] python -c "from minerbot.llm.exceptions import *" 成功

  **QA 场景**：

  场景：验证异常模块可导入
    工具：Bash
    步骤：
      1. `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from minerbot.llm.exceptions import LLMFactoryError, UnsupportedProviderError, InvalidConfigError, ModelNotSupportedError; print('OK')"`
    预期结果：输出 OK
    证据：.sisyphus/evidence/task-2-exceptions-import.{ext}

- [x] 3. 实现 config.py 配置模型

  **工作内容**：
  - 实现 LLMConfig 类（Pydantic BaseModel）
  - model_name 字段验证（格式：provider/model-name）
  - temperature 范围验证（0.0-2.0）
  - get_provider() 方法
  - get_model() 方法
  - get_api_key() 方法（支持 $ENV_VAR 格式）

  **禁止包含**：
  - 不实现实际 LLM 创建逻辑

  **推荐代理配置**：
  - 类别：quick
  - 原因：Pydantic 模型定义

  **并行化**：
  - 可并行运行：是
  - 并行组：Wave 1（与任务 1, 2, 4）
  - 阻塞：无
  - 被阻塞：任务 10（工厂类需要配置模型）

  **引用**：
  - docs/llm-factory-design.md:151-207 - 设计文档中的配置模型

  **验收标准**：
  - [ ] 文件 src/minerbot/llm/config.py 存在
  - [ ] LLMConfig 可导入
  - [ ] model_name 格式验证有效
  - [ ] temperature 范围验证有效

  **QA 场景**：

  场景：验证配置模型基本功能
    工具：Bash
    步骤：
      1. `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from minerbot.llm.config import LLMConfig; c = LLMConfig(model_name='test/model'); print(c.get_provider(), c.get_model())"`
    预期结果：输出 "test model"
    证据：.sisyphus/evidence/task-3-config-basic.{ext}

  场景：验证无效 model_name 格式
    工具：Bash
    步骤：
      1. `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from minerbot.llm.config import LLMConfig; LLMConfig(model_name='invalid')" 2>&1`
    预期结果：抛出 ValueError 包含 "格式错误"
    证据：.sisyphus/evidence/task-3-config-invalid.{ext}

- [x] 4. 实现 providers/base.py 基类

  **工作内容**：
  - 实现 BaseLLMProvider 抽象基类
  - provider_name 类属性
  - supported_models 列表
  - default_env_var
  - default_base_url
  - create_llm() 抽象方法
  - is_model_supported() 方法

  **禁止包含**：
  - 不实现具体提供商

  **推荐代理配置**：
  - 类别：quick
  - 原因：抽象基类定义

  **并行化**：
  - 可并行运行：是
  - 并行组：Wave 1（与任务 1, 2, 3）
  - 阻塞：无
  - 被阻塞：任务 5-8（提供商实现需要基类）

  **引用**：
  - docs/llm-factory-design.md:209-256 - 设计文档中的基类定义
  - src/minerbot/llm/config.py - 配置模型

  **验收标准**：
  - [ ] 文件 src/minerbot/llm/providers/base.py 存在
  - [ ] BaseLLMProvider 可导入
  - [ ] 抽象方法签名正确

  **QA 场景**：

  场景：验证基类可导入
    工具：Bash
    步骤：
      1. `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from minerbot.llm.providers.base import BaseLLMProvider; print('OK')"`
    预期结果：输出 OK
    证据：.sisyphus/evidence/task-4-base-import.{ext}

- [x] 5. 实现 anthropic.py 提供商
- [x] 6. 实现 openai.py 提供商
- [x] 7. 实现 minimax.py 提供商
- [x] 8. 实现 google.py 提供商
- [x] 9. 实现 providers/__init__.py

  **工作内容**：
  - 导出所有提供商类

  **推荐代理配置**：
  - 类别：quick

  **并行化**：
  - 可并行运行：是
  - 并行组：Wave 2
  - 阻塞：任务 5-8
  - 被阻塞：无

  **验收标准**：
  - [ ] 可导入所有提供商

  **QA 场景**：

  场景：验证导出
    工具：Bash
    步骤：
      1. `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from minerbot.llm.providers import AnthropicProvider, OpenAIProvider, MiniMaxProvider, GoogleProvider; print('OK')"`
    预期结果：输出 OK
    证据：.sisyphus/evidence/task-9-providers-init.{ext}

- [x] 10. 实现 factory.py 工厂类

  **工作内容**：
  - 实现 LLMFactory 类
  - initialize() 类方法（注册默认提供商）
  - register_provider() 类方法
  - create_llm_instance() 类方法
  - get_supported_providers() 类方法
  - load_config() 类方法（YAML 加载）

  **禁止包含**：
  - 不修改现有 agent 逻辑

  **推荐代理配置**：
  - 类别：quick

  **并行化**：
  - 可并行运行：是
  - 并行组：Wave 3
  - 阻塞：任务 5-9
  - 被阻塞：任务 12-14

  **引用**：
  - docs/llm-factory-design.md:405-530 - 设计文档

  **验收标准**：
  - [ ] 文件存在且语法正确
  - [ ] LLMFactory 可导入
  - [ ] get_supported_providers() 返回 4 个提供商

  **QA 场景**：

  场景：验证工厂初始化
    工具：Bash
    步骤：
      1. `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from minerbot.llm.factory import LLMFactory; LLMFactory.initialize(); print(LLMFactory.get_supported_providers())"`
    预期结果：输出包含 anthropic, openai, minimax, google 的列表
    证据：.sisyphus/evidence/task-10-factory-init.{ext}

  场景：验证不支持的提供商错误消息
    工具：Bash
    步骤：
      1. `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from minerbot.llm.factory import LLMFactory, UnsupportedProviderError; LLMFactory.initialize(); LLMFactory.create_llm_instance('unknown/model')" 2>&1`
    预期结果：错误消息包含支持的提供商列表
    证据：.sisyphus/evidence/task-10-factory-error.{ext}

  场景：验证配置文件加载
    工具：Bash
    步骤：
      1. `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from minerbot.llm.factory import LLMFactory; cfg = LLMFactory.load_config('config/llm.yaml'); print(cfg)"`
    预期结果：输出配置字典
    证据：.sisyphus/evidence/task-10-factory-config.{ext}

- [x] 11. 实现 llm/__init__.py 导出模块

  **工作内容**：
  - 导出 LLMConfig, LLMFactory
  - 导出所有异常类

  **推荐代理配置**：
  - 类别：quick

  **并行化**：
  - 可并行运行：是
  - 并行组：Wave 3
  - 阻塞：任务 10
  - 被阻塞：无

  **验收标准**：
  - [ ] 可从 minerbot.llm 导入所有公共 API

  **QA 场景**：

  场景：验证公共 API 导出
    工具：Bash
    步骤：
      1. `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from minerbot.llm import LLMConfig, LLMFactory, LLMFactoryError, UnsupportedProviderError, InvalidConfigError, ModelNotSupportedError; print('OK')"`
    预期结果：输出 OK
    证据：.sisyphus/evidence/task-11-llm-init.{ext}

- [x] 12. 更新 pyproject.toml 添加 Google 依赖
- [x] 13. 改造 super_agent.py 使用工厂并修复硬编码 API Key
- [x] 14. 更新 config/llm.yaml 配置

  **工作内容**：
  - 检查现有配置文件
  - 如需要，进行小调整

  **推荐代理配置**：
  - 类别：quick

  **并行化**：
  - 可并行运行：是
  - 并行组：Wave 4
  - 阻塞：任务 10-11
  - 被阻塞：无

  **验收标准**：
  - [ ] 配置文件格式正确

  **QA 场景**：

  场景：验证配置文件可加载
    工具：Bash
    步骤：
      1. `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from minerbot.llm.factory import LLMFactory; LLMFactory.load_config('config/llm.yaml')"`
    预期结果：成功加载
    证据：.sisyphus/evidence/task-14-config.{ext}

- [x] 15. 整体集成验证

  **工作内容**：
  - 验证所有模块协同工作
  - 验证从配置文件创建 LLM 实例

  **推荐代理配置**：
  - 类别：quick

  **并行化**：
  - 可并行运行：是
  - 并行组：Wave 5
  - 阻塞：任务 12-14
  - 被阻塞：无

  **验收标准**：
  - [ ] 完整流程可运行

  **QA 场景**：

  场景：端到端集成测试
    工具：Bash
    步骤：
      1. `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "
from minerbot.llm.factory import LLMFactory
LLMFactory.initialize()
config = LLMFactory.load_config('config/llm.yaml')
print('Config loaded:', config.get('model_name'))
providers = LLMFactory.get_supported_providers()
print('Providers:', providers)
print('Integration OK')
"`
    预期结果：输出 Integration OK
    证据：.sisyphus/evidence/task-15-integration.{ext}

- [x] 16. 代码清理与验证

  **工作内容**：
  - 代码格式检查
  - 最终验证

  **推荐代理配置**：
  - 类别：quick

  **并行化**：
  - 可并行运行：是
  - 并行组：Wave 5
  - 阻塞：任务 15
  - 被阻塞：无

  **验收标准**：
  - [ ] 无语法错误
  - [ ] 所有模块可导入

  **QA 场景**：

  场景：最终验证
    工具：Bash
    步骤：
      1. `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "import minerbot.llm; import minerbot.llm.factory; import minerbot.llm.providers; print('All modules OK')"`
    预期结果：输出 All modules OK
    证据：.sisyphus/evidence/task-16-final.{ext}

---

## 最终验证波次

> 4 个审查代理并行运行

- [x] F1. **计划合规审计** — oracle
- [x] F2. **代码质量审查** — unspecified-high
- [x] F3. **手动 QA** — unspecified-high
- [x] F4. **范围忠诚度检查** — deep
  对于每个任务：读取"工作内容"，读取实际差异。验证 1:1。检测跨任务污染：任务 N 接触任务 M 的文件。标记未计入的变更。
  输出：任务 [N/N 合规] | 污染 [清洁/N 问题] | 未计入 [清洁/N 文件] | 结论

---

## 提交策略

- **1**: `feat(llm): 实现 LLM 工厂模式` — src/minerbot/llm/, src/agent/super_agent.py, pyproject.toml, config/llm.yaml

---

## 成功标准

### 验证命令
```bash
# 验证所有模块可导入
uv run python -c "from minerbot.llm import LLMConfig, LLMFactory"

# 验证工厂初始化
uv run python -c "from minerbot.llm.factory import LLMFactory; LLMFactory.initialize(); print(LLMFactory.get_supported_providers())"

# 验证配置文件加载
uv run python -c "from minerbot.llm.factory import LLMFactory; LLMFactory.load_config('config/llm.yaml')"

# 验证无硬编码密钥
grep -r "sk-cp-" src/minerbot/agent/super_agent.py  # 应无结果
```

### 最终检查清单
- [ ] 所有"必须包含"已实现
- [ ] 所有"禁止包含"已排除
- [ ] 无硬编码 API Key
- [ ] 所有模块可导入
- [ ] 配置文件可加载
