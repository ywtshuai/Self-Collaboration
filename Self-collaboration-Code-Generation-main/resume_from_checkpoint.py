"""
从评估检查点恢复统计
当评估完成但统计阶段出错时，使用此脚本恢复
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apps_eval.data import get_data


def main():
    print("=" * 80)
    print("从评估检查点恢复统计")
    print("=" * 80)
    
    # 查找最新的运行目录
    baseline_outputs = Path("baseline_outputs")
    if not baseline_outputs.exists():
        print("❌ 错误: baseline_outputs 目录不存在")
        return
    
    run_dirs = sorted([d for d in baseline_outputs.iterdir() 
                      if d.is_dir() and d.name.startswith('run_')])
    
    if not run_dirs:
        print("❌ 错误: 没有找到任何运行目录")
        return
    
    run_dir = run_dirs[-1]
    print(f"🔍 运行目录: {run_dir}")
    
    # 加载检查点
    checkpoint_file = run_dir / "eval_checkpoint.json"
    if not checkpoint_file.exists():
        print(f"❌ 错误: 未找到检查点文件: {checkpoint_file}")
        print("提示: 此脚本只能用于评估完成但统计阶段出错的情况")
        return
    
    print(f"📂 加载检查点: {checkpoint_file}")
    with open(checkpoint_file, 'r', encoding='utf-8') as f:
        checkpoint = json.load(f)
    
    eval_results_data = checkpoint['eval_results']
    eval_time = checkpoint.get('eval_time', 0.0)
    eval_workers = checkpoint.get('eval_workers', 0)
    
    print(f"✅ 检查点加载成功")
    print(f"   - 评估结果数: {len(eval_results_data)}")
    print(f"   - 评估耗时: {eval_time:.2f} 秒")
    print(f"   - 使用进程数: {eval_workers}")
    
    # 统计结果
    print(f"\n[统计] 计算 Pass@1...")
    print("=" * 80)
    
    total_problems = len(eval_results_data)
    passed = sum(1 for r in eval_results_data if r.get('passed', False))
    pass_at_1 = (passed / total_problems * 100) if total_problems > 0 else 0.0
    
    # 打印结果
    print(f"\n📊 最终结果")
    print("=" * 80)
    print(f"✅ Pass@1: {pass_at_1:.2f}% ({passed}/{total_problems})")
    print(f"⏱️  评估耗时: {eval_time:.2f} 秒")
    print(f"📈 平均每题: {eval_time / total_problems:.2f} 秒")
    print("=" * 80)
    
    # 保存最终结果
    print(f"\n💾 保存最终结果...")
    
    summary = {
        'summary': {
            'pass_at_1': pass_at_1,
            'passed': passed,
            'total': total_problems,
            'time_cost': {
                'evaluation': eval_time
            },
            'token_usage': {
                'total': 0,  # 从检查点恢复无法获取
                'note': 'Token usage not available from checkpoint'
            },
            'config': {
                'eval_workers': eval_workers
            },
            'timestamp': datetime.now().isoformat(),
            'recovered_from_checkpoint': True
        },
        'results': eval_results_data
    }
    
    # 保存到运行目录
    summary_file = run_dir / "summary_recovered.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 结果已保存到: {summary_file}")
    
    # 生成报告
    report_file = run_dir / "REPORT_RECOVERED.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("恢复的评估报告\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"恢复时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"原始运行目录: {run_dir}\n")
        f.write(f"题目数量: {total_problems}\n\n")
        f.write(f"结果统计:\n")
        f.write(f"  - Pass@1: {pass_at_1:.2f}% ({passed}/{total_problems})\n")
        f.write(f"  - 评估耗时: {eval_time:.2f} 秒\n\n")
        f.write(f"详细结果:\n")
        for r in eval_results_data:
            status = "✅ PASS" if r.get('passed') else "❌ FAIL"
            acc = r.get('accuracy', 0.0) * 100
            passed_tests = r.get('passed_tests', 0)
            test_count = r.get('test_count', 0)
            f.write(f"  {status} {r['instance_id']} ({passed_tests}/{test_count} tests, {acc:.0f}%)\n")
    
    print(f"✅ 报告已保存到: {report_file}")
    
    # 同时保存到根目录
    root_result = "baseline_results_recovered.json"
    with open(root_result, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 结果副本: {root_result}")
    
    print("\n" + "=" * 80)
    print("🎉 统计完成！")
    print("=" * 80)


if __name__ == '__main__':
    main()
