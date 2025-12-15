#!/usr/bin/env python
"""
HRM2 FastAPI 后端启动脚本

用法:
    python run.py                    # 默认启动 (127.0.0.1:8000)
    python run.py -p 8080            # 指定端口
    python run.py --host 0.0.0.0     # 允许外网访问
    python run.py --reload           # 开启热重载
"""
import argparse
import sys
import os
from pathlib import Path

# 确保项目根目录在 Python 路径中
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="HRM2 FastAPI 后端启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=8000,
        help="服务端口 (默认: 8000)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="服务地址 (默认: 127.0.0.1)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="开启热重载 (开发模式)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="工作进程数 (默认: 1)"
    )
    return parser.parse_args()


def check_env():
    """检查环境配置"""
    env_file = ROOT_DIR / ".env"
    env_example = ROOT_DIR / ".env.example"
    
    if not env_file.exists():
        if env_example.exists():
            print("⚠️  未找到 .env 文件，正在从 .env.example 创建...")
            import shutil
            shutil.copy(env_example, env_file)
            print("✅ .env 文件已创建，请根据需要修改配置")
        else:
            print("⚠️  未找到 .env 文件，将使用默认配置")
    
    # 创建数据目录
    data_dir = ROOT_DIR / "data"
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
        print(f"✅ 数据目录已创建: {data_dir}")


def main():
    """主函数"""
    args = parse_args()
    
    print("=" * 50)
    print("  HRM2 FastAPI 后端服务")
    print("=" * 50)
    
    # 检查环境
    check_env()
    
    print(f"\n🚀 启动服务...")
    print(f"   地址: http://{args.host}:{args.port}")
    print(f"   文档: http://{args.host}:{args.port}/docs")
    print(f"   热重载: {'开启' if args.reload else '关闭'}")
    print(f"   工作进程: {args.workers}")
    print("\n" + "-" * 50 + "\n")
    
    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if not args.reload else 1,
            log_level="info",
        )
    except ImportError:
        print("❌ 错误: 未安装 uvicorn，请运行: pip install uvicorn[standard]")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 服务已停止")


if __name__ == "__main__":
    main()
