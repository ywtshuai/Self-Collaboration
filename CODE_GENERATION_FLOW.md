# 🔄 代码生成流程详解

## 📋 目录

1. [整体架构](#整体架构)
2. [详细流程图](#详细流程图)
3. [每个角色的职责](#每个角色的职责)
4. [迭代机制详解](#迭代机制详解)
5. [实际示例](#实际示例)
6. [关键参数说明](#关键参数说明)

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  process_single_problem(instance)                    │   │
│  │    ↓                                                  │   │
│  │  创建 Session(TEAM, ANALYST, DEVELOPER, TESTER)      │   │
│  │    ↓                                                  │   │
│  │  session.run_session()  ←─ 核心流程                 │   │
│  │    ↓                                                  │   │
│  │  返回: code, session_history                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 详细流程图

### 完整流程（最多 2 轮迭代）

```
开始
  │
  ├─→ [初始化] 创建三个角色
  │    - Analyst (需求分析师)
  │    - Coder (Python 开发者)
  │    - Tester (测试员)
  │
  ├─→ [第 0 轮] 初始生成
  │    │
  │    ├─→ 📋 Analyst.analyze()
  │    │    输入: 问题描述 (problem_statement)
  │    │    输出: 高层计划 (plan)
  │    │    示例: {
  │    │           "approach": "动态规划",
  │    │           "steps": ["读取输入", "初始化DP数组", "填充DP", "输出结果"]
  │    │          }
  │    │
  │    ├─→ 💻 Coder.implement(plan, is_init=True)
  │    │    输入: Analyst 的计划
  │    │    输出: Python 代码 (code_v0)
  │    │    示例: 完整的标准输入输出代码
  │    │
  │    ├─→ 🧪 Tester.test(code_v0)
  │    │    输入: Coder 生成的代码
  │    │    输出: 测试用例 (5 个 Input/Output 对)
  │    │    格式: Input:\n...\nOutput:\n...
  │    │
  │    ├─→ ⚙️ custom_unsafe_execute(code_v0, test_cases)
  │    │    功能: 执行代码并检查结果
  │    │    输出: "Code Test Passed." 或错误信息
  │    │
  │    └─→ 📊 判断
  │         ├─ 如果通过 → 提前结束 ✅
  │         └─ 如果失败 → 继续第 1 轮
  │
  ├─→ [第 1 轮] 根据反馈改进
  │    │
  │    ├─→ 💻 Coder.implement(error_report, is_init=False)
  │    │    输入: 测试失败报告
  │    │    输出: 改进的代码 (code_v1)
  │    │    改进策略:
  │    │      - 修复逻辑错误
  │    │      - 处理边界情况
  │    │      - 调整算法实现
  │    │
  │    ├─→ 🧪 Tester.test(code_v1)
  │    │    输入: 改进后的代码
  │    │    输出: 新的测试用例
  │    │
  │    ├─→ ⚙️ custom_unsafe_execute(code_v1, test_cases)
  │    │    功能: 再次执行并检查
  │    │    输出: "Code Test Passed." 或错误信息
  │    │
  │    └─→ 📊 判断
  │         ├─ 如果通过 → 结束 ✅
  │         └─ 如果失败 → 结束（达到最大轮数）❌
  │
  └─→ 返回最终代码
```

---

## 每个角色的职责

### 1. 📋 Analyst (需求分析师)

**文件位置:** `roles/analyst.py`

**职责:**
- 分析问题描述
- 制定高层解决方案
- 输出结构化的计划

**输入:**
```python
requirement = """
给定一个数组，找出最大子数组和。
Input: [-2,1,-3,4,-1,2,1,-5,4]
Output: 6
"""
```

**处理过程:**
```python
def analyze(self):
    # 调用 LLM
    responses = self.itf.run(
        prompt=self.history_message,
        max_tokens=self.max_tokens,
        temperature=self.temperature
    )
    
    plan = responses[0]  # 获取计划
    return plan
```

**输出示例:**
```json
{
  "problem_type": "动态规划",
  "input_format": "一行整数数组",
  "output_format": "一个整数",
  "algorithm": "Kadane算法",
  "steps": [
    "1. 读取输入数组",
    "2. 初始化当前和与最大和",
    "3. 遍历数组更新最大和",
    "4. 输出结果"
  ],
  "edge_cases": ["全负数", "单元素", "空数组"]
}
```

---

### 2. 💻 Coder (Python 开发者)

**文件位置:** `roles/coder.py`

**职责:**
- 根据计划或测试报告编写/改进代码
- 确保代码符合标准输入输出格式

**第一次调用（is_init=True）:**
```python
def implement(self, report, is_init=True):
    if is_init:
        # 基于 Analyst 的计划生成代码
        instruction = INSTRUCTPLAN.format(plan=report)
    else:
        # 基于测试报告改进代码
        instruction = INSTRUCTREPORT.format(report=report)
    
    # 调用 LLM 生成代码
    responses = self.itf.run(prompt=self.history_message, ...)
    code = code_truncate(responses[0])
    return code
```

**输出示例（第 0 轮）:**
```python
# 标准输入输出版本
import sys

def solve():
    # 读取输入
    line = sys.stdin.readline().strip()
    arr = list(map(int, line.split()))
    
    # Kadane算法
    max_sum = float('-inf')
    current_sum = 0
    
    for num in arr:
        current_sum = max(num, current_sum + num)
        max_sum = max(max_sum, current_sum)
    
    # 输出结果
    print(max_sum)

if __name__ == '__main__':
    solve()
```

**输出示例（第 1 轮 - 根据错误改进）:**
```python
# 修复边界情况
import sys

def solve():
    line = sys.stdin.readline().strip()
    if not line:  # 处理空输入
        print(0)
        return
    
    arr = list(map(int, line.split()))
    if not arr:  # 处理空数组
        print(0)
        return
    
    max_sum = arr[0]  # 修复：初始化为第一个元素而不是负无穷
    current_sum = arr[0]
    
    for num in arr[1:]:
        current_sum = max(num, current_sum + num)
        max_sum = max(max_sum, current_sum)
    
    print(max_sum)

if __name__ == '__main__':
    solve()
```

---

### 3. 🧪 Tester (测试员)

**文件位置:** `roles/tester.py`

**职责:**
- 为生成的代码创建测试用例
- 输出 Input/Output 对（不是 Python 测试代码）

**处理过程:**
```python
def test(self, code):
    instruction = INSTRUCTEST.format(code=code)
    
    # 调用 LLM 生成测试用例
    responses = self.itf.run(prompt=self.history_message, ...)
    report = responses[0]
    return report
```

**输出格式（CodeContests 适配版）:**
```
Input:
-2 1 -3 4 -1 2 1 -5 4
Output:
6

Input:
5 -3 5
Output:
7

Input:
-1 -2 -3
Output:
-1

Input:
10
Output:
10

Input:
1 2 3 4 5
Output:
15
```

**注意:** 这是文本格式，不是 Python 代码！

---

### 4. ⚙️ Executor (执行器)

**文件位置:** `main.py` 中的 `custom_unsafe_execute`

**职责:**
- 从 Tester 的输出提取测试用例
- 执行代码并验证结果

**处理流程:**
```python
def custom_unsafe_execute(code: str, report: str) -> str:
    # 1. 正则提取 Input/Output
    pattern = r'Input:\s*(.*?)\s*Output:\s*(.*?)(?=\s*Input:|\Z)'
    matches = re.findall(pattern, report, re.DOTALL | re.IGNORECASE)
    
    if not matches:
        return "Error: No valid test cases found in report."
    
    # 2. 逐个执行测试用例
    all_passed = True
    error_details = []
    
    for idx, (input_data, expected_output) in enumerate(matches, 1):
        # 调用 apps_eval.executor.evaluate_case
        result = evaluate_case(
            code=code,
            input_data=input_data.strip(),
            expected=expected_output.strip(),
            timeout=10.0,
            mode='stdio'  # 标准输入输出模式
        )
        
        if result.status == "AC":
            continue  # 通过
        else:
            all_passed = False
            error_details.append(
                f"Test Case {idx} Failed:\n"
                f"  Status: {result.status}\n"
                f"  Input:\n{input_data}\n"
                f"  Expected:\n{expected_output}\n"
                f"  Actual Output:\n{result.stdout}\n"
                f"  Error: {result.stderr}\n"
            )
    
    # 3. 返回结果
    if all_passed:
        return "Code Test Passed."
    else:
        return "\n".join(error_details)
```

---

## 迭代机制详解

### 核心代码（session.py）

```python
def run_session(self):
    # ========== 初始化 ==========
    plan = self.analyst.analyze()  # Analyst 分析
    report = plan
    is_init = True
    code = ""
    
    # ========== 迭代循环 ==========
    for i in range(self.max_round):  # max_round = 2
        
        # --- 步骤 1: Coder 生成/改进代码 ---
        naivecode = self.coder.implement(report, is_init)
        method_name = find_method_name(naivecode)
        
        if method_name:
            code = naivecode
        
        # 如果代码为空，提前结束
        if code.strip() == "":
            code = "error"
            break
        
        # --- 步骤 2: 检查是否是最后一轮 ---
        if i == self.max_round - 1:
            # 最后一轮，不再测试，直接返回
            self.session_history['Round_{}'.format(i)] = {"code": code}
            break
        
        # --- 步骤 3: Tester 生成测试用例 ---
        tests = self.tester.test(code)
        test_report = code_truncate(tests)
        
        # --- 步骤 4: 执行代码并获取结果 ---
        answer_report = unsafe_execute(
            self.before_func + code + '\n' + test_report + '\n' + f'check({method_name})', 
            ''
        )
        
        # 构造反馈报告
        report = f'The compilation output of the preceding code is: {answer_report}'
        
        # 保存当前轮次信息
        is_init = False
        self.session_history['Round_{}'.format(i)] = {
            "code": code, 
            "report": report
        }
        
        # --- 步骤 5: 检查是否通过 ---
        if answer_report == "Code Test Passed.":
            break  # 提前成功，结束迭代
        
        # 如果有错误，结束迭代
        if (plan == "error") or (code == "error") or (report == "error"):
            code = "error"
            break
    
    # ========== 清理并返回 ==========
    self.analyst.itf.clear_history()
    self.coder.itf.clear_history()
    self.tester.itf.clear_history()
    
    return code, self.session_history
```

### 迭代次数详解

**在 main.py 中设置:**
```python
session = Session(
    ...
    max_round=2,  # 最多 2 轮
    ...
)
```

**实际执行情况:**

#### 情况 1: 第 0 轮就通过 ✅
```
第 0 轮:
  Analyst → Coder → Tester → Execute → "Code Test Passed."
  → 提前结束（总共 1 轮）
```

#### 情况 2: 第 0 轮失败，第 1 轮通过 ✅
```
第 0 轮:
  Analyst → Coder → Tester → Execute → 错误报告
  
第 1 轮:
  Coder（根据错误改进）→ Tester → Execute → "Code Test Passed."
  → 结束（总共 2 轮）
```

#### 情况 3: 两轮都失败 ❌
```
第 0 轮:
  Analyst → Coder → Tester → Execute → 错误报告
  
第 1 轮:
  Coder（根据错误改进）→ Tester → Execute → 仍然失败
  → 达到 max_round，结束（总共 2 轮）
  → 返回第 1 轮的代码
```

**关键点:**
- `i = 0`: 第 0 轮（初始生成）
- `i = 1`: 第 1 轮（第一次改进）
- `i == self.max_round - 1` (即 `i == 1`) 时：最后一轮，不再测试

**所以答案是: Tester → Coder 最多迭代 1 次**

实际上：
- **第 0 轮**: Analyst → Coder → Tester → Execute
- **第 1 轮**: Coder → Tester → Execute (如果第 0 轮失败)
- **总共**: 最多调用 Coder 2 次，Tester 2 次

---

## 实际示例

### 示例：最大子数组和问题

**问题描述:**
```
给定一个整数数组，找出具有最大和的连续子数组。
Input: -2 1 -3 4 -1 2 1 -5 4
Output: 6
```

**第 0 轮:**

1. **Analyst 输出:**
```json
{
  "algorithm": "Kadane算法",
  "steps": ["读取输入", "遍历数组", "更新最大和", "输出"]
}
```

2. **Coder 输出 (code_v0):**
```python
import sys

arr = list(map(int, sys.stdin.readline().split()))
max_sum = float('-inf')
current_sum = 0

for num in arr:
    current_sum = max(num, current_sum + num)
    max_sum = max(max_sum, current_sum)

print(max_sum)
```

3. **Tester 输出:**
```
Input:
-2 1 -3 4 -1 2 1 -5 4
Output:
6

Input:
-1 -2 -3
Output:
-1
```

4. **Execute 结果:**
```
Test Case 2 Failed:
  Status: WA
  Input: -1 -2 -3
  Expected: -1
  Actual Output: -inf
  Error: 初始化问题
```

**第 1 轮:**

1. **Coder 收到错误报告并改进 (code_v1):**
```python
import sys

arr = list(map(int, sys.stdin.readline().split()))
max_sum = arr[0]  # 修复：初始化为第一个元素
current_sum = arr[0]

for num in arr[1:]:
    current_sum = max(num, current_sum + num)
    max_sum = max(max_sum, current_sum)

print(max_sum)
```

2. **Tester 输出:**
```
Input:
-2 1 -3 4 -1 2 1 -5 4
Output:
6

Input:
-1 -2 -3
Output:
-1

Input:
5
Output:
5
```

3. **Execute 结果:**
```
Code Test Passed. ✅
```

**最终:** 返回 code_v1

---

## 关键参数说明

### Session 初始化参数（main.py）

```python
session = Session(
    TEAM=TEAM,                    # 团队描述（提示词）
    ANALYST=ANALYST,              # Analyst 角色描述
    PYTHON_DEVELOPER=PYTHON_DEVELOPER,  # Coder 角色描述
    TESTER=TESTER,                # Tester 角色描述
    requirement=problem_statement, # 问题描述
    model='deepseek-chat',        # 模型名称（会被 backend 劫持）
    majority=1,                   # 采样数量（通常为 1）
    max_tokens=1400,              # 每次 LLM 调用的最大 token
    temperature=0.3,              # 生成温度（0.0-1.0）
    top_p=0.95,                   # 采样参数
    max_round=2,                  # ⭐ 最大迭代轮数
    before_func=''                # 前置函数（CodeContests 不需要）
)
```

### 各参数的影响

| 参数 | 默认值 | 影响 | 建议 |
|------|--------|------|------|
| `max_round` | 2 | 迭代次数 | 2-3 轮足够，更多会浪费 token |
| `max_tokens` | 1400 | 代码长度 | 简单题 800，复杂题 1400-2000 |
| `temperature` | 0.3 | 创造性 | 0.0-0.3 更稳定，0.7+ 更多样 |
| `majority` | 1 | 采样数 | 通常为 1，多采样用于投票 |

---

## 流程优化建议

### 1. 增加迭代轮数
```python
# 适用于复杂问题
session = Session(..., max_round=3)
```

### 2. 提早结束机制
当前已实现：
- 代码通过测试 → 提前结束 ✅
- 出现错误 → 提前结束 ✅

### 3. 保存中间状态
当前已实现：
```python
self.session_history['Round_{}'.format(i)] = {
    "code": code,
    "report": report
}
```

### 4. 错误处理
当前已实现：
```python
try:
    responses = self.itf.run(...)
except Exception as e:
    return "error"
```

---

## 总结

### 核心要点

1. **迭代次数**: 最多 2 轮（第 0 轮 + 第 1 轮）
2. **Tester → Coder**: 最多迭代 **1 次**（第 1 轮）
3. **提前结束**: 如果代码通过测试，立即结束
4. **最后一轮**: 不再测试，直接返回代码

### 流程总结

```
Analyst (1次) 
    ↓
Coder (第0轮)
    ↓
Tester (第0轮)
    ↓
Execute → 判断
    ├─ 通过 → 结束 ✅
    └─ 失败 → 继续
        ↓
    Coder (第1轮) ← 根据错误改进
        ↓
    Tester (第1轮)
        ↓
    Execute → 判断
        ├─ 通过 → 结束 ✅
        └─ 失败 → 结束 ❌（达到最大轮数）
```

**答案: Tester → Coder 最多迭代 1 次（从第 0 轮到第 1 轮）**

---

## 附录：完整的 Token 使用估算

假设每个角色每次调用使用的 token：

| 角色 | 输入 | 输出 | 总计 |
|------|------|------|------|
| Analyst | ~1000 | ~400 | ~1400 |
| Coder (第0轮) | ~1200 | ~800 | ~2000 |
| Tester (第0轮) | ~1500 | ~300 | ~1800 |
| Coder (第1轮) | ~1800 | ~800 | ~2600 |
| Tester (第1轮) | ~2000 | ~300 | ~2300 |

**两轮完整流程**: 约 10,000-12,000 tokens/问题

**DeepSeek 价格**: $0.27/1M tokens  
**单题成本**: $0.0027 - $0.0032

---

**现在您应该完全理解代码生成流程了！有任何问题欢迎继续提问。🎓**
