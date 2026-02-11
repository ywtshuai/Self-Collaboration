# 模型配置指南

本项目支持通过环境变量灵活配置不同的 LLM API 服务商和模型。

## 快速开始

### 方法 1: 修改代码（适合固定配置）

编辑 `Self-collaboration-Code-Generation-main/main.py` 文件，在开头找到 API 配置部分，取消注释对应的方案。

### 方法 2: 环境变量（适合临时切换）

通过命令行设置环境变量，无需修改代码。

## 支持的 API 服务商

### 1. DeepSeek（官方）

```bash
# Windows
set MODEL_API_BASE_URL=https://api.deepseek.com/v1
set MODEL_API_KEY_ENV=DEEPSEEK_API_KEY
set DEEPSEEK_API_KEY=sk-your-deepseek-key
set MODEL_C=deepseek-chat

# Linux/Mac
export MODEL_API_BASE_URL=https://api.deepseek.com/v1
export MODEL_API_KEY_ENV=DEEPSEEK_API_KEY
export DEEPSEEK_API_KEY=sk-your-deepseek-key
export MODEL_C=deepseek-chat
```

### 2. 阿里云 DashScope（Qwen 官方）

```bash
# Windows
set MODEL_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
set MODEL_API_KEY_ENV=DASHSCOPE_API_KEY
set DASHSCOPE_API_KEY=sk-your-dashscope-key
set MODEL_C=qwen-coder-plus

# Linux/Mac
export MODEL_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export MODEL_API_KEY_ENV=DASHSCOPE_API_KEY
export DASHSCOPE_API_KEY=sk-your-dashscope-key
export MODEL_C=qwen-coder-plus
```

**可用模型：**
- `qwen-coder-plus`（推荐）
- `qwen-coder-turbo`
- `qwen-plus`
- `qwen-turbo`
- `qwen-max`

### 3. 硅基流动（第三方，速度快）

```bash
# Windows
set MODEL_API_BASE_URL=https://api.siliconflow.cn/v1
set MODEL_API_KEY_ENV=SILICONFLOW_API_KEY
set SILICONFLOW_API_KEY=sk-your-siliconflow-key
set MODEL_C=Qwen/Qwen2.5-Coder-32B-Instruct

# Linux/Mac
export MODEL_API_BASE_URL=https://api.siliconflow.cn/v1
export MODEL_API_KEY_ENV=SILICONFLOW_API_KEY
export SILICONFLOW_API_KEY=sk-your-siliconflow-key
export MODEL_C=Qwen/Qwen2.5-Coder-32B-Instruct
```

**可用模型：**
- `Qwen/Qwen2.5-Coder-32B-Instruct`（推荐，性能强）
- `Qwen/Qwen2.5-Coder-7B-Instruct`（速度快）
- `deepseek-ai/DeepSeek-V3`
- 更多模型见：https://siliconflow.cn/models

### 4. 其他 OpenAI 兼容服务

任何支持 OpenAI Chat Completions API 格式的服务都可以使用：

```bash
# Windows
set MODEL_API_BASE_URL=https://your-service.com/v1
set MODEL_API_KEY_ENV=YOUR_API_KEY_NAME
set YOUR_API_KEY_NAME=your-api-key
set MODEL_C=your-model-name

# Linux/Mac
export MODEL_API_BASE_URL=https://your-service.com/v1
export MODEL_API_KEY_ENV=YOUR_API_KEY_NAME
export YOUR_API_KEY_NAME=your-api-key
export MODEL_C=your-model-name
```

## 环境变量说明

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `MODEL_API_BASE_URL` | API endpoint 地址 | `https://api.deepseek.com/v1` |
| `MODEL_API_KEY_ENV` | API key 的环境变量名 | `DEEPSEEK_API_KEY` |
| `{MODEL_API_KEY_ENV}` | 实际的 API key | 无默认值，必须设置 |
| `MODEL_C` | 模型名称 | `deepseek-chat` |

## 运行示例

### 示例 1：使用 DeepSeek 测试 5 个问题

```bash
# 设置环境变量
set MODEL_API_BASE_URL=https://api.deepseek.com/v1
set MODEL_API_KEY_ENV=DEEPSEEK_API_KEY
set DEEPSEEK_API_KEY=sk-your-key
set MODEL_C=deepseek-chat

# 运行测试
cd Self-collaboration-Code-Generation-main
python main.py --limit 5 --workers 5
```

### 示例 2：使用硅基流动的 Qwen 模型

```bash
# 设置环境变量
set MODEL_API_BASE_URL=https://api.siliconflow.cn/v1
set MODEL_API_KEY_ENV=SILICONFLOW_API_KEY
set SILICONFLOW_API_KEY=sk-your-key
set MODEL_C=Qwen/Qwen2.5-Coder-32B-Instruct

# 运行测试
cd Self-collaboration-Code-Generation-main
python main.py --limit 5 --workers 5 --output-dir baseline_outputs_qwen
```

## 输出目录配置

为了避免覆盖不同模型的测试结果，建议为每个模型使用不同的输出目录：

```bash
# DeepSeek
python main.py --output-dir baseline_outputs_deepseek

# Qwen
python main.py --output-dir baseline_outputs_qwen

# 其他模型
python main.py --output-dir baseline_outputs_custom
```

## 验证配置

运行程序时，会在开头显示当前的 LLM 配置：

```
🔧 LLM 配置:
   - Base URL: https://api.siliconflow.cn/v1
   - API Key Env: SILICONFLOW_API_KEY
   - Model: Qwen/Qwen2.5-Coder-32B-Instruct
```

如果配置错误，会显示 401 认证失败错误。

## 故障排查

### 错误：Authentication Fails

**原因：** API key 无效或 endpoint 不匹配

**解决：**
1. 检查 API key 是否正确
2. 确认 `MODEL_API_BASE_URL` 与 API key 匹配
3. 确认模型名称格式正确（不同服务商格式可能不同）

### 错误：Model not found

**原因：** 模型名称不正确

**解决：**
1. 查看服务商文档确认正确的模型名称
2. 注意大小写和斜杠格式（如 `Qwen/Qwen2.5-Coder-32B-Instruct`）

### 错误：HTTP 404

**原因：** endpoint URL 不正确

**解决：**
1. 确认 `MODEL_API_BASE_URL` 是否包含正确的版本号（如 `/v1`）
2. 检查 URL 末尾是否有多余的斜杠

## 推荐配置

- **性能优先**：阿里云 DashScope 的 `qwen-coder-plus`
- **速度优先**：硅基流动的 `Qwen/Qwen2.5-Coder-7B-Instruct`
- **平衡**：硅基流动的 `Qwen/Qwen2.5-Coder-32B-Instruct`
- **经济实惠**：DeepSeek 的 `deepseek-chat`
