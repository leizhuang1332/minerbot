"""REPL 模块 - 交互式命令行界面"""

import asyncio

from src.app.service import Service


class REPL:
    """REPL (Read-Eval-Print Loop) 交互式命令行界面
    
    提供一个简单的交互式界面，让用户可以直接与 Agent 交互。
    支持打字机效果的流式输出。
    
    Example:
        service = Service(config)
        await service.start()
        
        repl = REPL(service)
        await repl.run()
        
        await service.stop()
    """
    
    MAX_INPUT_LENGTH: int = 10000
    
    def __init__(self, service: Service, streaming: bool = True) -> None:
        """初始化 REPL
        
        Args:
            service: Service 实例，用于处理用户输入
            streaming: 是否使用流式输出（打字机效果），默认 True
        """
        self._service: Service = service
        self._running: bool = False
        self._streaming: bool = streaming
    
    def _stream_callback(self, text: str) -> None:
        """流式输出回调 - 实时打印文本"""
        print(text, end="", flush=True)
    
    async def run(self) -> None:
        """运行 REPL 主循环
        
        持续读取用户输入，调用 Agent 处理，并输出结果。
        支持 'exit' 或 'quit' 命令退出。
        """
        self._running = True
        
        while self._running:
            try:
                # 读取用户输入
                user_input = input(">>> ")
                
                # 处理空输入
                if not user_input.strip():
                    continue
                
                # 处理退出命令
                if user_input.strip().lower() in ("exit", "quit"):
                    self._running = False
                    print("再见!")
                    continue
                
                # 处理超长输入
                if len(user_input) > self.MAX_INPUT_LENGTH:
                    print(f"输入过长，最多支持 {self.MAX_INPUT_LENGTH} 个字符")
                    continue
                
                # 根据 streaming 设置选择调用方式
                if self._streaming:
                    # 流式输出（打字机效果）
                    print("🤖: ", end="")
                    result = await self._service.stream_run(
                        user_input,
                        callback=self._stream_callback
                    )
                    print()  # 换行
                else:
                    # 非流式输出
                    result = await self._service.run(user_input)
                    print(f"🤖: {result}")
                
            except KeyboardInterrupt:
                print("\n使用 'exit' 或 'quit' 命令退出")
                continue
            except EOFError:
                self._running = False
                print("\n再见!")
                break

from src.app.service import Service


# class REPL:
#     """REPL (Read-Eval-Print Loop) 交互式命令行界面
    
#     提供一个简单的交互式界面，让用户可以直接与 Agent 交互。
    
#     Example:
#         service = Service(config)
#         await service.start()
        
#         repl = REPL(service)
#         await repl.run()
        
#         await service.stop()
#     """
    
#     MAX_INPUT_LENGTH: int = 10000
    
#     def __init__(self, service: Service) -> None:
#         """初始化 REPL
        
#         Args:
#             service: Service 实例，用于处理用户输入
#         """
#         self._service: Service = service
#         self._running: bool = False
    
#     async def run(self) -> None:
#         """运行 REPL 主循环
        
#         持续读取用户输入，调用 Agent 处理，并输出结果。
#         支持 'exit' 或 'quit' 命令退出。
#         """
#         self._running = True
        
#         while self._running:
#             try:
#                 # 读取用户输入
#                 user_input = input(">>> ")
                
#                 # 处理空输入
#                 if not user_input.strip():
#                     continue
                
#                 # 处理退出命令
#                 if user_input.strip().lower() in ("exit", "quit"):
#                     self._running = False
#                     print("再见!")
#                     continue
                
#                 # 处理超长输入
#                 if len(user_input) > self.MAX_INPUT_LENGTH:
#                     print(f"输入过长，最多支持 {self.MAX_INPUT_LENGTH} 个字符")
#                     continue
                
#                 # 调用服务处理输入
#                 result = await self._service.run(user_input)
                
#                 # 输出结果
#                 print(result)
                
#             except KeyboardInterrupt:
#                 print("\n使用 'exit' 或 'quit' 命令退出")
#                 continue
#             except EOFError:
#                 self._running = False
#                 print("\n再见!")
#                 break
