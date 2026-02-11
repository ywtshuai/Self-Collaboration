import os
import re
import time
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests


@dataclass
class LLMConfig:
    provider: str
    base_url: str
    api_key_env: str
    model: str
    temperature: float = 0.3
    max_tokens: int = 1400  # 旧名，内部会映射到 max_completion_tokens
    timeout_sec: int = 120
    max_retries: int = 5
    api_mode: str = "auto"  # "auto" | "chat" | "responses"


class LLMClient:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.api_key = os.getenv(cfg.api_key_env, "")
        self.total_tokens = 0  # 添加 token 统计器
        if cfg.provider != "openai_compatible":
            raise ValueError(f"Unsupported provider: {cfg.provider}")
        if not self.api_key:
            raise RuntimeError(f"Missing API key env var: {cfg.api_key_env}. Please export {cfg.api_key_env}=...")

    def _is_gpt5_family(self) -> bool:
        m = (self.cfg.model or "").lower()
        return m.startswith("gpt-5")  # covers gpt-5, gpt-5-mini/nano, gpt-5-chat-latest, gpt-5.1/5.2, etc.

    def _should_use_responses(self) -> bool:
        if self.cfg.api_mode == "responses":
            return True
        if self.cfg.api_mode == "chat":
            return False
        # auto
        m = (self.cfg.model or "").lower()
        # Pro models in your list (and bianxie notes) require Responses
        return ("-pro" in m) or m.startswith("o3-pro")

    def _post(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        last_err = None
        for attempt in range(self.cfg.max_retries):
            try:
                r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=self.cfg.timeout_sec)
                if r.status_code == 400:
                    # 检查是否是token超限的错误
                    try:
                        error_data = r.json()
                        error_msg = error_data.get("error", {}).get("message", "")
                        if "maximum context length" in error_msg or "tokens" in error_msg:
                            # 返回一个特殊的标记表示token超限
                            return {"_token_limit_exceeded": True, "error_message": error_msg}
                    except:
                        # 如果不是JSON响应，继续抛出错误
                        pass
                    raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
                elif r.status_code >= 400:
                    raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
                return r.json()
            except Exception as e:
                last_err = e
                time.sleep(min(2 ** attempt, 20))
        raise RuntimeError(f"LLM call failed after retries: {last_err}")

    def chat(
            self,
            messages: List[Dict[str, str]],
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
    ) -> str:
        base = self.cfg.base_url.rstrip("/")
        use_responses = self._should_use_responses()
        is_gpt5 = self._is_gpt5_family()

        # token budget
        mt = self.cfg.max_tokens if max_tokens is None else max_tokens

        if use_responses:
            # Responses API: we stringify messages (minimal change, no tool use)
            url = base + "/responses"
            input_text = "\n\n".join([f"{m.get('role', '')}: {m.get('content', '')}" for m in messages])

            payload: Dict[str, Any] = {
                "model": self.cfg.model,
                "input": input_text,
                "max_completion_tokens": mt,
            }
            # GPT-5 family：不传 temperature（便携AI说明 + 常见报错）
            if (not is_gpt5):
                payload["temperature"] = self.cfg.temperature if temperature is None else temperature

            data = self._post(url, payload)
            if data.get("_token_limit_exceeded"):
                print(f"Warning: Token limit exceeded, returning empty response: {data.get('error_message', '')}")
                return ""
            
            # 统计 token 使用量
            if "usage" in data:
                self.total_tokens += data["usage"].get("total_tokens", 0)
            
            # 兼容提取：优先 output_text，其次从 output 里拼
            if "output_text" in data and isinstance(data["output_text"], str):
                return data["output_text"]
            out_items = data.get("output", []) or []
            chunks = []
            for item in out_items:
                for c in item.get("content", []) or []:
                    if c.get("type") == "output_text" and "text" in c:
                        chunks.append(c["text"])
            return "".join(chunks).strip()

        else:
            # Chat Completions API
            url = base + "/chat/completions"
            payload: Dict[str, Any] = {"model": self.cfg.model, "messages": messages}

            # GPT-5：max_completion_tokens 替代 max_tokens；不传 temperature
            if is_gpt5:
                payload["max_completion_tokens"] = mt
            else:
                payload["max_tokens"] = mt
                payload["temperature"] = self.cfg.temperature if temperature is None else temperature

            data = self._post(url, payload)
            
            # 统计 token 使用量
            if "usage" in data:
                self.total_tokens += data["usage"].get("total_tokens", 0)
            
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as e:
                print(f"Warning: Unexpected response format, returning empty: {e}")
                return ""


_PROMPT_DIR = Path("Self-collaboration-Code-Generation-main/prompts")
_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def _load_md(filename: str) -> str:
    path = _PROMPT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt markdown not found: {path}")
    return path.read_text(encoding="utf-8")


def _render_md(template: str, **kwargs: Any) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1)
        if key not in kwargs:
            raise KeyError(f"Missing prompt variable: {key}")
        val = kwargs[key]
        return "" if val is None else str(val)

    return _VAR_RE.sub(repl, template)


# 由于我们在 run_baseline.py 中直接定义了 prompts，这里不需要加载 markdown
# 如果需要使用 markdown prompts，请确保 _PROMPT_DIR 指向正确的目录


def sys_msg(content: str) -> Dict[str, str]:
    return {"role": "system", "content": content}


def user_msg(content: str) -> Dict[str, str]:
    return {"role": "user", "content": content}


def build_llm(model_env: str, *, temperature: float, max_tokens: int) -> LLMClient:
    """
    构建 LLM 客户端，支持通过环境变量配置
    
    环境变量：
    - MODEL_API_BASE_URL: API endpoint (默认: https://api.deepseek.com/v1)
    - MODEL_API_KEY_ENV: API key 环境变量名 (默认: DEEPSEEK_API_KEY)
    - MODEL_C: 模型名称
    """
    # 读取配置
    base_url = os.environ.get("MODEL_API_BASE_URL", "https://api.deepseek.com/v1")
    api_key_env = os.environ.get("MODEL_API_KEY_ENV", "DEEPSEEK_API_KEY")
    model = os.environ.get(model_env, "deepseek-chat")
    
    # 打印配置信息（首次调用时）
    if not hasattr(build_llm, '_config_printed'):
        print(f"🔧 LLM 配置:")
        print(f"   - Base URL: {base_url}")
        print(f"   - API Key Env: {api_key_env}")
        print(f"   - Model: {model}")
        build_llm._config_printed = True
    
    return LLMClient(
        LLMConfig(
            provider="openai_compatible",
            base_url=base_url,
            api_key_env=api_key_env,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    )


if __name__ == "__main__":
    # 简单测试
    # 配置示例：使用硅基流动的 Qwen 模型
    """
    os.environ['MODEL_API_BASE_URL'] = 'https://api.siliconflow.cn/v1'
    os.environ['MODEL_API_KEY_ENV'] = 'SILICONFLOW_API_KEY'
    os.environ['SILICONFLOW_API_KEY'] = 'sk-6e2d56a85bbf4ba6ac45bc5a3ca7126a'
    os.environ['MODEL_C'] = 'Qwen/Qwen2.5-Coder-32B-Instruct'
    """

    os.environ['MODEL_API_BASE_URL'] = 'https://api.deepseek.com/v1'
    os.environ['MODEL_API_KEY_ENV'] = 'DEEPSEEK_API_KEY'
    os.environ['DEEPSEEK_API_KEY'] = 'sk-cb2233a3ea8f475797b414d6d05365d8'
    os.environ['MODEL_C'] = 'deepseek-chat'
    
    llm = build_llm("MODEL_C", temperature=0.0, max_tokens=512)
    
    response = llm.chat([
        {"role": "user", "content": "Say 'Hello, World!' in Python"}
    ])
    
    print("Response:", response)
    print("Total tokens used:", llm.total_tokens)
