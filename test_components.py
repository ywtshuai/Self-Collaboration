"""
环境验证测试脚本
用于检查 Baseline 运行所需的所有组件是否正常
"""

import sys
import os

print("=" * 60)
print("环境验证测试")
print("=" * 60)

# 1. 检查 Python 版本
print(f"\n[1/7] Python 版本")
print(f"  ✓ Python {sys.version.split()[0]}")
if sys.version_info < (3, 8):
    print("  ⚠️  警告: 建议使用 Python 3.8 或更高版本")

# 2. 检查依赖包
print(f"\n[2/7] 依赖包检查")
required_packages = {
    'requests': 'pip install requests',
    'tqdm': 'pip install tqdm (可选，用于进度条)',
}

for package, install_cmd in required_packages.items():
    try:
        __import__(package)
        print(f"  ✓ {package} 已安装")
    except ImportError:
        print(f"  ✗ {package} 未安装")
        print(f"    安装命令: {install_cmd}")

# 3. 检查 API Key
print(f"\n[3/7] API Key 检查")
api_key = os.getenv('DEEPSEEK_API_KEY')
if api_key:
    print(f"  ✓ DEEPSEEK_API_KEY 已设置")
    print(f"    前缀: {api_key[:10]}...")
else:
    print(f"  ✗ DEEPSEEK_API_KEY 未设置")
    print(f"    设置方法:")
    print(f"      PowerShell: $env:DEEPSEEK_API_KEY=\"sk-your-key\"")
    print(f"      CMD: set DEEPSEEK_API_KEY=sk-your-key")

# 4. 检查数据集
print(f"\n[4/7] 数据集检查")
dataset_path = 'Datasets/code_contests.jsonl'
if os.path.exists(dataset_path):
    file_size = os.path.getsize(dataset_path) / (1024 * 1024)  # MB
    print(f"  ✓ 数据集文件存在")
    print(f"    路径: {dataset_path}")
    print(f"    大小: {file_size:.2f} MB")
    
    # 尝试读取第一行验证格式
    try:
        import json
        with open(dataset_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            data = json.loads(first_line)
            if 'problem_id' in data and 'description' in data:
                print(f"  ✓ 数据集格式正确")
            else:
                print(f"  ⚠️  警告: 数据集格式可能不正确")
    except Exception as e:
        print(f"  ⚠️  警告: 无法解析数据集: {e}")
else:
    print(f"  ✗ 数据集文件不存在")
    print(f"    期望路径: {dataset_path}")

# 5. 检查源代码文件
print(f"\n[5/7] 源代码文件检查")
required_files = {
    'Self-collaboration-Code-Generation-main/core/backend.py': '核心后端',
    'Self-collaboration-Code-Generation-main/roles/rule_descriptions_actc.py': '角色定义',
    'Self-collaboration-Code-Generation-main/main.py': '主程序',
    'Self-collaboration-Code-Generation-main/session.py': '会话管理',
    'generate_code.py': 'LLM 客户端',
    'apps_eval/data.py': '数据加载',
    'apps_eval/executor.py': '代码执行',
    'apps_eval/parallel_runner.py': '并行评估',
}

all_files_exist = True
for file_path, description in required_files.items():
    if os.path.exists(file_path):
        print(f"  ✓ {description}: {file_path}")
    else:
        print(f"  ✗ {description}: {file_path} (缺失)")
        all_files_exist = False

# 6. 测试 LLM 连接
print(f"\n[6/7] LLM 连接测试")
if api_key and all_files_exist:
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from generate_code import build_llm
        
        print(f"  → 初始化 LLM 客户端...")
        llm = build_llm("MODEL_C", temperature=0.0, max_tokens=50)
        
        print(f"  → 发送测试请求...")
        response = llm.chat([{"role": "user", "content": "Reply with: OK"}])
        
        if response and len(response.strip()) > 0:
            print(f"  ✓ LLM 连接成功")
            print(f"    响应: {response[:50]}...")
            print(f"    Token 使用: {llm.total_tokens}")
        else:
            print(f"  ✗ LLM 返回空响应")
    except Exception as e:
        print(f"  ✗ LLM 连接失败")
        print(f"    错误: {str(e)[:100]}")
else:
    print(f"  ⊘ 跳过测试（API Key 未设置或文件缺失）")

# 7. 测试数据加载
print(f"\n[7/7] 数据加载测试")
if os.path.exists(dataset_path) and all_files_exist:
    try:
        from apps_eval.data import get_data
        
        print(f"  → 加载数据集...")
        dataset = get_data('code_contests')
        
        print(f"  ✓ 数据加载成功")
        print(f"    问题数量: {len(dataset)}")
        if len(dataset) > 0:
            first = dataset[0]
            print(f"    第一个问题:")
            print(f"      ID: {first.instance_id}")
            print(f"      描述长度: {len(first.problem_statement)} 字符")
            print(f"      测试用例数: {len(first.test_cases.get('inputs', []))}")
    except Exception as e:
        print(f"  ✗ 数据加载失败")
        print(f"    错误: {str(e)[:100]}")
else:
    print(f"  ⊘ 跳过测试（数据集不存在或文件缺失）")

# 总结
print("\n" + "=" * 60)
print("验证总结")
print("=" * 60)

if api_key and all_files_exist and os.path.exists(dataset_path):
    print("✅ 所有组件就绪，可以运行 Baseline！")
    print("\n运行命令:")
    print("  cd Self-collaboration-Code-Generation-main")
    print("  python main.py")
else:
    print("⚠️  部分组件存在问题，请检查上述输出并修复")
    if not api_key:
        print("  - 需要设置 DEEPSEEK_API_KEY")
    if not all_files_exist:
        print("  - 需要确保所有源代码文件存在")
    if not os.path.exists(dataset_path):
        print("  - 需要准备数据集文件")

print("=" * 60)
