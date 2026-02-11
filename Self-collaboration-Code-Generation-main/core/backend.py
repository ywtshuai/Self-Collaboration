# ============================================================
# 任务 1: 劫持 LLM 调用，使用 generate_code.py 中的 LLMClient
# ============================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 延迟初始化全局 LLM 客户端，避免循环导入
_GLOBAL_LLM = None


def _get_llm():
    """延迟导入和初始化 LLM 客户端"""
    global _GLOBAL_LLM
    if _GLOBAL_LLM is None:
        from core.generate_code import build_llm
        _GLOBAL_LLM = build_llm("MODEL_C", temperature=0.3, max_tokens=1400)
    return _GLOBAL_LLM


def call_chatgpt(prompt, model='gpt-3.5-turbo', stop=None, temperature=0., top_p=0.95,
                 max_tokens=128, echo=False, majority_at=None):
    """
    重写的 call_chatgpt 函数，使用 DeepSeek LLMClient 替代 OpenAI。
    忽略 model 参数，强制使用 _GLOBAL_LLM。
    支持 majority_at 参数（多次采样）。
    """
    llm = _get_llm()  # 使用延迟加载的 LLM 客户端
    num_completions = majority_at if majority_at is not None else 1
    completions = []
    
    for i in range(num_completions):
        try:
            # 调用 LLMClient 的 chat 方法
            response = llm.chat(
                messages=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            completions.append(response)
        except Exception as e:
            print(f"❌ LLM 调用失败 (第 {i+1}/{num_completions} 次): {e}")
            # 如果失败，添加空字符串作为占位
            completions.append("")
    
    return completions[:num_completions]