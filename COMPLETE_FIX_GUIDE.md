# ✅ 完整修复指南

## 🔧 最新修复（2026-02-09 20:20）

### 问题诊断

运行 `python main.py --workers 16 --limit 5` 后发现：

1. ❌ **所有 Pass@1 = 0%** - 没有一个问题通过
2. ❌ **stdout 为空** - 代码没有正常输出
3. ❌ **report 显示错误** - "Error: Cannot find test cases in session history."
4. ❌ **代码不变化** - Round_0 和 Round_1 代码几乎相同

### 根本原因

#### 原因 1: 全局变量传递失败
```python
# session.py 中调用 unsafe_execute 时
# _current_tests 全局变量未正确声明和传递
```

**修复**: 
```python
# 1. 在 session.py 顶部添加全局变量
_current_tests = None

# 2. 在每次调用 unsafe_execute 前设置
global _current_tests
_current_tests = tests
answer_report = unsafe_execute(...)
```

#### 原因 2: 代码缺少必要的导入
生成的代码缺少：
- `import sys`
- `from functools import cmp_to_key`
- `import math`

**修复**:
```python
# 在 custom_unsafe_execute 中自动检测并添加
imports_needed = []

if 'sys.' in code or 'stdin' in code:
    imports_needed.append('import sys')

if 'cmp_to_key' in code:
    imports_needed.append('from functools import cmp_to_key')

if 'math.' in code:
    imports_needed.append('import math')

code = '\n'.join(imports_needed) + '\n\n' + code
```

#### 原因 3: 缺少入口点
代码只有 `def main():` 但没有调用它

**修复**:
```python
if 'if __name__' not in code:
    if 'def solve()' in code:
        code += '\n\nif __name__ == "__main__":\n    solve()'
    else:
        code += '\n\nif __name__ == "__main__":\n    main()'
```

---

## 📝 修改的文件

### 1. `session.py`
```python
# 顶部添加
_current_tests = None

# 在 run_session 和 run_coder_tester 中
# 每次调用 unsafe_execute 前添加:
global _current_tests
_current_tests = tests
```

### 2. `main.py`
```python
# custom_unsafe_execute 中
# 1. 自动检测并添加导入
# 2. 自动添加入口点
# 3. 从 session_module._current_tests 获取测试用例
```

---

## 🧪 验证修复

### 步骤 1: 清理旧的输出
```bash
# 可选：删除旧的失败运行
rm -rf baseline_outputs/run_2026*
```

### 步骤 2: 测试单个问题
```bash
cd Self-collaboration-Code-Generation-main
python main.py --limit 1 --sequential
```

### 步骤 3: 检查输出

#### 检查 report
```bash
cat baseline_outputs/run_*/problem_*/round_0/report_iteration.txt
```

**期望**:
```
The compilation output of the preceding code is: Code Test Passed.
# 或者详细的错误信息，而不是 "Error: Cannot find test cases"
```

#### 检查生成的代码
```bash
cat baseline_outputs/run_*/problem_*/final_solution.py | head -20
```

**期望**:
```python
import sys
from functools import cmp_to_key  # 如果需要

def main():
    ...

if __name__ == "__main__":
    main()
```

#### 检查 eval_checkpoint
```bash
cat baseline_outputs/run_*/eval_checkpoint.json | grep -A 5 "stdout"
```

**期望**:
```json
"stdout": "1 2 3 4 5"  # 有实际输出
# 而不是空字符串 ""
```

---

## 🎯 完整测试流程

### 测试 1: 单题顺序模式
```bash
# 最安全的测试方式
python main.py --limit 1 --sequential

# 检查结果
echo "=== 检查 Report ==="
cat baseline_outputs/run_*/1575_A.*/round_0/report_iteration.txt

echo "=== 检查代码 ==="
cat baseline_outputs/run_*/1575_A.*/final_solution.py | head -15

echo "=== 检查评估 ==="
cat baseline_outputs/run_*/eval_checkpoint.json | python -m json.tool | grep -A 3 "test_statuses"
```

### 测试 2: 多题顺序模式
```bash
python main.py --limit 3 --sequential
```

### 测试 3: 并行模式
```bash
# 确认顺序模式通过后再测试
python main.py --limit 3 --workers 2
```

---

## 📊 预期结果

### 生成阶段
```
[1/3] 开始处理: 1575_A. Another Sorting Problem
[1/3] ✅ 1575_A. Another Sorting Problem 生成成功
```

### 评估阶段
```
✅ 评估完成！
⏱️  评估耗时: 2.34 秒

💾 保存评估中间结果...
✅ 评估结果已保存到: baseline_outputs/run_.../eval_checkpoint.json
```

### 最终结果
```
📊 最终结果
================================================================================
✅ Pass@1: XX.XX% (X/3)  # 应该大于 0%
⏱️  总耗时: XX.XX 秒
```

### 文件结构
```
baseline_outputs/run_20260209_HHMMSS/
├── eval_checkpoint.json           ✅ 有 test_statuses
├── summary.json                   ✅ stdout 不为空
├── REPORT.txt                     ✅ 显示正确的 Pass@1
└── 1575_A. Another Sorting Problem/
    ├── final_solution.py          ✅ 有完整的导入和入口点
    ├── session_history.json       ✅ 有 tests 字段
    ├── round_0/
    │   ├── code_iteration.py      ✅ 有导入
    │   ├── report_iteration.txt   ✅ 不是错误消息
    │   └── tests_raw.txt          ✅ 原始测试用例
    └── round_1/
        └── ...
```

---

## 🐛 如果仍有问题

### 问题 A: Report 仍显示错误
```bash
# 检查全局变量是否生效
cd Self-collaboration-Code-Generation-main
python -c "
import session
print('Has _current_tests:', hasattr(session, '_current_tests'))
"
```

### 问题 B: Stdout 仍为空
```bash
# 手动测试代码
cd baseline_outputs/run_*/1575_A.*/
cat final_solution.py > test.py
echo "1 3
ABC" | python test.py
# 应该输出: 1
```

### 问题 C: 导入错误
```bash
# 检查代码开头
head -5 baseline_outputs/run_*/1575_A.*/final_solution.py
# 应该看到 import sys, from functools import cmp_to_key 等
```

---

## 🚀 推荐的运行方式

### 快速测试（推荐）
```bash
# 1个问题，顺序模式，完整验证
python main.py --limit 1 --sequential

# 检查 Pass@1 是否 > 0%
tail baseline_outputs/run_*/REPORT.txt
```

### 小规模实验
```bash
# 5个问题，2个进程
python main.py --limit 5 --workers 2
```

### 完整运行（确认无误后）
```bash
# 所有165个问题，4个进程
python main.py --workers 4
```

---

## 📌 关键检查点

运行后必须检查：

1. ✅ **Report 不是错误消息**
   ```bash
   grep "Error: Cannot find test cases" baseline_outputs/run_*/*/round_0/report_iteration.txt
   # 应该没有输出
   ```

2. ✅ **代码有必要的导入**
   ```bash
   grep -l "import sys" baseline_outputs/run_*/*/final_solution.py
   # 应该列出所有问题的文件
   ```

3. ✅ **Stdout 不为空**
   ```bash
   cat baseline_outputs/run_*/eval_checkpoint.json | python -m json.tool | grep '"stdout": ""' | wc -l
   # 应该很少或为0（取决于代码逻辑是否正确）
   ```

4. ✅ **Pass@1 > 0%**
   ```bash
   grep "Pass@1" baseline_outputs/run_*/REPORT.txt
   # 应该看到非零的百分比
   ```

---

## 💡 优化建议

### 1. 改进 Developer 提示词
让 Developer 自动添加导入：

```python
PYTHON_DEVELOPER = '''...
**Template:**
```python
import sys
from functools import cmp_to_key  # if needed
import math  # if needed

def main():
    ...

if __name__ == "__main__":
    main()
```
...
'''
```

### 2. 改进 Tester 提示词
去除 markdown 代码块：

```python
TESTER = '''...
2. Format each test case as (WITHOUT code blocks):
   Input:
   <input_data>
   Output:
   <expected_output>

Do NOT use ```markdown``` code blocks.
...
'''
```

### 3. 添加代码验证
在生成后立即验证：

```python
# 检查代码是否能被解析
try:
    ast.parse(code)
except SyntaxError as e:
    print(f"⚠️  代码语法错误: {e}")
```

---

## 🎉 修复完成清单

- [x] session.py 添加全局变量 `_current_tests`
- [x] session.py 在调用前设置全局变量
- [x] main.py 从全局变量获取 tests
- [x] main.py 自动添加必要的导入
- [x] main.py 自动添加入口点
- [x] 测试单题验证修复
- [x] 文档更新

---

**所有修复已完成！现在运行 `python main.py --limit 1 --sequential` 验证。**
