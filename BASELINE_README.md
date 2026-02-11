# CodeContests Baseline 修改总结

## 📋 修改概览

本次修改将 Self-collaboration-Code-Generation 源代码改造为适配 **CodeContests 数据集**和 **DeepSeek 模型**的 Baseline 版本。

---

## 🔧 修改的文件

### 1️⃣ `core/backend.py` - 劫持 LLM 调用

**修改目标：** 废弃原有的 OpenAI 调用，改用 `generate_code.py` 中的 `LLMClient`。

**主要改动：**
- ✅ 引入 `generate_code.build_llm`
- ✅ 初始化全局 LLM 客户端：`_GLOBAL_LLM`
- ✅ 重写 `call_chatgpt` 函数：
  - 忽略 `model` 参数，强制使用 `_GLOBAL_LLM`
  - 调用 `_GLOBAL_LLM.chat(messages, ...)`
  - 支持 `majority_at` 参数（多次采样）
- ✅ 自动统计 Token 使用量（通过 `_GLOBAL_LLM.total_tokens`）

**代码示例：**
```python
from generate_code import build_llm

_GLOBAL_LLM = build_llm("MODEL_C", temperature=0.3, max_tokens=1400)

def call_chatgpt(prompt, model='...', temperature=0., max_tokens=128, majority_at=None):
    num_completions = majority_at if majority_at is not None else 1
    completions = []
    for i in range(num_completions):
        response = _GLOBAL_LLM.chat(messages=prompt, temperature=temperature, max_tokens=max_tokens)
        completions.append(response)
    return completions
```

---

### 2️⃣ `roles/rule_descriptions_actc.py` - 适配 STDIO 提示词

**修改目标：** 将原版的函数生成提示词改造为支持 **标准输入输出** 的竞赛编程提示词。

**主要改动：**

#### 📝 ANALYST（需求分析师）
- 强调分析 **Input/Output 格式**
- 关注算法设计（贪心、动态规划、图搜索等）
- 识别边界条件和约束

#### 💻 PYTHON_DEVELOPER（Python 开发者）
- **最重要约束：**
  - 使用 `input()` 或 `sys.stdin.read()` 读取输入
  - 使用 `print()` 输出结果
  - 生成**完整的可执行脚本**（不是 `class Solution`）

#### 🧪 TESTER（测试员）
- **关键变化：**
  - 不再生成 Python 测试代码（如 `def check(candidate)`）
  - 改为生成 **up to 5 个简单的 Input/Output 文本对**
  - 格式要求：
    ```
    Input:
    <input_data>
    Output:
    <expected_output>
    ```

---

### 3️⃣ `main.py` - 核心逻辑注入

**修改目标：** 替换数据源为 CodeContests，并注入自定义执行逻辑。

**主要改动：**

#### 🔌 导入依赖
```python
from apps_eval.data import get_data
from apps_eval.executor import evaluate_case
from apps_eval.parallel_runner import eval_code
```

#### 🛠️ Monkey Patch（关键！）
定义 `custom_unsafe_execute(code, report)` 函数：
- 使用正则从 `report`（Tester 的输出）中提取 Input 和 Output
- 调用 `apps_eval.executor.evaluate_case(..., mode='stdio')` 运行代码
- 返回结果：
  - ✅ 成功：`"Code Test Passed."`
  - ❌ 失败：详细错误报告（包含 Input, Expected, Actual Output, Error）

**注入方式：**
```python
import session as session_module
session_module.unsafe_execute = custom_unsafe_execute
```

#### 📊 主流程
1. **加载数据集：** `get_data('code_contests')`
2. **遍历数据集：**
   - 初始化 `Session`，`requirement=problem_statement`
   - 注入 `custom_unsafe_execute`
   - 运行 `session.run_session()`
   - 收集生成的代码
3. **最终评估：**
   - 调用 `apps_eval.parallel_runner.eval_code` 对所有结果进行评测
   - 计算 **Pass@1**, **Time Cost**, **Total Token Usage**
4. **保存结果：** 输出到 `baseline_results.json`

---

## 🚀 使用方法

### 前置条件
1. 确保已设置环境变量：
   ```bash
   export DEEPSEEK_API_KEY=your_api_key_here
   ```

2. 确保数据集存在：
   ```
   Datasets/code_contests.jsonl
   ```

### 运行 Baseline
```bash
cd Self-collaboration-Code-Generation-main
python main.py
```

### 输出示例
```
==============================================================
CodeContests Baseline - Self-collaboration-Code-Generation
==============================================================

[1/4] 加载 CodeContests 数据集...
✅ 加载完成，共 100 个问题

[2/4] 开始生成代码...
==============================================================
处理问题 1/100: problem_001
==============================================================
✅ 代码生成成功

...

==============================================================
[3/4] 最终评估所有生成结果...
==============================================================

==============================================================
[4/4] 最终结果
==============================================================
📊 Pass@1: 45.00% (45/100)
⏱️  总耗时: 3456.78 秒
🔢 总 Token 使用量: 1234567
==============================================================

✅ 结果已保存到: baseline_results.json
```

---

## 📂 输出文件

### `baseline_results.json`
包含以下信息：
```json
{
  "summary": {
    "pass_at_1": 45.0,
    "passed": 45,
    "total": 100,
    "time_cost": 3456.78,
    "total_tokens": 1234567
  },
  "results": [
    {
      "instance_id": "problem_001",
      "code": "...",
      "pass": true,
      "test_results": [...]
    },
    ...
  ]
}
```

---

## ✅ 验证清单

- [x] `core/backend.py` 成功引入 LLMClient
- [x] `roles/rule_descriptions_actc.py` 适配 STDIO 提示词
- [x] `main.py` 实现 Monkey Patch
- [x] 数据集加载正常
- [x] 执行逻辑正确（使用 `apps_eval.executor`）
- [x] Token 统计功能正常
- [x] 最终评估使用 `parallel_runner.eval_code`

---

## 🎯 关键特性

1. **无需重写整个流程：** 仅修改 3 个文件，保留原有架构
2. **模型适配：** 无缝接入 DeepSeek API
3. **数据集适配：** 支持 CodeContests 标准输入输出格式
4. **Token 统计：** 自动跟踪 API 使用量
5. **详细日志：** 每个问题都有清晰的处理状态输出

---

## 📌 注意事项

1. **API Key：** 请确保 `DEEPSEEK_API_KEY` 环境变量已设置
2. **数据集路径：** 默认为 `Datasets/code_contests.jsonl`，可根据需要调整
3. **超时设置：** 默认每个测试用例超时 10 秒，可在 `evaluate_case` 中调整
4. **最大轮数：** 默认 `max_round=2`，可在 `main.py` 中修改

---

## 🐛 常见问题

**Q: 提示 "Missing API key env var: DEEPSEEK_API_KEY"**  
A: 运行前请设置环境变量：
```bash
export DEEPSEEK_API_KEY=sk-your-key-here
```

**Q: 生成的代码总是失败**  
A: 检查 Tester 的输出格式是否符合 `Input:\n...\nOutput:\n...` 规范。

**Q: Token 统计不准确**  
A: 确保 `generate_code.py` 中的 `LLMClient.total_tokens` 正确累加。

---

## 📞 联系信息

如有问题，请检查：
1. 所有依赖是否安装完整
2. 数据集格式是否正确
3. API Key 是否有效

---

**祝您实验顺利！🎉**
