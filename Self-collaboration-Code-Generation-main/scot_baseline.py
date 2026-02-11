"""
SCoT (Structured Chain-of-Thought) Baseline
使用 3-Shot Few-Shot 策略，提供算法示例来教导模型处理不同的逻辑结构
"""

import os
import sys
import re
import json
import time
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ============================================================
# 配置模型 API
# ============================================================
# 方案 1: DeepSeek (默认)
#os.environ['MODEL_API_BASE_URL'] = 'https://api.deepseek.com/v1'
#os.environ['MODEL_API_KEY_ENV'] = 'DEEPSEEK_API_KEY'
#os.environ['DEEPSEEK_API_KEY'] = 'sk-cb2233a3ea8f475797b414d6d05365d8'
#os.environ['MODEL_C'] = 'deepseek-chat'

# 方案 2: 阿里云 DashScope (Qwen 官方) - 如果要使用，请注释掉方案1，启用方案2
os.environ['MODEL_API_BASE_URL'] = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
os.environ['MODEL_API_KEY_ENV'] = 'DASHSCOPE_API_KEY'
os.environ['DASHSCOPE_API_KEY'] = 'sk-bf8c6bd3b0364cf1835351ccb25b2806'
os.environ['MODEL_C'] = 'qwen2.5-coder-32b-instruct'

# 方案 3: 硅基流动 (第三方)
#os.environ['MODEL_API_BASE_URL'] = 'https://api.siliconflow.cn/v1'
#os.environ['MODEL_API_KEY_ENV'] = 'SILICONFLOW_API_KEY'
#os.environ['SILICONFLOW_API_KEY'] = 'sk-6e2d56a85bbf4ba6ac45bc5a3ca7126a'
#os.environ['MODEL_C'] = 'Qwen/Qwen2.5-Coder-32B-Instruct'

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入依赖
from core.generate_code import build_llm, LLMConfig
from apps_eval.data import get_data, InstanceData
from apps_eval.parallel_runner import eval_code

# ============================================================
# SCoT System Prompt (3-Shot)
# ============================================================

SCOT_SYSTEM_PROMPT = """You are an expert programmer.
You are required to generate a Structured Chain-of-Thought (SCoT) before writing the code.
The SCoT must describe the logical steps using three specific structures: "Sequence", "Branch", and "Loop".

You must follow this format:
1. **Input/Output Analysis**: Define input format and expected output.
2. **Structured Plan**: Describe the algorithm using "Sequence", "Branch", and "Loop".
3. **Code**: Write the full Python script using `sys.stdin`.

Here are 3 examples of the required format:

--- EXAMPLE 1 ---
Problem: Find two numbers in `nums` that add up to `target`.

SCoT:
1. Input/Output Analysis:
   - Input: Array `nums`, Integer `target`.
   - Output: Indices of the two numbers.
2. Structured Plan:
   - Sequence: Initialize an empty dictionary `num_map`.
   - Loop: Iterate through `nums` with index `i` and value `num`:
     - Sequence: Calculate `complement = target - num`.
     - Branch: If `complement` is in `num_map`:
       - Sequence: Return `[num_map[complement], i]`.
     - Sequence: Store `num_map[num] = i`.
   - Sequence: Return empty list if no solution.

3. Code:
```python
import sys

def two_sum():
    lines = sys.stdin.read().strip().split('\\n')
    nums = list(map(int, lines[0].split()))
    target = int(lines[1])
    
    num_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            print(f"{num_map[complement]} {i}")
            return
        num_map[num] = i
    print("")

if __name__ == "__main__":
    two_sum()
```

--- EXAMPLE 2 ---
Problem: Check if the input string containing brackets is valid.

SCoT:
1. Input/Output Analysis:
   - Input: String s.
   - Output: Boolean (True/False).
2. Structured Plan:
   - Sequence: Initialize an empty stack and a mapping of closing to opening brackets.
   - Loop: Iterate through each character char in s:
     - Branch: If char is a closing bracket:
       - Branch: If stack is empty or top element doesn't match:
         - Sequence: Return False.
       - Sequence: Pop from stack.
     - Branch: Else (opening bracket):
       - Sequence: Push char onto stack.
   - Sequence: Return True if stack is empty, else False.

3. Code:
```python
import sys

def is_valid():
    s = sys.stdin.read().strip()
    
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    
    for char in s:
        if char in mapping:
            if not stack or stack[-1] != mapping[char]:
                print("False")
                return
            stack.pop()
        else:
            stack.append(char)
    
    print("True" if not stack else "False")

if __name__ == "__main__":
    is_valid()
```

--- EXAMPLE 3 ---
Problem: Merge all overlapping intervals.

SCoT:
1. Input/Output Analysis:
   - Input: List of intervals.
   - Output: List of merged intervals.
2. Structured Plan:
   - Sequence: Sort intervals by start time.
   - Sequence: Initialize merged list with the first interval.
   - Loop: Iterate through remaining intervals:
     - Sequence: Let last be the last interval in merged, curr be current interval.
     - Branch: If curr.start <= last.end (Overlap):
       - Sequence: Update last.end to max(last.end, curr.end).
     - Branch: Else (No overlap):
       - Sequence: Append curr to merged.
   - Sequence: Return merged.

3. Code:
```python
import sys

def merge_intervals():
    lines = sys.stdin.read().strip().split('\\n')
    n = int(lines[0])
    intervals = []
    for i in range(1, n + 1):
        start, end = map(int, lines[i].split())
        intervals.append([start, end])
    
    if not intervals:
        print("")
        return
    
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    
    for curr in intervals[1:]:
        last = merged[-1]
        if curr[0] <= last[1]:
            last[1] = max(last[1], curr[1])
        else:
            merged.append(curr)
    
    for interval in merged:
        print(f"{interval[0]} {interval[1]}")

if __name__ == "__main__":
    merge_intervals()
```

--- END OF EXAMPLES ---

Now, solve the following problem using the same format.

IMPORTANT:
- Use sys.stdin.read() for input.
- Output to stdout.
- Wrap code in ```python ... ```.
"""


# ============================================================
# SCoT Agent
# ============================================================

class SCoTAgent:
    """SCoT (Structured Chain-of-Thought) Agent"""
    
    def __init__(self, model_name: str = "deepseek-chat", temperature: float = 0.0):
        """
        初始化 SCoT Agent
        
        Args:
            model_name: 模型名称
            temperature: 温度参数
        """
        # 设置模型环境变量（如果还没有设置）
        if 'MODEL_C' not in os.environ:
            os.environ['MODEL_C'] = model_name
        elif model_name != os.environ.get('MODEL_C'):
            # 如果传入的模型名和环境变量不同，更新环境变量
            os.environ['MODEL_C'] = model_name
        
        # 使用 build_llm 函数构建 LLM 客户端
        # 增加 max_tokens 以避免复杂问题的代码被截断
        self.llm = build_llm(
            model_env='MODEL_C',
            temperature=temperature,
            max_tokens=8192  # 从 2048 增加到 8192，支持更长的代码
        )
        self.temperature = temperature
        
    def generate(self, problem_desc: str) -> str:
        """
        生成代码
        
        Args:
            problem_desc: 问题描述
            
        Returns:
            生成的 Python 代码
        """
        response = self.generate_with_response(problem_desc)
        code = self._extract_code(response)
        return code
    
    def generate_with_response(self, problem_desc: str) -> str:
        """
        生成代码并返回完整响应
        
        Args:
            problem_desc: 问题描述
            
        Returns:
            完整的 LLM 响应（包含 SCoT 和代码）
        """
        # 构造消息
        messages = [
            {"role": "system", "content": SCOT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Problem:\n{problem_desc}\n\nSCoT:"}
        ]
        
        # 调用 LLM
        try:
            response = self.llm.chat(messages, temperature=self.temperature)
            return response
            
        except Exception as e:
            print(f"❌ 生成失败: {e}")
            return f"# Generation failed: {e}"
    
    def _extract_code(self, response: str) -> str:
        """
        从响应中提取代码（改进版，支持截断的代码）
        
        Args:
            response: LLM 响应
            
        Returns:
            提取的代码
        """
        # 方法1: 尝试提取完整的 ```python ... ``` 代码块
        pattern = r"```python(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)
        
        if matches:
            # 返回第一个匹配的代码块
            code = matches[0].strip()
            return code
        
        # 方法2: 如果没有完整代码块，尝试提取从 ```python 开始的代码（即使被截断）
        pattern_start = r"```python(.*)$"
        matches_start = re.findall(pattern_start, response, re.DOTALL)
        
        if matches_start:
            print("⚠️  警告: 代码可能被截断（没有结束标记），尝试提取")
            code = matches_start[0].strip()
            # 移除可能的 SCoT 分析部分（以数字+点开头的行，如 "1. **Input/Output Analysis**"）
            lines = code.split('\n')
            code_lines = []
            in_code = False
            for line in lines:
                # 检测是否开始真正的代码（import 或 def 语句）
                if line.strip().startswith(('import ', 'from ', 'def ', 'class ')):
                    in_code = True
                # 跳过 SCoT 分析行
                if not in_code and re.match(r'^\d+\.\s+\*\*', line.strip()):
                    continue
                if in_code or line.strip().startswith(('import ', 'from ', 'def ', 'class ', '#', 'if ', 'while ', 'for ')):
                    code_lines.append(line)
            
            if code_lines:
                return '\n'.join(code_lines).strip()
            else:
                return code.strip()
        
        # 方法3: 寻找代码块（查找以 import/def 开头的部分）
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            # 检测代码开始
            if line.strip().startswith(('import ', 'from ', 'def ', 'class ')):
                in_code = True
            
            # 如果在代码区域内，收集所有行
            if in_code:
                code_lines.append(line)
        
        if code_lines:
            print("⚠️  警告: 未找到标准代码块标记，尝试提取代码部分")
            return '\n'.join(code_lines).strip()
        
        # 方法4: 如果都失败了，返回整个响应
        print("❌ 错误: 无法提取代码，返回整个响应")
        return response.strip()


# ============================================================
# 详细日志系统
# ============================================================

class DetailedLogger:
    """为每个题目创建详细的日志记录"""
    
    def __init__(self, output_dir: str = "scot_baseline_outputs_qwen"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.output_dir / f"run_{self.timestamp}"
        self.run_dir.mkdir(exist_ok=True)
        
    def create_problem_dir(self, instance_id: str) -> Path:
        """为单个问题创建目录"""
        problem_dir = self.run_dir / instance_id
        problem_dir.mkdir(exist_ok=True)
        return problem_dir
    
    def save_problem_info(self, problem_dir: Path, instance: InstanceData):
        """保存问题描述"""
        with open(problem_dir / "problem_statement.txt", "w", encoding="utf-8") as f:
            f.write(instance.problem_statement)
    
    def save_generation_info(self, problem_dir: Path, code: str, response: str):
        """保存生成信息"""
        # 保存最终代码（确保是纯代码）
        with open(problem_dir / "generated_code.py", "w", encoding="utf-8") as f:
            # 确保保存的是提取出的代码，而不是整个响应
            f.write(code)
        
        # 保存完整响应（包含 SCoT）
        with open(problem_dir / "full_response.txt", "w", encoding="utf-8") as f:
            f.write(response)
        
        # 如果代码看起来被截断或包含非代码内容，记录警告
        if len(response) > len(code) * 2 or "**Input/Output Analysis**" in code:
            with open(problem_dir / "extraction_warning.txt", "w", encoding="utf-8") as f:
                f.write("警告: 代码提取可能不完整或包含非代码内容\n")
                f.write(f"响应长度: {len(response)} 字符\n")
                f.write(f"提取代码长度: {len(code)} 字符\n")
    
    def save_summary(self, summary: Dict):
        """保存总体摘要"""
        with open(self.run_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


# ============================================================
# 主流程
# ============================================================

def process_single_instance(args: tuple) -> Dict[str, Any]:
    """
    处理单个实例
    
    Args:
        args: (agent, instance, idx, total, logger) 元组
        
    Returns:
        结果字典
    """
    agent, instance, idx, total, logger = args
    
    try:
        print(f"[{idx}/{total}] 开始处理: {instance.instance_id}")
        
        # 创建问题目录
        problem_dir = logger.create_problem_dir(instance.instance_id)
        logger.save_problem_info(problem_dir, instance)
        
        start_time = time.time()
        
        # 生成代码（修改 generate 方法以返回完整响应）
        response = agent.generate_with_response(instance.problem_statement)
        code = agent._extract_code(response)
        
        generation_time = time.time() - start_time
        
        # 保存生成信息
        logger.save_generation_info(problem_dir, code, response)
        
        if code and not code.startswith("# Generation failed"):
            print(f"[{idx}/{total}] ✅ {instance.instance_id} 生成成功 (耗时: {generation_time:.2f}s)")
        else:
            print(f"[{idx}/{total}] ❌ {instance.instance_id} 生成失败")
        
        return {
            'instance_id': instance.instance_id,
            'code': code,
            'test_cases': instance.test_cases,
            'generation_time': generation_time,
            'problem_dir': str(problem_dir),
            'response': response
        }
        
    except Exception as e:
        print(f"[{idx}/{total}] ❌ {instance.instance_id} 异常: {e}")
        return {
            'instance_id': instance.instance_id,
            'code': f"# Exception: {e}",
            'test_cases': instance.test_cases,
            'generation_time': 0.0,
            'error': str(e),
            'problem_dir': ''
        }


def main(
    model_name: str = None,
    temperature: float = 0.0,
    max_workers: int = 16,
    output_dir: str = None,
    limit: int = None
):
    """
    主函数
    
    Args:
        model_name: 模型名称（默认从环境变量 MODEL_C 读取）
        temperature: 温度参数
        max_workers: 并行线程数
        output_dir: 输出目录（None 则根据模型自动选择）
        limit: 限制处理的问题数量（用于测试）
    """
    print("=" * 80)
    print("SCoT (Structured Chain-of-Thought) Baseline")
    print("=" * 80)
    
    # 读取环境变量配置
    if model_name is None:
        model_name = os.environ.get('MODEL_C', 'deepseek-chat')
    
    # 根据模型名称自动选择输出目录
    if output_dir is None:
        if 'qwen' in model_name.lower():
            output_dir = 'scot_baseline_outputs_qwen'
        else:
            output_dir = 'scot_baseline_outputs'
    
    print(f"\n⚙️  配置信息:")
    print(f"  - 模型: {model_name}")
    print(f"  - Temperature: {temperature}")
    print(f"  - 并行线程数: {max_workers}")
    print(f"  - 输出目录: {output_dir}")
    
    # 加载数据集
    print(f"\n[步骤 1/5] 加载 CodeContests 数据集...")
    dataset = get_data('code_contests')
    
    # 如果指定了限制，只取前N个问题
    if limit is not None and limit > 0:
        dataset = dataset[:limit]
        print(f"✅ 加载完成，共 {len(dataset)} 个问题（限制为前 {limit} 个）")
    else:
        print(f"✅ 加载完成，共 {len(dataset)} 个问题")
    
    # 创建日志记录器
    logger = DetailedLogger(output_dir)
    print(f"✅ 运行目录: {logger.run_dir}")
    
    # 创建 SCoT Agent
    print(f"\n[步骤 2/5] 初始化 SCoT Agent...")
    agent = SCoTAgent(model_name=model_name, temperature=temperature)
    print(f"✅ Agent 初始化完成")
    
    # 并发生成代码
    print(f"\n[步骤 3/5] 开始生成代码...")
    print("=" * 80)
    
    all_results = []
    start_time = time.time()
    
    # 准备参数
    args_list = [
        (agent, instance, idx + 1, len(dataset), logger)
        for idx, instance in enumerate(dataset)
    ]
    
    # 使用 ThreadPoolExecutor 并发生成
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_single_instance, args) for args in args_list]
        
        for future in as_completed(futures):
            result = future.result()
            all_results.append(result)
    
    # 按照原始顺序排序（根据 instance_id）
    instance_id_order = {inst.instance_id: idx for idx, inst in enumerate(dataset)}
    all_results.sort(key=lambda x: instance_id_order.get(x['instance_id'], 999999))
    
    generation_time = time.time() - start_time
    
    print("\n" + "=" * 80)
    print(f"✅ 代码生成完成！")
    print(f"⏱️  生成耗时: {generation_time:.2f} 秒")
    print(f"📈 平均每题: {generation_time / len(dataset):.2f} 秒")
    print("=" * 80)
    
    # 评估代码
    print(f"\n[步骤 4/5] 评估生成的代码...")
    print("=" * 80)
    
    eval_start_time = time.time()
    
    # 准备评估数据
    eval_dataset = []
    eval_solutions = []
    
    for result in all_results:
        instance = next((inst for inst in dataset if inst.instance_id == result['instance_id']), None)
        if instance:
            eval_dataset.append(instance)
            eval_solutions.append(result['code'])
    
    # 确定评估的并行进程数（Windows 限制）
    import platform
    if platform.system() == 'Windows':
        eval_workers = min(max_workers * 2, 8)  # Windows: 最多 8 个进程
    else:
        eval_workers = min(max_workers * 4, 60)  # Linux/Mac: 最多 60 个进程
    
    print(f"🔍 使用 {eval_workers} 个进程并行评估... (平台: {platform.system()})")
    
    try:
        eval_results = eval_code(eval_dataset, eval_solutions, timeout=10.0, workers=eval_workers)
        eval_time = time.time() - eval_start_time
        
        print(f"✅ 评估完成！")
        print(f"⏱️  评估耗时: {eval_time:.2f} 秒")
        print(f"📈 平均每题: {eval_time / len(dataset):.2f} 秒")
        
    except Exception as e:
        print(f"\n❌ 评估过程出错: {e}")
        print(f"⚠️  已生成的代码已保存在: {logger.run_dir}")
        print(f"💡 提示: 可以使用恢复脚本完成评估")
        raise
    
    # 💾 立即保存评估结果（防止后续统计阶段出错导致丢失）
    print(f"\n💾 保存评估中间结果...")
    try:
        eval_checkpoint = {
            'eval_results': [
                {
                    'instance_id': result['instance_id'],
                    'accuracy': acc_rate,
                    'passed': acc_rate == 1.0,
                    'test_count': len(eval_result_list),
                    'passed_tests': sum(1 for r in eval_result_list if r.status == 'AC'),
                    'test_statuses': [r.status for r in eval_result_list]
                }
                for result, (acc_rate, eval_result_list) in zip(all_results, eval_results)
            ],
            'eval_time': eval_time,
            'eval_workers': eval_workers,
            'timestamp': datetime.now().isoformat()
        }
        
        checkpoint_file = logger.run_dir / "eval_checkpoint.json"
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(eval_checkpoint, f, indent=2, ensure_ascii=False)
        print(f"✅ 评估结果已保存到: {checkpoint_file}")
        print(f"   即使后续步骤出错，评估数据也不会丢失")
    except Exception as e:
        print(f"⚠️  警告: 保存评估结果失败: {e}")
        print(f"   将继续执行，但建议检查")
    
    # 统计结果
    print(f"\n[步骤 5/5] 统计结果...")
    print("=" * 80)
    
    total_problems = len(eval_results)
    passed = sum(1 for acc_rate, _ in eval_results if acc_rate == 1.0)
    pass_at_1 = (passed / total_problems * 100) if total_problems > 0 else 0.0
    
    total_time = time.time() - start_time
    
    # 获取 token 使用量
    total_tokens = 0
    if hasattr(agent.llm, 'total_tokens'):
        total_tokens = agent.llm.total_tokens
    else:
        print("⚠️  注意: 无法统计 Token 使用量（并行模式下）")
    
    # 打印最终结果
    print(f"\n📊 最终结果")
    print("=" * 80)
    print(f"✅ Pass@1: {pass_at_1:.2f}% ({passed}/{total_problems})")
    print(f"⏱️  总耗时: {total_time:.2f} 秒")
    print(f"   - 代码生成: {generation_time:.2f} 秒 ({generation_time/total_time*100:.1f}%)")
    print(f"   - 代码评估: {eval_time:.2f} 秒 ({eval_time/total_time*100:.1f}%)")
    
    if total_tokens > 0:
        print(f"🔢 总 Token 使用量: {total_tokens:,}")
        print(f"📈 平均每题 Token: {total_tokens/total_problems:.0f}")
        print(f"💰 估算成本 (按 $0.27/1M tokens): ${total_tokens * 0.27 / 1_000_000:.4f}")
    else:
        print(f"🔢 总 Token 使用量: N/A (并行模式下未统计)")
    
    print("=" * 80)
    
    # 保存结果
    print(f"\n保存结果...")
    print("=" * 80)
    
    # 整理详细结果
    detailed_results = []
    for i, (result, (acc_rate, eval_result_list)) in enumerate(zip(all_results, eval_results)):
        detailed_results.append({
            'instance_id': result['instance_id'],
            'problem_dir': result.get('problem_dir', ''),
            'code': result['code'],
            'accuracy': acc_rate,
            'passed': acc_rate == 1.0,
            'generation_time': result.get('generation_time', 0.0),
            'test_results': [
                {
                    'status': r.status,
                    'time_cost': r.time_cost,
                    'stdin': str(r.stdin)[:100] if r.stdin else '',
                    'stdout': str(r.stdout)[:100] if r.stdout else '',
                    'expected': str(r.expected)[:100] if r.expected else ''
                }
                for r in eval_result_list
            ],
            'response': result.get('response', '')
        })
    
    # 保存到 run 目录
    summary = {
        'summary': {
            'method': 'SCoT (Structured Chain-of-Thought)',
            'model': model_name,
            'temperature': temperature,
            'pass_at_1': pass_at_1,
            'passed': passed,
            'total': total_problems,
            'time_cost': {
                'total': total_time,
                'generation': generation_time,
                'evaluation': eval_time
            },
            'token_usage': {
                'total': total_tokens if total_tokens > 0 else 'N/A (parallel mode)',
                'average_per_problem': total_tokens / total_problems if (total_problems > 0 and total_tokens > 0) else 'N/A'
            },
            'config': {
                'max_workers': max_workers,
                'eval_workers': eval_workers,
                'few_shot': '3-Shot (Two Sum, Valid Parentheses, Merge Intervals)'
            },
            'timestamp': datetime.now().isoformat()
        },
        'results': detailed_results
    }
    
    logger.save_summary(summary)
    
    # 也保存到根目录（兼容旧版）- 根据模型名称选择文件名
    if 'qwen' in model_name.lower():
        output_file = "scot_baseline_results_qwen.json"
    else:
        output_file = "scot_baseline_results.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 详细结果已保存到: {logger.run_dir}")
    print(f"✅ 摘要已保存到: {output_file}")
    print(f"✅ 每个问题的详细日志: {logger.run_dir}/<problem_id>/")
    
    # 生成可读的摘要报告
    report_file = logger.run_dir / "REPORT.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("SCoT Baseline 运行报告\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"方法: SCoT (Structured Chain-of-Thought)\n")
        f.write(f"模型: {model_name}\n")
        f.write(f"Temperature: {temperature}\n")
        f.write(f"Few-Shot: 3-Shot (Two Sum, Valid Parentheses, Merge Intervals)\n")
        f.write(f"数据集: CodeContests\n")
        f.write(f"题目数量: {total_problems}\n\n")
        f.write(f"配置信息:\n")
        f.write(f"  - 并行线程数: {max_workers}\n")
        f.write(f"  - 评估进程数: {eval_workers}\n\n")
        f.write(f"结果统计:\n")
        f.write(f"  - Pass@1: {pass_at_1:.2f}% ({passed}/{total_problems})\n")
        f.write(f"  - 总耗时: {total_time:.2f} 秒\n")
        f.write(f"  - 生成耗时: {generation_time:.2f} 秒\n")
        f.write(f"  - 评估耗时: {eval_time:.2f} 秒\n")
        if total_tokens > 0:
            f.write(f"  - 总 Token: {total_tokens:,}\n")
            f.write(f"  - 平均每题 Token: {total_tokens/total_problems:.0f}\n\n")
        else:
            f.write(f"  - 总 Token: N/A (并行模式下未统计)\n\n")
        f.write(f"详细结果:\n")
        for result in detailed_results:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            f.write(f"  {status} {result['instance_id']} (准确率: {result['accuracy']*100:.0f}%)\n")
    
    print(f"✅ 可读报告已保存到: {report_file}")
    
    print("\n" + "=" * 80)
    print("🎉 所有任务完成！")
    print("=" * 80)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='SCoT Baseline Runner')
    parser.add_argument('--model', type=str, default=None,
                       help='模型名称（默认从环境变量 MODEL_C 读取）')
    parser.add_argument('--temperature', type=float, default=0.0,
                       help='Temperature 参数（默认: 0.0）')
    parser.add_argument('--workers', type=int, default=16,
                       help='并行线程数（默认: 16）')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='输出目录（默认: 根据模型自动选择 scot_baseline_outputs_qwen 或 scot_baseline_outputs）')
    parser.add_argument('--limit', type=int, default=None,
                       help='限制处理的问题数量（用于测试，如: --limit 5）')
    
    args = parser.parse_args()
    
    main(
        model_name=args.model,
        temperature=args.temperature,
        max_workers=args.workers,
        output_dir=args.output_dir,
        limit=args.limit
    )
