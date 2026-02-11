"""
Self-Collaboration Baseline 运行脚本
实现 Analyst -> Coder -> Tester 多智能体协作工作流
用于 CodeContests 数据集评估
"""
import os
import re
import json
import time
from typing import List, Dict, Any, Tuple
from pathlib import Path

# 设置 DeepSeek API Key
os.environ['DEEPSEEK_API_KEY'] = 'sk-cb2233a3ea8f475797b414d6d05365d8'
os.environ['DEEPSEEK_BASE_URL'] = 'https://api.deepseek.com/v1'
os.environ['MODEL_C'] = 'deepseek-chat'

from generate_code import LLMClient, LLMConfig
from apps_eval.data import get_data, InstanceData
from apps_eval.executor import evaluate_case, EvalResult
from apps_eval.parallel_runner import eval_code


# ==================== Prompt 定义 ====================

ANALYST_SYSTEM = """There is a development team that includes a requirements analyst, a developer, and a quality assurance reviewer. The team needs to develop programs that satisfy the requirements of the users. The different roles have different divisions of labor and need to cooperate with each others.

I want you to act as a requirement analyst on our development team. Given a user requirement, your task is to analyze, decompose, and develop a high-level plan to guide our developer in writing programs. The plan should include the following information:
1. Decompose the requirement into several easy-to-solve subproblems that can be more easily implemented by the developer.
2. Develop a high-level plan that outlines the major steps of the program.
Remember, your plan should be high-level and focused on guiding the developer in writing code, rather than providing implementation details."""

CODER_SYSTEM = """There is a development team that includes a requirements analyst, a developer, and a quality assurance reviewer. The team needs to develop programs that satisfy the requirements of the users. The different roles have different divisions of labor and need to cooperate with each others.

I want you to act as a developer on our development team. You will receive plans from a requirements analyst or test reports from a reviewer. Your job is split into two parts:
1. If you receive a plan from a requirements analyst, write code in Python that meets the requirements following the plan. Ensure that the code you write is efficient, readable, and follows best practices.
2. If you receive a test report from a reviewer, fix or improve the code based on the content of the report. Ensure that any changes made to the code do not introduce new bugs or negatively impact the performance of the code.

IMPORTANT CONSTRAINTS FOR CODECONTESTS:
- This is a CodeContests problem that requires standard input/output using sys.stdin and sys.stdout
- DO NOT use file I/O operations
- DO NOT use "class Solution" format
- Read from stdin and write to stdout directly
- Your solution should be a complete Python program

Remember, do not need to explain the code you wrote. You should provide a well-formed python code and your response should start with "```python\\n"."""

TESTER_SYSTEM = """There is a development team that includes a requirements analyst, a developer, and a quality assurance reviewer. The team needs to develop programs that satisfy the requirements of the users. The different roles have different divisions of labor and need to cooperate with each others.

I want you to act as a tester in the team. You will receive the code written by the developer, and your job is to generate 2-3 simple test cases to verify the correctness of the code.

For each test case, provide:
- Input: The input data (as it would be provided via stdin)
- Expected Output: The expected output

Format your response as:
Test Case 1:
Input:
<input data>
Expected Output:
<expected output>

Test Case 2:
...
"""


# ==================== 工具函数 ====================

def create_llm_client() -> LLMClient:
    """创建 LLM 客户端"""
    cfg = LLMConfig(
        provider="openai_compatible",
        base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        model="deepseek-chat",
        temperature=0.0,
        max_tokens=4096,
    )
    return LLMClient(cfg)


def clean_code(code: str) -> str:
    """清理代码中的 Markdown 标记"""
    code = code.strip()
    
    # 移除 markdown 代码块标记
    if code.startswith("```"):
        lines = code.split('\n')
        # 移除第一行（```python 或 ```）
        lines = lines[1:]
        # 移除最后一行如果是 ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = '\n'.join(lines)
    
    return code.strip()


def parse_test_cases(tester_output: str) -> List[Tuple[str, str]]:
    """
    从 Tester 输出中解析测试用例
    返回 [(input1, expected_output1), (input2, expected_output2), ...]
    """
    test_cases = []
    
    # 使用正则表达式提取测试用例
    # 匹配 "Test Case X:" 后面的 Input 和 Expected Output
    pattern = r"Test Case \d+:.*?Input:\s*(.*?)Expected Output:\s*(.*?)(?=Test Case \d+:|$)"
    matches = re.findall(pattern, tester_output, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        input_data = match[0].strip()
        expected_output = match[1].strip()
        
        # 清理可能的代码块标记
        input_data = re.sub(r'^```.*?\n', '', input_data)
        input_data = re.sub(r'\n```$', '', input_data)
        expected_output = re.sub(r'^```.*?\n', '', expected_output)
        expected_output = re.sub(r'\n```$', '', expected_output)
        
        test_cases.append((input_data, expected_output))
    
    return test_cases


# ==================== Self-Collaboration 工作流 ====================

class SelfCollaborationWorkflow:
    """Self-Collaboration 多智能体协作工作流"""
    
    def __init__(self, llm: LLMClient, max_refinement_rounds: int = 3):
        self.llm = llm
        self.max_refinement_rounds = max_refinement_rounds
    
    def run(self, problem: InstanceData) -> str:
        """
        运行完整的 Self-Collaboration 流程
        
        Args:
            problem: 问题实例
        
        Returns:
            最终生成的代码
        """
        print(f"\n{'='*60}")
        print(f"问题 ID: {problem.instance_id}")
        print(f"{'='*60}")
        
        # Step 1: Analyst 分析问题并生成计划
        print("\n[Step 1] Analyst 正在分析问题...")
        plan = self._analyst_analyze(problem.problem_statement)
        print(f"✓ 计划生成完成 (长度: {len(plan)} 字符)")
        
        # Step 2: Coder 根据计划生成初始代码
        print("\n[Step 2] Coder 正在生成代码...")
        code = self._coder_implement(problem.problem_statement, plan, is_initial=True)
        code = clean_code(code)
        print(f"✓ 初始代码生成完成 (长度: {len(code)} 字符)")
        
        # Step 3: Tester 生成测试用例
        print("\n[Step 3] Tester 正在生成测试用例...")
        test_cases_text = self._tester_generate_tests(problem.problem_statement, code)
        test_cases = parse_test_cases(test_cases_text)
        print(f"✓ 生成了 {len(test_cases)} 个测试用例")
        
        # Step 4: 自我修正循环
        if test_cases:
            print(f"\n[Step 4] 开始自我修正循环 (最多 {self.max_refinement_rounds} 轮)...")
            code = self._refinement_loop(problem.problem_statement, code, test_cases)
        else:
            print("\n[Warning] 未能解析测试用例，跳过自我修正")
        
        return code
    
    def _analyst_analyze(self, problem_statement: str) -> str:
        """Analyst 角色：分析问题并生成计划"""
        messages = [
            {"role": "system", "content": ANALYST_SYSTEM},
            {"role": "user", "content": f"Please analyze the following programming problem and provide a high-level plan:\n\n{problem_statement}"}
        ]
        
        response = self.llm.chat(messages, temperature=0.0, max_tokens=2048)
        return response
    
    def _coder_implement(self, problem_statement: str, context: str, is_initial: bool = True) -> str:
        """Coder 角色：生成或修复代码"""
        messages = [
            {"role": "system", "content": CODER_SYSTEM}
        ]
        
        if is_initial:
            # 初始代码生成
            user_message = f"""The plan from the requirement analyst is as following:
{context}

Please implement the following code. Use ```python to put the Python code in markdown quotes:
{problem_statement}"""
        else:
            # 代码修复
            user_message = f"""The report from the tester is as following:
{context}

Please fix or improve the code based on the test report. Use ```python to put the Python code in markdown quotes:
{problem_statement}"""
        
        messages.append({"role": "user", "content": user_message})
        
        response = self.llm.chat(messages, temperature=0.0, max_tokens=4096)
        return response
    
    def _tester_generate_tests(self, problem_statement: str, code: str) -> str:
        """Tester 角色：生成测试用例"""
        messages = [
            {"role": "system", "content": TESTER_SYSTEM},
            {"role": "user", "content": f"""The code provided by developer is as follows:
```python
{code}
```

The problem statement is:
{problem_statement}

Please generate 2-3 simple test cases to verify this code."""}
        ]
        
        response = self.llm.chat(messages, temperature=0.0, max_tokens=2048)
        return response
    
    def _refinement_loop(self, problem_statement: str, code: str, test_cases: List[Tuple[str, str]]) -> str:
        """自我修正循环"""
        current_code = code
        
        for round_num in range(1, self.max_refinement_rounds + 1):
            print(f"\n  Round {round_num}/{self.max_refinement_rounds}:")
            
            # 运行测试用例
            all_passed = True
            failed_cases = []
            
            for idx, (input_data, expected_output) in enumerate(test_cases):
                result = evaluate_case(
                    code=current_code,
                    input_data=input_data,
                    expected=expected_output,
                    timeout=10.0,
                    mode="stdio"
                )
                
                if result.status != "AC":
                    all_passed = False
                    failed_cases.append({
                        'case_num': idx + 1,
                        'input': input_data,
                        'expected': expected_output,
                        'status': result.status,
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    })
            
            if all_passed:
                print(f"  ✓ 所有测试用例通过！")
                return current_code
            
            print(f"  ✗ {len(failed_cases)}/{len(test_cases)} 个测试用例失败")
            
            # 如果是最后一轮，不再修复
            if round_num == self.max_refinement_rounds:
                print(f"  达到最大修复轮数，返回当前代码")
                break
            
            # 构建错误报告
            error_report = self._build_error_report(failed_cases)
            
            # 让 Coder 修复代码
            print(f"  正在修复代码...")
            new_code = self._coder_implement(problem_statement, error_report, is_initial=False)
            current_code = clean_code(new_code)
        
        return current_code
    
    def _build_error_report(self, failed_cases: List[Dict]) -> str:
        """构建错误报告"""
        report_parts = ["Test Report:\n"]
        
        for case in failed_cases:
            report_parts.append(f"\nTest Case {case['case_num']} FAILED:")
            report_parts.append(f"  Status: {case['status']}")
            report_parts.append(f"  Input: {case['input'][:200]}")
            report_parts.append(f"  Expected Output: {case['expected'][:200]}")
            report_parts.append(f"  Actual Output: {case['stdout'][:200]}")
            if case['stderr']:
                report_parts.append(f"  Error: {case['stderr'][:200]}")
        
        report_parts.append("\n\nPlease fix the code to pass all test cases.")
        
        return '\n'.join(report_parts)


# ==================== 主评估流程 ====================

def main():
    """主评估流程"""
    print("="*60)
    print("Self-Collaboration Baseline 评估")
    print("="*60)
    
    # 检查数据文件
    data_file = "./Datasets/code_contests.jsonl"
    if not os.path.exists(data_file):
        print(f"\n✗ 错误：数据文件不存在: {data_file}")
        print("请先运行 prepare_data.py 下载并准备数据集")
        return
    
    print(f"\n✓ 数据文件存在: {data_file}")
    
    # 加载数据集
    print("\n加载数据集...")
    try:
        dataset = get_data('code_contests')
        print(f"✓ 成功加载 {len(dataset)} 个问题")
    except Exception as e:
        print(f"✗ 加载数据集失败: {e}")
        return
    
    # 限制评估数量（用于测试）
    # 取消注释下面这行可以只评估前 N 个问题
    dataset = dataset[:5]
    
    # 创建 LLM 客户端
    llm = create_llm_client()
    
    # 创建工作流
    workflow = SelfCollaborationWorkflow(llm, max_refinement_rounds=3)
    
    # 记录开始时间
    start_time = time.time()
    
    # 对每个问题运行 Self-Collaboration
    print(f"\n开始评估 {len(dataset)} 个问题...")
    solutions = []
    
    for idx, problem in enumerate(dataset):
        print(f"\n{'='*60}")
        print(f"进度: {idx + 1}/{len(dataset)}")
        print(f"{'='*60}")
        
        try:
            code = workflow.run(problem)
            solutions.append(code)
        except Exception as e:
            print(f"\n✗ 错误: {e}")
            # 失败时添加空代码
            solutions.append("")
        
        # 每 10 个问题显示一次进度
        if (idx + 1) % 10 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / (idx + 1)
            remaining = avg_time * (len(dataset) - idx - 1)
            print(f"\n进度统计:")
            print(f"  已完成: {idx + 1}/{len(dataset)}")
            print(f"  已用时: {elapsed/60:.1f} 分钟")
            print(f"  预计剩余: {remaining/60:.1f} 分钟")
            print(f"  Token 使用: {llm.total_tokens}")
    
    # 计算总时间
    total_time = time.time() - start_time
    
    # 评估结果
    print(f"\n{'='*60}")
    print("开始最终评估...")
    print(f"{'='*60}")
    
    try:
        eval_results = eval_code(dataset, solutions, timeout=10.0, workers=16)
        
        # 统计 Pass@1
        passed = 0
        total = len(eval_results)
        
        for acc_rate, _ in eval_results:
            if acc_rate == 1.0:  # 所有测试用例都通过
                passed += 1
        
        pass_at_1 = (passed / total) * 100 if total > 0 else 0.0
        
        # 打印结果
        print(f"\n{'='*60}")
        print("评估结果")
        print(f"{'='*60}")
        print(f"Pass@1:        {pass_at_1:.2f}%")
        print(f"通过题目数:    {passed}/{total}")
        print(f"Time Cost:     {total_time/60:.2f} 分钟")
        print(f"Token Usage:   {llm.total_tokens}")
        print(f"{'='*60}")
        
        # 保存详细结果
        results_file = "baseline_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'pass_at_1': pass_at_1,
                'passed': passed,
                'total': total,
                'time_cost_minutes': total_time / 60,
                'token_usage': llm.total_tokens,
                'problems': [
                    {
                        'problem_id': dataset[i].instance_id,
                        'accuracy': eval_results[i][0],
                        'solution': solutions[i]
                    }
                    for i in range(len(dataset))
                ]
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 详细结果已保存至: {results_file}")
        
    except Exception as e:
        print(f"\n✗ 评估失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
