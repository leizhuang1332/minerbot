"""MinerBot 主程序入口

提供 CLI 界面启动应用服务和交互式 REPL。
"""
import argparse
import asyncio
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.app import Config, REPL, Service


WELCOME_MESSAGE = """========================================
  欢迎使用 MinerBot
  AI Assistant built with LangChain DeepAgents
========================================

输入您的消息与 AI 助手交互。
输入 'exit' 或 'quit' 退出程序。

"""

GOODBYE_MESSAGE = """========================================
  再见！感谢使用 MinerBot
========================================
"""


def parse_args() -> argparse.Namespace:
    """解析命令行参数
    
    Returns:
        解析后的参数对象
    """
    parser = argparse.ArgumentParser(
        prog="minerbot",
        description="MinerBot - AI Assistant built with LangChain DeepAgents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config/app_config.yaml",
        help="指定配置文件路径 (默认: config/app_config.yaml)",
    )
    
    return parser.parse_args()


def load_config(config_path: str) -> Config:
    """加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        Config 实例
        
    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置验证失败
    """
    # 将相对路径转换为绝对路径（相对于项目根目录）
    path = Path(config_path)
    if not path.is_absolute():
        path = project_root / path
    
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    
    # 使用 Config 的加载机制
    config = Config.load()
    return config


async def async_main(args: argparse.Namespace) -> None:
    """异步主函数
    
    Args:
        args: 解析后的命令行参数
    """
    # 1. 加载配置
    config = load_config(args.config)
    
    # 2. 创建服务实例
    service = Service(config)
    
    # 3. 显示欢迎信息
    print(WELCOME_MESSAGE)
    
    # 4. 启动服务
    await service.start()
    
    # 5. 创建并运行 REPL
    repl = REPL(service)
    await repl.run()
    
    # 6. 停止服务
    await service.stop()
    
    # 7. 显示 goodbye 信息
    print(GOODBYE_MESSAGE)


def main() -> int:
    """主函数
    
    Returns:
        退出码
    """
    try:
        # 解析命令行参数
        args = parse_args()
        
        # 运行异步主函数
        asyncio.run(async_main(args))
        
        return 0
        
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n程序被用户中断", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"发生错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
