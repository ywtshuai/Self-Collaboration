"""
数据准备脚本：下载并转换 CodeContests 数据集
从 Hugging Face 下载 deepmind/code_contests 数据集，并转换为 apps_eval 兼容格式
"""
import os

# ==========================================
# 核心修复：强制将缓存路径设置到 E 盘
# ⚠️ 必须在 import datasets 之前设置！
# ==========================================
os.environ["HF_HOME"] = "E:/huggingface_cache"
os.environ["HF_DATASETS_CACHE"] = "E:/huggingface_cache/datasets"

# 创建目录确保存在
os.makedirs(os.environ["HF_DATASETS_CACHE"], exist_ok=True)
print(f"✓ 缓存目录已设置为: {os.environ['HF_DATASETS_CACHE']}")

# 现在才导入 datasets 库
import json
from typing import List, Dict, Any
from datasets import load_dataset
from tqdm import tqdm


def merge_test_cases(public_tests: Dict, private_tests: Dict) -> Dict[str, List]:
    """
    合并 public 和 private 测试用例为统一格式
    
    Args:
        public_tests: 公开测试用例 {'input': [...], 'output': [...]}
        private_tests: 私有测试用例 {'input': [...], 'output': [...]}
    
    Returns:
        合并后的测试用例 {'inputs': [...], 'outputs': [...]}
    """
    all_inputs = []
    all_outputs = []
    
    # 合并公开测试用例
    if public_tests and 'input' in public_tests and 'output' in public_tests:
        all_inputs.extend(public_tests['input'])
        all_outputs.extend(public_tests['output'])
    
    # 合并私有测试用例
    if private_tests and 'input' in private_tests and 'output' in private_tests:
        all_inputs.extend(private_tests['input'])
        all_outputs.extend(private_tests['output'])
    
    return {
        'inputs': all_inputs,
        'outputs': all_outputs
    }


def extract_python_solutions(solutions: Dict) -> Dict[str, List]:
    """
    提取 Python3 解答 (language=3 表示 Python3)
    
    Args:
        solutions: 原始 solutions 字典 {'language': [...], 'solution': [...]}
    
    Returns:
        过滤后的 Python3 解答
    """
    if not solutions or 'language' not in solutions or 'solution' not in solutions:
        return {'language': [], 'solution': []}
    
    python_solutions = {'language': [], 'solution': []}
    
    for lang, sol in zip(solutions['language'], solutions['solution']):
        if lang == 3:  # Python3
            python_solutions['language'].append(lang)
            python_solutions['solution'].append(sol)
    
    return python_solutions


def download_and_convert_codecontests():
    """
    下载 CodeContests 数据集并转换为指定格式
    """
    print("=" * 60)
    print("开始下载 CodeContests 数据集...")
    print("=" * 60)
    
    # 创建输出目录
    output_dir = "./Datasets"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "code_contests.jsonl")
    
    # 从 Hugging Face 下载数据集
    try:
        dataset = load_dataset("deepmind/code_contests", split="test", trust_remote_code=True)
        print(f"✓ 成功下载数据集，共 {len(dataset)} 个问题")
    except Exception as e:
        print(f"✗ 下载失败: {e}")
        print("提示：请确保已安装 datasets 库 (pip install datasets)")
        return
    
    print("\n开始转换数据格式...")
    
    converted_count = 0
    skipped_count = 0
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, item in enumerate(tqdm(dataset, desc="转换进度")):
            try:
                # 提取测试用例
                public_tests = item.get('public_tests', {})
                private_tests = item.get('private_tests', {})
                all_test_cases = merge_test_cases(public_tests, private_tests)
                
                # 如果没有测试用例，跳过
                if not all_test_cases['inputs']:
                    skipped_count += 1
                    continue
                
                # 提取 Python3 解答
                solutions = extract_python_solutions(item.get('solutions', {}))
                
                # 构建转换后的数据项
                converted_item = {
                    'problem_id': item.get('name', f"code_contests_{idx}"),
                    'description': item.get('description', ''),
                    'all_test_cases': all_test_cases,
                    'solutions': solutions
                }
                
                # 写入 JSONL 文件
                f.write(json.dumps(converted_item, ensure_ascii=False) + '\n')
                converted_count += 1
                
            except Exception as e:
                print(f"\n警告：处理第 {idx} 个问题时出错: {e}")
                skipped_count += 1
                continue
    
    print("\n" + "=" * 60)
    print("数据转换完成！")
    print("=" * 60)
    print(f"✓ 成功转换: {converted_count} 个问题")
    print(f"✗ 跳过问题: {skipped_count} 个")
    print(f"✓ 输出文件: {output_file}")
    print("=" * 60)


def verify_data():
    """
    验证生成的数据文件格式
    """
    output_file = "./Datasets/code_contests.jsonl"
    
    if not os.path.exists(output_file):
        print("✗ 数据文件不存在，请先运行下载")
        return
    
    print("\n验证数据文件...")
    
    with open(output_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"总共 {len(lines)} 条数据")
        
        if lines:
            # 显示第一条数据示例
            first_item = json.loads(lines[0])
            print("\n第一条数据示例：")
            print(f"- problem_id: {first_item['problem_id']}")
            print(f"- description 长度: {len(first_item['description'])} 字符")
            print(f"- 测试用例数量: {len(first_item['all_test_cases']['inputs'])}")
            print(f"- Python3 解答数量: {len(first_item['solutions']['solution'])}")
            
            # 显示测试用例结构
            if first_item['all_test_cases']['inputs']:
                print(f"\n测试用例结构示例:")
                print(f"  Input: {first_item['all_test_cases']['inputs'][0][:100]}...")
                print(f"  Output: {first_item['all_test_cases']['outputs'][0][:100]}...")
    
    print("\n✓ 数据格式验证完成")


if __name__ == "__main__":
    # 下载并转换数据集
    download_and_convert_codecontests()
    
    # 验证数据
    verify_data()
