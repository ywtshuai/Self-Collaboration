# ============================================================
# 任务 3: 修改 main.py（核心逻辑注入）
# ============================================================

import os
import sys
import json
import time
from typing import List, Dict, Any, Tuple
from multiprocessing import Pool, cpu_count
from datetime import datetime
from pathlib import Path

# ============================================================
# 配置模型 API
# ============================================================
# 方案 1: DeepSeek (默认)
os.environ['MODEL_API_BASE_URL'] = 'https://api.deepseek.com/v1'
os.environ['MODEL_API_KEY_ENV'] = 'DEEPSEEK_API_KEY'
os.environ['DEEPSEEK_API_KEY'] = 'sk-cb2233a3ea8f475797b414d6d05365d8'
os.environ['MODEL_C'] = 'deepseek-chat'

# 方案 2: 阿里云 DashScope (Qwen 官方)
#os.environ['MODEL_API_BASE_URL'] = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
#os.environ['MODEL_API_KEY_ENV'] = 'DASHSCOPE_API_KEY'
#os.environ['DASHSCOPE_API_KEY'] = 'sk-bf8c6bd3b0364cf1835351ccb25b2806'

# 尝试使用完整的模型名称指定 32B 版本
# 可能的格式（按优先级尝试）：
#os.environ['MODEL_C'] = 'qwen3-coder-30b-a3b-instruct'  # 方式1: 小写格式
# os.environ['MODEL_C'] = 'Qwen2.5-Coder-32B-Instruct'  # 方式2: 标准格式
# os.environ['MODEL_C'] = 'qwen-coder-plus'  # 方式3: 托管版本（可能是32B或更高）

# 💡 说明：
# - qwen-coder-plus: 阿里云托管版本，性能优化，但不确定具体参数规模
# - qwen2.5-coder-32b-instruct: 明确指定32B版本
# - 如果上述名称不工作，阿里云可能只支持简化名称，那么 qwen-coder-plus 可能就是最接近的选择

# 方案 3: 硅基流动 (第三方，明确支持 32B 版本)
#os.environ['MODEL_API_BASE_URL'] = 'https://api.siliconflow.cn/v1'
#os.environ['MODEL_API_KEY_ENV'] = 'SILICONFLOW_API_KEY'
#os.environ['SILICONFLOW_API_KEY'] = 'sk-6e2d56a85bbf4ba6ac45bc5a3ca7126a'
#os.environ['MODEL_C'] = 'Qwen/Qwen2.5-Coder-32B-Instruct'  # 硅基流动明确支持完整版本名

# 💡 提示：也可以通过命令行设置环境变量，无需修改代码
# Windows: 
#   set MODEL_API_BASE_URL=https://api.siliconflow.cn/v1
#   set MODEL_API_KEY_ENV=SILICONFLOW_API_KEY
#   set SILICONFLOW_API_KEY=sk-xxx
#   set MODEL_C=Qwen/Qwen2.5-Coder-32B-Instruct
# Linux/Mac:
#   export MODEL_API_BASE_URL=https://api.siliconflow.cn/v1
#   export MODEL_API_KEY_ENV=SILICONFLOW_API_KEY
#   export SILICONFLOW_API_KEY=sk-xxx
#   export MODEL_C=Qwen/Qwen2.5-Coder-32B-Instruct

# 导入依赖
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from session import Session
from apps_eval.data import get_data, InstanceData
from apps_eval.parallel_runner import eval_code

# 导入角色定义
from roles.rule_descriptions_actc import TEAM, ANALYST, PYTHON_DEVELOPER, TESTER

# 导入全局 LLM（从 backend 中获取）
from core.backend import _GLOBAL_LLM


# ============================================================
# 详细日志系统
# ============================================================

class DetailedLogger:
    """为每个题目创建详细的日志记录"""
    
    def __init__(self, output_dir: str = "baseline_outputs"):
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
    
    def save_round_info(self, problem_dir: Path, round_num: int, 
                       code: str, report: str, role: str):
        """保存每一轮的信息"""
        round_dir = problem_dir / f"round_{round_num}"
        round_dir.mkdir(exist_ok=True)
        
        # 保存代码
        with open(round_dir / f"code_{role}.py", "w", encoding="utf-8") as f:
            f.write(code)
        
        # 保存报告
        with open(round_dir / f"report_{role}.txt", "w", encoding="utf-8") as f:
            f.write(report)
    
    def save_session_history(self, problem_dir: Path, session_history: Dict):
        """保存完整的 session 历史"""
        with open(problem_dir / "session_history.json", "w", encoding="utf-8") as f:
            json.dump(session_history, f, indent=2, ensure_ascii=False)
    
    def save_final_code(self, problem_dir: Path, code: str):
        """保存最终生成的代码"""
        with open(problem_dir / "final_solution.py", "w", encoding="utf-8") as f:
            f.write(code)
    
    def save_summary(self, summary: Dict):
        """保存总体摘要"""
        with open(self.run_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


# ============================================================
# 并行生成器
# ============================================================

def process_single_problem(args: Tuple[InstanceData, int, int, str, Path]) -> Dict:
    """
    处理单个问题的工作函数（用于并行）
    
    Args:
        args: (instance, idx, total, output_dir, run_dir) 元组
    
    Returns:
        包含结果的字典
    """
    instance, idx, total, output_dir, run_dir = args
    
    try:
        # 直接使用传入的 run_dir，不创建新的 logger
        # 为单个问题创建目录
        problem_dir = run_dir / instance.instance_id
        problem_dir.mkdir(exist_ok=True)
        
        # 保存问题描述
        with open(problem_dir / "problem_statement.txt", "w", encoding="utf-8") as f:
            f.write(instance.problem_statement)
        
        print(f"[{idx}/{total}] 开始处理: {instance.instance_id}")
        
        # 初始化 Session（从环境变量读取模型名称）
        model_name = os.environ.get('MODEL_C', 'deepseek-chat')
        
        # 在运行 Session 前记录起始 token 数
        tokens_before = 0
        try:
            from core.backend import _get_llm
            llm = _get_llm()
            if hasattr(llm, 'total_tokens'):
                tokens_before = llm.total_tokens
        except Exception as e:
            pass  # 忽略错误，继续执行
        
        session = Session(
            TEAM=TEAM,
            ANALYST=ANALYST,
            PYTHON_DEVELOPER=PYTHON_DEVELOPER,
            TESTER=TESTER,
            requirement=instance.problem_statement,
            model=model_name,
            majority=1,
            max_tokens=4096,  # 增加token限制，支持更复杂的代码
            temperature=0,  # 轻微增加创造性，帮助跳出局部最优
            top_p=0.95,
            max_round=4,  # 从4增加到6，给更多迭代机会
            before_func=''
        )
        
        # 运行 Session
        code, session_history = session.run_session()
        
        # 获取当前子进程的 token 使用量（计算差值）
        tokens_used = 0
        try:
            # 导入 backend 模块以访问该子进程的 _GLOBAL_LLM
            from core.backend import _get_llm
            llm = _get_llm()
            if hasattr(llm, 'total_tokens'):
                tokens_after = llm.total_tokens
                tokens_used = tokens_after - tokens_before  # 计算本次问题使用的 token 数
                print(f"[{idx}/{total}] 📊 {instance.instance_id} 使用了 {tokens_used} tokens")
        except Exception as e:
            print(f"⚠️  警告: [{idx}/{total}] {instance.instance_id} 获取 token 使用量失败: {e}")
        
        # 保存详细历史
        with open(problem_dir / "session_history.json", "w", encoding="utf-8") as f:
            json.dump(session_history, f, indent=2, ensure_ascii=False)
        
        # 保存每一轮的详细信息
        for round_key, round_data in session_history.items():
            if round_key.startswith('Round_'):
                round_num = int(round_key.split('_')[1])
                if 'code' in round_data:
                    # 创建轮次目录
                    round_dir = problem_dir / f"round_{round_num}"
                    round_dir.mkdir(exist_ok=True)
                    
                    # 保存代码
                    with open(round_dir / f"code_iteration.py", "w", encoding="utf-8") as f:
                        f.write(round_data['code'])
                    
                    # 保存静态分析报告（Tester 的反馈）
                    if 'tester_analysis' in round_data:
                        with open(round_dir / f"tester_analysis.txt", "w", encoding="utf-8") as f:
                            f.write(round_data['tester_analysis'])
                    
                    # 保存状态
                    if 'status' in round_data:
                        with open(round_dir / f"status.txt", "w", encoding="utf-8") as f:
                            f.write(round_data['status'])
        
        # 保存最终代码（添加必要的导入和入口点）
        final_code = code  # 初始化 final_code
        if code and code != "error":
            # 添加必要的导入
            imports_needed = []
            
            if 'import sys' not in final_code and ('sys.' in final_code or 'stdin' in final_code):
                imports_needed.append('import sys')
            
            if 'cmp_to_key' in final_code and 'from functools import' not in final_code:
                imports_needed.append('from functools import cmp_to_key')
            
            if 'math.' in final_code and 'import math' not in final_code:
                imports_needed.append('import math')
            
            if imports_needed:
                final_code = '\n'.join(imports_needed) + '\n\n' + final_code
            
            # 添加入口点
            if 'if __name__' not in final_code:
                if 'def solve()' in final_code:
                    final_code += '\n\nif __name__ == "__main__":\n    solve()'
                elif 'def main()' in final_code:
                    final_code += '\n\nif __name__ == "__main__":\n    main()'
            
            # 保存最终代码
            with open(problem_dir / "final_solution.py", "w", encoding="utf-8") as f:
                f.write(final_code)
            print(f"[{idx}/{total}] ✅ {instance.instance_id} 生成成功")
        else:
            final_code = "# Generation failed"
            print(f"[{idx}/{total}] ❌ {instance.instance_id} 生成失败")
        
        return {
            'instance_id': instance.instance_id,
            'code': final_code,  # 返回补全后的代码或失败标记
            'test_cases': instance.test_cases,
            'session_history': session_history,
            'problem_dir': str(problem_dir),
            'tokens_used': tokens_used
        }
        
    except Exception as e:
        print(f"[{idx}/{total}] ❌ {instance.instance_id} 异常: {e}")
        return {
            'instance_id': instance.instance_id,
            'code': f"# Exception: {e}",
            'test_cases': instance.test_cases,
            'session_history': {},
            'error': str(e),
            'tokens_used': 0
        }


# ============================================================
# 主流程
# ============================================================

def main(parallel: bool = True, workers: int = None, output_dir: str = "baseline_outputs", limit: int = None):
    """
    主函数
    
    Args:
        parallel: 是否使用并行生成（默认 True）
        workers: 并行进程数（默认为 CPU 核心数的一半）
        output_dir: 输出目录
    """
    print("=" * 80)
    print("CodeContests Baseline - Self-collaboration-Code-Generation")
    print("=" * 80)
    
    # 加载数据集
    print("\n[步骤 1/5] 加载 CodeContests 数据集...")
    dataset = get_data('code_contests')
    
    # 如果指定了限制，只取前N个问题
    if limit is not None and limit > 0:
        dataset = dataset[:limit]
        print(f"✅ 加载完成，共 {len(dataset)} 个问题（限制为前 {limit} 个）")
    else:
        print(f"✅ 加载完成，共 {len(dataset)} 个问题")
    
    # 创建日志记录器
    logger = DetailedLogger(output_dir)
    print(f"✅ 输出目录: {logger.run_dir}")
    
    # 确定并行进程数
    if workers is None:
        workers = max(1, cpu_count() // 2)
    
    print(f"\n⚙️  配置信息:")
    print(f"  - 并行模式: {'开启' if parallel else '关闭'}")
    print(f"  - 工作进程数: {workers}")
    print(f"  - CPU 核心数: {cpu_count()}")
    
    # 收集所有生成结果
    all_results = []
    start_time = time.time()
    
    # 主循环：生成代码
    print(f"\n[步骤 2/5] 开始生成代码...")
    print("=" * 80)
    
    if parallel and len(dataset) > 1:
        # 并行生成
        print(f"🚀 使用 {workers} 个进程并行生成...")
        
        # 准备参数（传递统一的 run_dir）
        args_list = [
            (instance, idx + 1, len(dataset), output_dir, logger.run_dir)
            for idx, instance in enumerate(dataset)
        ]
        
        # 并行执行
        with Pool(workers) as pool:
            all_results = pool.map(process_single_problem, args_list)
        
    else:
        # 顺序生成
        print("⏩ 顺序生成模式...")
        for idx, instance in enumerate(dataset):
            result = process_single_problem(
                (instance, idx + 1, len(dataset), output_dir, logger.run_dir)
            )
            all_results.append(result)
    
    generation_time = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"✅ 代码生成完成！")
    print(f"⏱️  生成耗时: {generation_time:.2f} 秒")
    print(f"📈 平均每题: {generation_time / len(dataset):.2f} 秒")
    print("=" * 80)
    
    # 最终评估
    print(f"\n[步骤 3/5] 最终评估所有生成结果...")
    print("=" * 80)
    
    eval_start_time = time.time()
    
    # 准备评估数据
    eval_dataset = []
    eval_solutions = []
    
    for result in all_results:
        # 从原始数据集中找到对应的实例
        instance = next((inst for inst in dataset if inst.instance_id == result['instance_id']), None)
        if instance:
            eval_dataset.append(instance)
            eval_solutions.append(result['code'])
    
    # 确定评估的并行进程数
    # Windows 限制最多 63 个句柄，实际建议更少
    import platform
    if platform.system() == 'Windows':
        eval_workers = min(workers * 2, 8)  # Windows: 最多 8 个进程
    else:
        eval_workers = min(workers * 4, 60)  # Linux/Mac: 最多 60 个进程
    
    print(f"🔍 使用 {eval_workers} 个进程并行评估... (平台: {platform.system()})")
    
    # 调用 eval_code 进行评估
    try:
        eval_results = eval_code(eval_dataset, eval_solutions, timeout=10.0, workers=eval_workers)
        eval_time = time.time() - eval_start_time
        
        print(f"✅ 评估完成！")
        print(f"⏱️  评估耗时: {eval_time:.2f} 秒")
        print(f"📈 平均每题: {eval_time / len(dataset):.2f} 秒")
        
    except Exception as e:
        print(f"\n❌ 评估过程出错: {e}")
        print(f"⚠️  已生成的代码已保存在: {logger.run_dir}")
        print(f"💡 提示: 可以使用恢复脚本完成评估:")
        print(f"   python recover_and_eval.py --run-dir {logger.run_dir}")
        raise  # 重新抛出异常
    
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
    print(f"\n[步骤 4/5] 统计结果...")
    print("=" * 80)
    
    total_problems = len(eval_results)
    passed = sum(1 for acc_rate, _ in eval_results if acc_rate == 1.0)
    pass_at_1 = (passed / total_problems * 100) if total_problems > 0 else 0.0
    
    total_time = time.time() - start_time
    
    # 从所有结果中汇总 token 使用量
    total_tokens = 0
    for result in all_results:
        total_tokens += result.get('tokens_used', 0)
    
    if total_tokens == 0:
        print("⚠️  注意: 未能统计到 Token 使用量")
    else:
        print(f"✅ 成功汇总所有子进程的 Token 使用量")
    
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
        print(f"🔢 总 Token 使用量: N/A (未能统计到 token 使用量)")
    
    print("=" * 80)
    
    # 保存结果到文件
    print(f"\n[步骤 5/5] 保存结果...")
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
            'tokens_used': result.get('tokens_used', 0),
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
            'session_history': result.get('session_history', {})
        })
    
    # 保存到 run 目录
    summary = {
        'summary': {
            'pass_at_1': pass_at_1,
            'passed': passed,
            'total': total_problems,
            'time_cost': {
                'total': total_time,
                'generation': generation_time,
                'evaluation': eval_time
            },
            'token_usage': {
                'total': total_tokens if total_tokens > 0 else 'N/A',
                'average_per_problem': total_tokens / total_problems if (total_problems > 0 and total_tokens > 0) else 'N/A',
                'per_problem_details': [r.get('tokens_used', 0) for r in all_results]
            },
            'config': {
                'parallel': parallel,
                'workers': workers,
                'eval_workers': eval_workers
            },
            'timestamp': datetime.now().isoformat()
        },
        'results': detailed_results
    }
    
    logger.save_summary(summary)
    
    # 也保存到根目录（兼容旧版）
    output_file = "baseline_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 详细结果已保存到: {logger.run_dir}")
    print(f"✅ 摘要已保存到: {output_file}")
    print(f"✅ 每个问题的详细日志: {logger.run_dir}/<problem_id>/")
    
    # 生成可读的摘要报告
    report_file = logger.run_dir / "REPORT.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("CodeContests Baseline 运行报告\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"数据集: CodeContests\n")
        f.write(f"题目数量: {total_problems}\n\n")
        f.write(f"配置信息:\n")
        f.write(f"  - 并行模式: {'开启' if parallel else '关闭'}\n")
        f.write(f"  - 生成进程数: {workers}\n")
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
            f.write(f"  - 总 Token: N/A (未能统计到 token 使用量)\n\n")
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
    
    parser = argparse.ArgumentParser(description='CodeContests Baseline Runner')
    parser.add_argument('--parallel', action='store_true', default=True,
                       help='使用并行生成（默认开启）')
    parser.add_argument('--sequential', action='store_true',
                       help='使用顺序生成（覆盖 --parallel）')
    parser.add_argument('--workers', type=int, default=None,
                       help='并行进程数（默认为 CPU 核心数的一半）')
    parser.add_argument('--output-dir', type=str, default='baseline_outputs',
                       help='输出目录（默认: baseline_outputs）')
    parser.add_argument('--limit', type=int, default=None,
                       help='限制处理的问题数量（用于测试，如: --limit 5）')
    
    args = parser.parse_args()
    
    # 如果指定了 sequential，则关闭并行
    parallel = not args.sequential if args.sequential else args.parallel
    
    main(parallel=parallel, workers=args.workers, output_dir=args.output_dir, limit=args.limit)
