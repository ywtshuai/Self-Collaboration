# 🧪 测试运行指南

## ✅ 最新修复（2026-02-09 20:40）

### 关键修复
1. ✅ **保存最终代码时自动添加导入** - 确保 final_solution.py 包含所有必要的 import
2. ✅ **返回值使用补全后的代码** - 确保评估阶段使用完整代码
3. ✅ **从 session_history 获取代码** - 避免从混合的字符串中提取
4. ✅ **保存评估检查点** - 防止统计阶段出错导致丢失

---

## 🚀 推荐的测试步骤

### 步骤 1: 测试单个问题（必做）

```bash
cd Self-collaboration-Code-Generation-main

# 最保守的测试
python main.py --limit 1 --sequential
```

**立即检查**:
```bash
# 1. 检查生成的代码
cd baseline_outputs/run_*/1575_A*/
cat final_solution.py

# 应该看到：
# import sys
# 
# def main():
#     ...
# 
# if __name__ == "__main__":
#     main()

# 2. 手动测试代码
echo "1 3
ABC" | python final_solution.py
# 应该输出: 1

# 3. 检查 report
cat round_0/report_iteration.txt
# 应该看到类似:
# Test Case 1 Failed: ... Actual Output: 1 ...
# 或
# Code Test Passed.
```

### 步骤 2: 测试 3 个问题

如果步骤 1 通过：
```bash
cd Self-collaboration-Code-Generation-main
python main.py --limit 3 --sequential
```

检查 Pass@1 是否 > 0%：
```bash
cat baseline_outputs/run_*/REPORT.txt | grep "Pass@1"
# 期望: Pass@1: 33.33% (1/3) 或更高
```

### 步骤 3: 小规模并行测试

```bash
python main.py --limit 5 --workers 2
```

---

## 🔍 诊断清单

运行后必须检查的关键点：

### ✅ 检查点 1: 代码有导入
```bash
head -5 baseline_outputs/run_*/1575_A*/final_solution.py
```
**期望输出**:
```python
import sys

def main():
    data = sys.stdin.read().strip().split()
```

### ✅ 检查点 2: 代码有入口点
```bash
tail -5 baseline_outputs/run_*/1575_A*/final_solution.py
```
**期望输出**:
```python
    print(' '.join(result))

if __name__ == "__main__":
    main()
```

### ✅ 检查点 3: 代码能手动运行
```bash
cd baseline_outputs/run_*/1575_A*/
echo "1 3
ABC" | python final_solution.py
```
**期望输出**: `1`（不是空）

### ✅ 检查点 4: Report 显示测试结果
```bash
cat baseline_outputs/run_*/1575_A*/round_0/report_iteration.txt
```
**期望**:
```
The compilation output of the preceding code is: Test Case 1 Failed:
  Status: WA
  Actual Output: 1  # 有实际输出
```
**而不是**:
```
Error: Cannot find test cases
```

### ✅ 检查点 5: 评估结果有输出
```bash
cat baseline_outputs/run_*/summary.json | python -m json.tool | grep -A 2 "stdout"
```
**期望**:
```json
"stdout": "1",  # 不是空字符串
```

### ✅ 检查点 6: Pass@1 > 0%
```bash
cat baseline_outputs/run_*/REPORT.txt | grep "Pass@1"
```
**期望**:
```
Pass@1: 20.00% (1/5) 或更高
```

---

## 🐛 常见问题排查

### 问题 A: Stdout 仍然为空

**诊断**:
```bash
# 检查代码
cat baseline_outputs/run_*/problem_*/final_solution.py | head -10

# 缺少 import sys？
grep "import sys" baseline_outputs/run_*/problem_*/final_solution.py
```

**修复**: 确认 `process_single_problem` 函数中的保存代码逻辑生效

### 问题 B: 代码逻辑错误（WA）

**这是正常的！**
- WA（Wrong Answer）表示代码运行了，但结果不对
- 这是生成代码的质量问题，不是框架问题
- 可以通过改进提示词或增加迭代轮次来提高

**验证代码确实运行了**:
```bash
# 检查 report，应该看到 Actual Output
cat baseline_outputs/run_*/problem_*/round_0/report_iteration.txt | grep "Actual Output"
```

### 问题 C: 所有问题都失败（Pass@1 = 0%）

**可能原因**:
1. 代码逻辑错误（正常现象，取决于模型质量）
2. 代码仍缺少导入（检查 final_solution.py）
3. 测试用例不正确（检查 tests_raw.txt）

**验证**:
```bash
# 手动运行一个代码
cd baseline_outputs/run_*/1575_A*/
cat final_solution.py > /tmp/test.py
cat round_0/tests_raw.txt | grep -A 10 "Input:" | head -5 > /tmp/input.txt
python /tmp/test.py < /tmp/input.txt
```

---

## 📊 预期的正常输出

### 生成阶段
```
[1/3] 开始处理: 1575_A. Another Sorting Problem
[1/3] ✅ 1575_A. Another Sorting Problem 生成成功
```

### 评估阶段（检查点保存）
```
💾 保存评估中间结果...
✅ 评估结果已保存到: baseline_outputs/run_.../eval_checkpoint.json
   即使后续步骤出错，评估数据也不会丢失
```

### 最终结果
```
📊 最终结果
================================================================================
✅ Pass@1: 33.33% (1/3)  # 或其他非零值
⏱️  总耗时: 78.45 秒
```

### Final Solution 文件
```python
import sys

def main():
    data = sys.stdin.read().strip().split()
    ...
    print(' '.join(result))

if __name__ == "__main__":
    main()
```

---

## 🎯 如果 Pass@1 仍然是 0%

这**可能是正常的**，取决于：

1. **问题难度** - CodeContests 的题目通常较难
2. **模型能力** - DeepSeek 在算法题上的表现
3. **提示词质量** - 当前的提示词可能不够详细
4. **迭代轮数** - 只有 2 轮可能不够

**如何提高 Pass@1**:

### 方法 1: 增加迭代轮数
```python
# 在 process_single_problem 中
session = Session(..., max_round=5)  # 改为 5 轮
```

### 方法 2: 改进提示词
在 `roles/rule_descriptions_actc.py` 中添加示例：
```python
PYTHON_DEVELOPER = '''...
**Example:**
```python
import sys

def main():
    data = sys.stdin.read().strip().split()
    n = int(data[0])
    # ... process input ...
    print(result)

if __name__ == "__main__":
    main()
```
...
'''
```

### 方法 3: 使用更好的模型
```bash
# 设置环境变量使用更强的模型
export MODEL_C=deepseek-reasoner  # 如果可用
```

---

## 💡 重要提示

### ✅ 代码能运行 vs ❌ 代码逻辑正确

- **能运行** (Status: WA, 有 Actual Output) ✅ 框架正常
- **逻辑正确** (Status: AC) ✅ 代码质量好

**如果看到**:
```
Test Case 1: Status: WA, Actual Output: 2 1, Expected: 1 2
```

这说明：
- ✅ 代码成功运行了
- ✅ 产生了输出（2 1）
- ❌ 但结果不对（应该是 1 2）

这是**代码质量问题**，不是**框架问题**。

---

## 📝 快速验证命令

一键检查所有关键点：
```bash
#!/bin/bash
echo "=== 检查最新运行 ==="
RUN_DIR=$(ls -td baseline_outputs/run_* | head -1)
echo "目录: $RUN_DIR"

echo -e "\n=== 检查代码导入 ==="
head -3 $RUN_DIR/1575_A*/final_solution.py

echo -e "\n=== 检查代码入口 ==="
tail -3 $RUN_DIR/1575_A*/final_solution.py

echo -e "\n=== 手动运行代码 ==="
cd $RUN_DIR/1575_A*
echo "1 3
ABC" | python final_solution.py

echo -e "\n=== 检查 Pass@1 ==="
grep "Pass@1" $RUN_DIR/REPORT.txt

echo -e "\n=== 检查 Stdout ==="
cat $RUN_DIR/summary.json | python -m json.tool | grep -m 3 "stdout"
```

保存为 `check_run.sh` 并执行：
```bash
bash check_run.sh
```

---

**现在运行 `python main.py --limit 1 --sequential` 并按照清单检查！**
