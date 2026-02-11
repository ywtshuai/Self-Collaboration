# 🔍 问题排查与解决方案

## 📋 目录

1. [评估阶段常见问题](#评估阶段常见问题)
2. [代码生成失败原因](#代码生成失败原因)
3. [诊断工具](#诊断工具)
4. [解决方案汇总](#解决方案汇总)

---

## 评估阶段常见问题

### 问题 1: Windows 多进程错误 ⭐⭐⭐⭐⭐

**现象:**
```
KeyboardInterrupt
或
PicklingError
或
进程卡死
```

**原因:**
- Windows 使用 `spawn` 方式创建进程（不是 `fork`）
- 每个子进程需要重新导入所有模块
- 过多进程会导致资源竞争

**解决方案:**
```bash
# 方案 1: 使用顺序模式
python quick_eval.py  # 使用新创建的顺序评估脚本

# 方案 2: 减少进程数
python recover_and_eval.py --workers 2

# 方案 3: 强制顺序模式
python recover_and_eval.py --sequential
```

---

### 问题 2: 代码执行超时 ⭐⭐⭐⭐

**现象:**
```
EvalResult(status=TLE, time_cost=10.0s, ...)
```

**原因:**
- 生成的代码效率低（时间复杂度高）
- 测试用例数据量大
- 死循环或递归过深

**影响:**
- 单个超时不影响其他测试
- 但会降低 Pass@1 分数

**调整方案:**
修改 `quick_eval.py` 或 `recover_and_eval.py` 中的超时设置：

```python
# 找到这一行
result = evaluate_case(..., timeout=10.0)

# 改为更长的超时时间
result = evaluate_case(..., timeout=20.0)  # 20 秒
```

---

### 问题 3: 代码包含禁用操作 ⭐⭐⭐

**现象:**
```
EvalResult(status=FORBIDDEN, stderr="[ForbiddenImport]...")
```

**原因:**
- 代码尝试导入被禁止的模块（如 `os`, `subprocess`）
- 使用了被禁止的函数（如 `exec`, `eval`）

**检查位置:**
`apps_eval/checker.py` 中的禁用列表：

```python
FORBIDDEN_MODULES = {
    # "os", "sys", "subprocess", "socket",
    # 默认是空的，可以根据需要添加
}

FORBIDDEN_CALLS = {
    # "exec", "eval", "__import__",
    # 默认是空的
}
```

**解决方案:**
- 如果是合理的导入，修改 `checker.py` 允许它
- 如果是不安全代码，需要修改提示词避免生成

---

### 问题 4: 输入输出格式不匹配 ⭐⭐⭐⭐

**现象:**
```
EvalResult(status=WA, stdout="...", expected="...")
```

**原因:**
- 生成的代码输出格式与预期不符
- 多余的空格、换行
- 输出顺序错误

**示例:**
```python
# 预期输出
"1 2 3"

# 实际输出
"1 2 3\n"  # 多了换行
" 1 2 3"   # 多了空格
```

**解决方案:**
`apps_eval/executor.py` 已经做了处理：

```python
# 自动去除首尾空白和标准化换行
if isinstance(result.stdout, str):
    result.stdout = '\n'.join([line.strip() for line in result.stdout.splitlines()])
```

但如果仍有问题，可能需要调整提示词。

---

### 问题 5: 运行时错误 ⭐⭐⭐⭐

**现象:**
```
EvalResult(status=RE, stderr="ZeroDivisionError: division by zero")
EvalResult(status=RE, stderr="IndexError: list index out of range")
```

**原因:**
- 代码逻辑错误
- 未处理边界情况
- 类型错误

**这是正常的！**
- RE（Runtime Error）会被正确标记为失败
- 不影响评估流程
- 反映了代码生成的质量

---

### 问题 6: 测试用例加载失败 ⭐⭐

**现象:**
```python
KeyError: 'inputs'
或
IndexError: list index out of range
```

**原因:**
- 数据集格式问题
- 测试用例缺失

**检查:**
```python
# 查看某个问题的测试用例
import json
with open("Datasets/code_contests.jsonl") as f:
    for line in f:
        data = json.loads(line)
        print(data['problem_id'])
        print(data['all_test_cases'])
        break
```

---

## 代码生成失败原因

### 原因 1: API 调用失败 ⭐⭐⭐⭐⭐

**现象:**
```
[X/165] ❌ problem_xxx 生成失败
```

**可能的错误:**

#### 1.1 网络问题
```
requests.exceptions.ConnectionError
requests.exceptions.Timeout
```

**解决方案:**
- 检查网络连接
- 检查 API 端点是否可达
- 增加重试次数（在 `generate_code.py` 中已有）

#### 1.2 API 限流
```
HTTP 429: Too Many Requests
```

**解决方案:**
```bash
# 减少并发数
python main.py --workers 1  # 顺序执行

# 或添加延迟（需修改代码）
```

#### 1.3 认证失败
```
HTTP 401: Unauthorized
```

**解决方案:**
```bash
# 检查 API Key
echo $DEEPSEEK_API_KEY

# 重新设置
export DEEPSEEK_API_KEY=sk-your-key
```

---

### 原因 2: Token 超限 ⭐⭐⭐⭐⭐

**现象:**
```python
# generate_code.py 中会返回
{"_token_limit_exceeded": True, "error_message": "..."}
```

**原因:**
- 问题描述太长
- 加上提示词和历史，超过模型上下文限制
- DeepSeek-V3 的上下文长度有限

**当前处理:**
```python
# generate_code.py 第 103-105 行
if data.get("_token_limit_exceeded"):
    print(f"Warning: Token limit exceeded, returning empty response")
    return ""
```

**改进建议:**
1. 截断过长的问题描述
2. 使用更大上下文的模型
3. 简化提示词

---

### 原因 3: 模型返回格式错误 ⭐⭐⭐⭐

**现象:**
生成的代码无法通过正则提取

**原因分析:**

#### Analyst 返回格式问题
期望返回 JSON，但实际返回：
```
The plan is as follows...
{plan details}
```

#### Developer 返回格式问题
期望返回纯代码，但实际返回：
```
Here's the solution:

```python
def solve():
    ...
```
```

#### Tester 返回格式问题
期望返回 `Input:\n...\nOutput:\n...`，但实际返回：
```
Test case 1:
Input: 5
Expected output: 10
```

**检查位置:**
```python
# roles/analyst.py, roles/coder.py, roles/tester.py
# 使用 code_truncate 提取代码
from utils import code_truncate
```

**解决方案:**
- 改进提示词，明确格式要求
- 增强正则表达式
- 添加更多示例

---

### 原因 4: Session 内部错误 ⭐⭐⭐

**现象:**
```python
Exception occurred
```

**可能的原因:**

#### 4.1 Monkey Patch 失败
```python
# main.py 中
import session as session_module
session_module.unsafe_execute = custom_unsafe_execute
```

如果在并行模式下，每个子进程需要重新 patch。

#### 4.2 find_method_name 失败
```python
# session.py 第 29 行
method_name = find_method_name(naivecode)
if method_name:
    code = naivecode
```

如果生成的是 STDIO 代码（没有函数定义），`find_method_name` 返回 None。

**修复建议:**
对于 CodeContests（STDIO 模式），应该修改这个逻辑：

```python
# 在 session.py 中
if method_name or "input()" in naivecode or "sys.stdin" in naivecode:
    code = naivecode
```

---

### 原因 5: 正则提取失败 ⭐⭐⭐⭐

**位置:** `main.py` 中的 `custom_unsafe_execute`

```python
pattern = r'Input:\s*(.*?)\s*Output:\s*(.*?)(?=\s*Input:|\Z)'
matches = re.findall(pattern, report, re.DOTALL | re.IGNORECASE)

if not matches:
    return "Error: No valid test cases found in report."
```

**失败场景:**
1. Tester 没有按格式返回
2. 提取的 Input/Output 为空
3. 格式变体（如 "Test Input:", "Expected Output:"）

**改进建议:**
使用更宽松的正则：

```python
# 更宽松的模式
pattern = r'(?:Test\s+)?Input[:\s]+(.*?)(?:Expected\s+)?Output[:\s]+(.*?)(?=(?:Test\s+)?Input|$)'
```

---

### 原因 6: 迭代轮次用尽 ⭐⭐⭐

**现象:**
代码生成了，但没通过测试，2 轮后停止

**原因:**
```python
# main.py 中设置
max_round=2  # 最多 2 轮迭代
```

**策略:**
- 第 0 轮：Analyst → Developer → Tester
- 第 1 轮：根据测试报告改进
- 2 轮后无论是否通过都停止

**如果想要更多轮次:**
```python
session = Session(..., max_round=5)  # 改为 5 轮
```

但注意：
- 更多轮次 = 更多 Token 消耗
- 不一定提升成功率（可能陷入循环）

---

## 诊断工具

### 工具 1: 检查单个问题的生成过程

```bash
# 查看某个问题的详细信息
cd baseline_outputs/run_20260209_181309/1575_A.\ Another\ Sorting\ Problem/

# 查看问题描述
cat problem_statement.txt

# 查看 session 历史
cat session_history.json | python -m json.tool

# 查看每一轮的代码
cat round_0/code_iteration.py
cat round_1/code_iteration.py

# 查看最终代码
cat final_solution.py
```

---

### 工具 2: 统计生成失败的原因

创建一个分析脚本：

```python
# analyze_failures.py
import json
from pathlib import Path

run_dir = Path("baseline_outputs/run_20260209_181309")

stats = {
    'total': 0,
    'success': 0,
    'failed': 0,
    'no_code': 0,
    'empty_code': 0,
    'error_code': 0
}

for problem_dir in run_dir.iterdir():
    if not problem_dir.is_dir():
        continue
    
    stats['total'] += 1
    
    final_code = problem_dir / "final_solution.py"
    
    if not final_code.exists():
        stats['no_code'] += 1
        stats['failed'] += 1
    else:
        code = final_code.read_text(encoding='utf-8')
        
        if not code.strip():
            stats['empty_code'] += 1
            stats['failed'] += 1
        elif "Generation failed" in code or "Exception" in code:
            stats['error_code'] += 1
            stats['failed'] += 1
        else:
            stats['success'] += 1

print(json.dumps(stats, indent=2))
```

---

### 工具 3: 检查 API 连接

```python
# test_api.py
import os
from generate_code import build_llm

# 设置 API Key
os.environ['DEEPSEEK_API_KEY'] = 'sk-your-key'

# 测试连接
llm = build_llm("MODEL_C", temperature=0.0, max_tokens=100)

try:
    response = llm.chat([
        {"role": "user", "content": "Say 'Hello, World!'"}
    ])
    
    print("✅ API 连接成功")
    print(f"响应: {response}")
    print(f"Token 使用: {llm.total_tokens}")
except Exception as e:
    print(f"❌ API 连接失败: {e}")
```

---

### 工具 4: 测试单个问题的生成

```python
# test_single_problem.py
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

os.environ['DEEPSEEK_API_KEY'] = 'sk-your-key'

from session import Session
from apps_eval.data import get_data
from roles.rule_descriptions_actc import TEAM, ANALYST, PYTHON_DEVELOPER, TESTER
from main import custom_unsafe_execute

# 加载数据集
dataset = get_data('code_contests')
instance = dataset[0]  # 测试第一个问题

print(f"问题: {instance.instance_id}")
print(f"描述长度: {len(instance.problem_statement)}")

# 初始化 Session
session = Session(
    TEAM=TEAM,
    ANALYST=ANALYST,
    PYTHON_DEVELOPER=PYTHON_DEVELOPER,
    TESTER=TESTER,
    requirement=instance.problem_statement,
    model='deepseek-chat',
    majority=1,
    max_tokens=1400,
    temperature=0.3,
    top_p=0.95,
    max_round=2,
    before_func=''
)

# Monkey Patch
import session as session_module
session_module.unsafe_execute = custom_unsafe_execute

# 运行
try:
    code, session_history = session.run_session()
    
    print("\n" + "=" * 60)
    print("生成结果:")
    print("=" * 60)
    print(code)
    
    print("\n" + "=" * 60)
    print("Session 历史:")
    print("=" * 60)
    import json
    print(json.dumps(session_history, indent=2, ensure_ascii=False))
    
except Exception as e:
    print(f"\n❌ 生成失败: {e}")
    import traceback
    traceback.print_exc()
```

---

## 解决方案汇总

### 立即可用的解决方案

#### 1. 使用顺序评估（推荐 Windows 用户）
```bash
cd Self-collaboration-Code-Generation-main
python quick_eval.py
```

#### 2. 恢复并评估（Linux/Mac 或较少题目）
```bash
python recover_and_eval.py --workers 4
```

#### 3. 重新生成失败的题目
```bash
# 需要修改 main.py，只处理失败的题目
# 或使用 --sequential 模式逐个生成
python main.py --sequential
```

---

### 改进建议

#### 1. 增强错误处理
在 `main.py` 的 `process_single_problem` 中：

```python
try:
    code, session_history = session.run_session()
except Exception as e:
    # 记录详细错误
    error_log = {
        'error_type': type(e).__name__,
        'error_message': str(e),
        'traceback': traceback.format_exc()
    }
    
    with open(problem_dir / "error.json", 'w') as f:
        json.dump(error_log, f, indent=2)
```

#### 2. 添加进度保存
每生成 N 个问题，保存一次中间结果。

#### 3. 支持断点续传
检查已生成的问题，跳过它们。

#### 4. 改进提示词
根据失败案例，优化 `roles/rule_descriptions_actc.py` 中的提示。

#### 5. 添加重试机制
对于 API 失败，自动重试 3 次。

---

## 常见问题 FAQ

**Q: 为什么只生成了 1-8 个代码就停止了？**  
A: 可能原因：
1. API 调用失败（网络、限流）
2. 进程崩溃（Windows 多进程问题）
3. 手动中断（Ctrl+C）

**Q: 可以只重新生成失败的题目吗？**  
A: 可以，需要修改 `main.py`：
```python
# 加载已有结果
existing = set()
if run_dir.exists():
    for d in run_dir.iterdir():
        if (d / "final_solution.py").exists():
            existing.add(d.name)

# 过滤数据集
dataset = [d for d in get_data('code_contests') 
           if d.instance_id not in existing]
```

**Q: 如何提高生成成功率？**  
A: 
1. 使用更好的模型（如 GPT-4）
2. 增加 max_tokens
3. 优化提示词
4. 增加迭代轮数

**Q: 评估结果准确吗？**  
A: 是的，使用与 APPS 相同的评估逻辑，包括：
- 代码执行隔离
- 超时控制
- 输出对比
- 安全检查

---

**需要更多帮助？查看详细日志文件或运行诊断脚本！**
