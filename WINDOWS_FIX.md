# 🪟 Windows 平台注意事项

## 常见问题及解决方案

### 1️⃣ 多进程问题

在 Windows 上运行时，如果遇到多进程相关错误，请修改 `apps_eval/parallel_runner.py`：

#### 原代码：
```python
def eval_code(dataset: List[InstanceData], solutions: List[str],
              timeout: float = 10.0, workers: int = 64):
```

#### Windows 修复：
```python
def eval_code(dataset: List[InstanceData], solutions: List[str],
              timeout: float = 10.0, workers: int = 4):  # 减少 worker 数量
```

或者在 `main.py` 中调用时指定较少的 workers：
```python
eval_results = eval_code(eval_dataset, eval_solutions, timeout=10.0, workers=4)
```

---

### 2️⃣ 信号处理问题

`session.py` 中的 `time_limit` 函数使用了 UNIX 信号，在 Windows 上不可用。

**临时解决方案：**  
将 `custom_unsafe_execute` 中的超时时间设置得更长一些，避免依赖 `session.py` 的超时机制。

---

### 3️⃣ 路径问题

确保使用 `os.path.join` 而不是硬编码路径分隔符：

```python
# 正确
path = os.path.join('Datasets', 'code_contests.jsonl')

# 错误
path = 'Datasets/code_contests.jsonl'  # 在 Windows 上可能有问题
```

---

### 4️⃣ Python 命令

在 `apps_eval/executor.py` 中，Windows 使用 `python` 而不是 `python3`（已在代码中处理）。

---

### 5️⃣ 环境变量设置

在 Windows PowerShell 中：
```powershell
# 设置环境变量（当前会话）
$env:DEEPSEEK_API_KEY="sk-your-key"

# 永久设置（系统级）
[System.Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY', 'sk-your-key', 'User')
```

在 Windows CMD 中：
```cmd
set DEEPSEEK_API_KEY=sk-your-key
```

---

### 6️⃣ 推荐的 Windows 运行配置

在 `main.py` 中的 Session 初始化部分，推荐使用以下设置：

```python
session = Session(
    ...
    max_round=2,          # 保持较少的轮数
    max_tokens=1400,      # 适中的 token 数
    temperature=0.3,      # 较低的温度保证稳定性
    ...
)
```

并在调用 `eval_code` 时：
```python
eval_results = eval_code(
    eval_dataset, 
    eval_solutions, 
    timeout=10.0, 
    workers=4  # Windows 建议使用较少的 worker
)
```

---

## 🔍 调试建议

如果遇到问题，可以逐步调试：

### 1. 测试单个问题
修改 `main.py`：
```python
dataset = get_data('code_contests')[:1]  # 只测试第一个问题
```

### 2. 禁用多进程
修改 `apps_eval/parallel_runner.py`：
```python
def parallel_evaluate(tasks, workers=16):
    # 临时禁用多进程，改为顺序执行
    return [_worker(task) for task in tasks]
```

### 3. 打印详细日志
在 `custom_unsafe_execute` 中添加：
```python
print(f"[DEBUG] 提取到 {len(matches)} 个测试用例")
print(f"[DEBUG] Input: {input_data[:50]}...")
print(f"[DEBUG] Expected: {expected_output[:50]}...")
print(f"[DEBUG] Result: {result}")
```

---

## ✅ 验证安装

运行以下测试脚本验证环境：

```python
# test_components.py
import sys
import os

print("=" * 60)
print("环境验证测试")
print("=" * 60)

# 1. 检查 Python 版本
print(f"\n✓ Python 版本: {sys.version}")

# 2. 检查依赖
try:
    import requests
    print("✓ requests 已安装")
except ImportError:
    print("✗ requests 未安装，请运行: pip install requests")

# 3. 检查 API Key
api_key = os.getenv('DEEPSEEK_API_KEY')
if api_key:
    print(f"✓ DEEPSEEK_API_KEY 已设置: {api_key[:10]}...")
else:
    print("✗ DEEPSEEK_API_KEY 未设置")

# 4. 检查数据集
if os.path.exists('Datasets/code_contests.jsonl'):
    print("✓ 数据集文件存在")
else:
    print("✗ 数据集文件不存在")

# 5. 测试 LLM 连接
try:
    from generate_code import build_llm
    llm = build_llm("MODEL_C", temperature=0.0, max_tokens=50)
    response = llm.chat([{"role": "user", "content": "Say hi"}])
    if response:
        print(f"✓ LLM 连接成功: {response[:30]}...")
    else:
        print("✗ LLM 返回空响应")
except Exception as e:
    print(f"✗ LLM 连接失败: {e}")

print("\n" + "=" * 60)
```

运行：
```bash
python test_components.py
```

---

**如果以上都检查无误，就可以放心运行主程序了！🎉**
