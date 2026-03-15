"""任务调度器模块 - 管理异步任务队列"""

import asyncio
import inspect
import logging
from dataclasses import dataclass
from typing import Any, Callable, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class TaskItem(Generic[T]):
    func: "Callable[..., T]"
    args: "tuple[Any, ...]"
    kwargs: "dict[str, Any]"
    future: "asyncio.Future[T]"


class TaskScheduler:
    def __init__(self, max_workers: int = 3):
        self._max_workers: int = max_workers
        self._queue: "asyncio.Queue[TaskItem[Any]]" = asyncio.Queue()
        self._workers: list["asyncio.Task[None]"] = []
        self._running: bool = False
        self._stop_event: asyncio.Event = asyncio.Event()

    @property
    def is_running(self) -> bool:
        return self._running

    async def enqueue(
        self, func: "Callable[..., T]", *args: Any, **kwargs: Any
    ) -> "asyncio.Future[T]":
        if not self._running and not self._stop_event.is_set():
            raise RuntimeError("调度器未启动，请先调用 start() 方法")

        future: asyncio.Future[T] = asyncio.get_event_loop().create_future()  # type: ignore[attr-defined]

        task_item = TaskItem(
            func=func,
            args=args,
            kwargs=kwargs,
            future=future
        )

        await self._queue.put(task_item)
        logger.debug(f"任务已入队: {func.__name__}")

        return future

    async def start(self) -> None:
        if self._running:
            logger.warning("调度器已在运行中")
            return

        self._running = True
        self._stop_event.clear()

        for i in range(self._max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

        logger.info(f"调度器已启动，使用 {self._max_workers} 个工作线程")

    async def stop(self) -> None:
        if not self._running:
            return

        self._running = False

        await self._queue.join()

        self._stop_event.set()

        for worker in self._workers:
            worker.cancel()

        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()
        self._stop_event.clear()

        logger.info("调度器已停止")

    async def _worker(self, worker_id: int) -> None:
        logger.debug(f"工作线程 {worker_id} 已启动")

        while not self._stop_event.is_set():
            try:
                task_item = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                func = task_item.func
                args = task_item.args
                kwargs = task_item.kwargs

                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = await asyncio.to_thread(func, *args, **kwargs)

                if not task_item.future.done():
                    task_item.future.set_result(result)

                logger.debug(f"工作线程 {worker_id} 完成任务: {func.__name__}")

            except asyncio.CancelledError:
                if not task_item.future.done():
                    task_item.future.cancel()
                raise

            except Exception as e:
                logger.exception(f"工作线程 {worker_id} 执行任务时发生异常: {e}")
                if not task_item.future.done():
                    task_item.future.set_exception(e)

            finally:
                self._queue.task_done()

        logger.debug(f"工作线程 {worker_id} 已停止")

    def get_queue_size(self) -> int:
        return self._queue.qsize()

    def get_worker_count(self) -> int:
        return len(self._workers)
