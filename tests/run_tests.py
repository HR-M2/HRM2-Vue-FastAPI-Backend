#!/usr/bin/env python
"""
一键运行测试脚本

可在任意路径双击运行，自动使用当前 Python 环境执行测试
"""
import os
import sys
import subprocess


def main():
    # 获取脚本所在目录和项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # 切换到项目根目录
    os.chdir(project_root)
    
    print(f"项目目录: {project_root}")
    print(f"Python 环境: {sys.executable}")
    print("-" * 60)
    
    # 构建 pytest 命令，使用当前 Python 解释器
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]
    
    # 检查命令行参数，支持传递额外的 pytest 参数
    if len(sys.argv) > 1:
        # 如果用户传入参数，替换默认的测试路径
        cmd = [sys.executable, "-m", "pytest"] + sys.argv[1:]
    
    print(f"执行命令: {' '.join(cmd)}")
    print("=" * 60)
    
    # 执行测试
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
