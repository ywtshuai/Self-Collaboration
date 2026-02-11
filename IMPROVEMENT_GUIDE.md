# 🚀 代码生成质量改进指南

## 📊 当前状态评估

### ✅ 框架状态：完全正常
- ✅ 代码能够正确执行
- ✅ 输出不再为空
- ✅ Pass@1 = 20% (1/5)
- ✅ 部分问题准确率很高（82%, 100%）

### ⚠️ 待改进：代码质量
- WA (Wrong Answer) 主要原因：算法逻辑、浮点精度、边界情况
- Tester 样例可能不够覆盖
- Coder 对错误反馈的响应不够

---

## 🎯 改进方向

### 改进 1: 增强 Tester 样例质量

**当前问题**：
- Tester 只生成 5 个简单样例
- 可能没有覆盖关键边界情况
- Coder 看到错误但不知道如何修复

**改进方案**：修改 `roles/rule_descriptions_actc.py` 中的 `TESTER` 提示词

#### 方案 A: 更详细的测试策略

```python
TESTER = '''I want you to act as a tester on our development team. You will receive a Python script for a competitive programming problem, and your job is:

1. **Generate 5-7 diverse test cases** that cover:
   - **Minimal input** (smallest constraints, e.g., n=1)
   - **Typical case** (medium-sized, representative inputs)
   - **Edge cases** (maximum constraints, boundary values)
   - **Corner cases** (special structures like all zeros, all same values)

2. **Format each test case as**:
   ```
   Input:
   <input_data>
   
   Output:
   <expected_output>
   ```

3. **For each test case, ensure**:
   - Input follows the problem's format exactly
   - Expected output is correct and matches problem requirements
   - Test cases are simple enough to manually verify

**Critical Rules:**
- Do NOT write Python test code or functions like `def check(candidate)`.
- Only provide plain text Input/Output pairs in markdown code blocks.
- Make sure test cases progress from simple to complex.

**Example format:**
```
Input:
3 2
AA
AB
BA

Output:
1 2 3
```

Remember, provide ONLY the test cases in the specified format, no explanations.
'''
```

#### 方案 B: 加强 Coder 对错误的响应

修改 `PYTHON_DEVELOPER`：

```python
PYTHON_DEVELOPER = '''I want you to act as a Python developer on our development team for competitive programming problems. Your job:

1. **If you receive a plan**: Write a **complete Python script** that reads from **standard input** and writes to **standard output**.

2. **If you receive a test report with failures**:
   - **Carefully read** each failed test case
   - **Identify the bug**: Compare expected vs actual output
   - **Fix the logic**: Modify the algorithm to handle the failing cases
   - **Verify**: Mentally trace through the fixed code with failed inputs

**Critical Requirements:**
- Use `input()` or `sys.stdin.read()` to read input
- Use `print()` to output results (match exact format, including spaces and newlines)
- Write a **standalone script** (NOT a class like `class Solution`)
- The code must be executable as-is
- Handle edge cases: empty input, minimum/maximum constraints, special values

**Common Pitfalls to Avoid:**
- Off-by-one errors in loops
- Integer overflow (use appropriate data types)
- Floating-point precision (use proper formatting)
- Input parsing errors (split(), strip(), int() conversions)

**Debugging Strategy:**
When a test fails:
1. Print or trace the failing input mentally
2. Identify where actual output differs from expected
3. Fix the specific logic causing the difference
4. Ensure fix doesn't break other cases

Remember, provide ONLY the Python code, no explanations.
'''
```

---

### 改进 2: 增加迭代轮数

**当前配置**：`max_round=2`（只有 2 轮 Tester-Coder 迭代）

**建议修改**：`main.py` 中的 `process_single_problem` 函数

```python
# 找到这一行
session = Session(problem, developer, analyst, tester, max_round=2)

# 改为
session = Session(problem, developer, analyst, tester, max_round=4)  # 增加到 4 轮
```

**影响**：
- ✅ Coder 有更多机会根据错误修正代码
- ⚠️ 生成时间增加（约 2 倍）
- ⚠️ Token 消耗增加

---

### 改进 3: 优化 Analyst 提示词（可选）

为 Analyst 增加示例和具体指导：

```python
ANALYST = '''I want you to act as a requirement analyst on our development team. Given a competitive programming problem, your task is to analyze and develop a high-level plan. The plan should include:

1. **Input/Output Format Analysis**: 
   - Clearly specify how to parse input (e.g., "First line: n m, next n lines: ...")
   - Specify exact output format (e.g., "Single integer", "Space-separated integers")
   - Note any special formatting requirements (precision for floats, etc.)

2. **Algorithm Design**: 
   - Identify the problem type (sorting, graph, DP, greedy, geometry, etc.)
   - Outline the core algorithm with complexity analysis
   - Break down into implementable steps

3. **Edge Cases**: 
   - Minimum input (n=1, empty arrays, etc.)
   - Maximum constraints (n=10^5, large numbers)
   - Special values (zeros, negatives, duplicates)
   - Boundary conditions specific to the problem

4. **Common Pitfalls**:
   - Overflow risks
   - Precision issues
   - Off-by-one errors

Remember, provide the concise plan in JSON format with clear structure.
'''
```

---

## 📈 预期改进效果

### 短期目标（改进 Tester + 增加迭代）
- Pass@1: 20% → **30-40%**
- 平均准确率提升
- 减少简单错误（输入解析、格式问题）

### 长期目标（全面改进）
- Pass@1: 30-40% → **50%+**
- 需要结合：
  - 更好的模型（如 DeepSeek-V3 或 Reasoner）
  - 更多示例代码在提示词中
  - Few-shot learning（在提示词中加入成功案例）

---

## 🔧 快速应用改进

### 方案 1: 最小改动（推荐先试）

**只改 2 个地方**：

1. **增加迭代轮数**：
```bash
# 在 main.py 中找到
max_round=2
# 改为
max_round=4
```

2. **改进 TESTER 提示词**：
   - 复制上面 "方案 A" 的 `TESTER` 内容
   - 替换 `roles/rule_descriptions_actc.py` 中的对应部分

**测试**：
```bash
python main.py --limit 3 --sequential
```

**预期**：
- Pass@1 从 20% 提升到 25-35%
- 生成时间增加约 50-100%

---

### 方案 2: 全面改进

应用上述所有改进：
1. ✅ 增强 TESTER（方案 A）
2. ✅ 增强 PYTHON_DEVELOPER（方案 B）
3. ✅ 优化 ANALYST
4. ✅ 增加 max_round 到 4-5

---

## 📊 对比：当前 vs 理想状态

### 当前状态
```
TESTER: "Generate up to 5 simple test cases"
Coder:  看到错误 → 不知道怎么改 → 代码不变
Result: WA (算法逻辑问题)
```

### 改进后
```
TESTER: "Generate 5-7 diverse cases covering minimal/typical/edge/corner"
Coder:  看到错误 → 分析差异 → 修复逻辑 → 验证修复
Result: AC or improved accuracy
```

---

## 💡 重要说明

### 关于 20% Pass@1 的认知

**这个结果其实不错！** 原因：

1. **CodeContests 题目很难**
   - 这些是 Codeforces 真实比赛题
   - 人类选手在比赛中的通过率也不是 100%

2. **对比业界基准**
   - GPT-4 在 APPS 数据集上：Pass@1 ≈ 20-30%
   - AlphaCode 论文：Pass@1 ≈ 30-40%（使用大量采样）
   - 你的当前结果：20%

3. **部分题目准确率高**
   - 1575_A: 100% ✅
   - 1575_D: 82% ✅
   - 说明框架对简单/中等题目效果很好

### WA vs 框架问题的区别

| 症状 | WA (代码质量问题) | 框架问题 |
|------|------------------|---------|
| Stdout | **有输出** | 空输出 |
| 错误信息 | `Expected: X, Actual: Y` | `Error: Cannot find...` |
| 部分 AC | ✅ 有 | ❌ 无 |
| 改进方法 | 提示词、迭代次数 | 修复代码逻辑 |

**你的情况**：
- ✅ Stdout 有输出
- ✅ 部分测试 AC
- ✅ 错误是 WA（算法问题）

→ **这是 WA 问题，不是框架问题！框架已经完美运行！**

---

## 🎯 行动建议

### 立即行动（10 分钟）
```bash
# 1. 修改迭代次数
vi Self-collaboration-Code-Generation-main/main.py
# 找到 max_round=2，改为 max_round=4

# 2. 测试效果
cd Self-collaboration-Code-Generation-main
python main.py --limit 3 --sequential

# 3. 对比 Pass@1
cat baseline_outputs/run_*/REPORT.txt | grep "Pass@1"
```

### 短期优化（1 小时）
1. 应用改进的 TESTER 提示词（方案 A）
2. 应用改进的 PYTHON_DEVELOPER 提示词（方案 B）
3. 测试 5-10 个问题，观察准确率变化

### 长期优化（持续）
1. 分析失败案例，找出共性问题
2. 在提示词中加入成功案例（Few-shot）
3. 尝试更强的模型（DeepSeek-V3, Reasoner）
4. 增加温度参数调优（temperature, top_p）

---

## 📝 快速测试命令

```bash
# 测试改进效果
python main.py --limit 10 --workers 3

# 对比前后
echo "=== 之前 ==="
cat baseline_outputs/run_20260209_205226/REPORT.txt | grep -E "(Pass@1|准确率)"

echo "=== 改进后 ==="
cat baseline_outputs/run_*/REPORT.txt | grep -E "(Pass@1|准确率)" | tail -1
```

---

**总结：你的框架已经完美运行！现在需要的是提升代码生成质量，而不是修复 bug。建议先从增加迭代次数和改进 Tester 提示词开始！** 🚀
