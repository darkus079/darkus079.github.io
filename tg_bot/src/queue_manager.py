from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any

from loguru import logger

from parser_service import parser_service
from config import settings


@dataclass
class TaskInfo:
    user_id: int
    case_number: str
    created_at: float
    task: asyncio.Task
    cancelled: bool = False


class QueueManager:
    def __init__(self) -> None:
        self._tasks: Dict[int, TaskInfo] = {}
        self._lock = asyncio.Lock()
        self._history: List[Dict[str, Any]] = []

    def has_active(self, user_id: int) -> bool:
        return user_id in self._tasks and not self._tasks[user_id].task.done()

    async def cancel(self, user_id: int) -> bool:
        async with self._lock:
            info = self._tasks.get(user_id)
            if not info:
                return False
            info.cancelled = True
            info.task.cancel()
            return True

    async def submit(self, user_id: int, case_number: str, on_update) -> None:
        async with self._lock:
            if user_id in self._tasks and not self._tasks[user_id].task.done():
                raise RuntimeError("У вас уже есть активная задача")

            loop = asyncio.get_running_loop()
            task = loop.create_task(self._run_task(user_id, case_number, on_update))
            self._tasks[user_id] = TaskInfo(
                user_id=user_id, case_number=case_number, created_at=loop.time(), task=task
            )

    async def _run_task(self, user_id: int, case_number: str, on_update) -> None:
        # Use local parser service
        try:
            await on_update(f"Запуск парсинга: {case_number}")
            # Collect links using local selenium in a thread
            loop = asyncio.get_running_loop()
            links = await parser_service.collect_links(
                case_number,
                on_progress=lambda s, _loop=loop: asyncio.run_coroutine_threadsafe(on_update(s), _loop),
            )
            if not links:
                await on_update("Ссылки не найдены")
                self._history.append({
                    "user_id": user_id,
                    "case_number": case_number,
                    "success": False,
                    "links_count": 0,
                })
                return
            # Пакетно отправляем в on_update как итог
            await on_update(f"Готово. Найдено ссылок: {len(links)}")
            # Возвращаем список через тот же callback (маркер [RESULT])
            await on_update({"type": "result_links", "case": case_number, "links": links})
            self._history.append({
                "user_id": user_id,
                "case_number": case_number,
                "success": True,
                "links_count": len(links),
            })

        except asyncio.CancelledError:
            await on_update("Задача отменена пользователем")
            self._history.append({
                "user_id": user_id,
                "case_number": case_number,
                "success": False,
                "links_count": 0,
                "cancelled": True,
            })
        except Exception as e:
            logger.exception("Ошибка задачи парсинга")
            await on_update(f"Ошибка: {e}")
            self._history.append({
                "user_id": user_id,
                "case_number": case_number,
                "success": False,
                "links_count": 0,
                "error": str(e),
            })

    def get_user_status(self, user_id: int) -> Optional[str]:
        info = self._tasks.get(user_id)
        if info and not info.task.done():
            return info.case_number
        return None

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(self._history[-limit:])


queue_manager = QueueManager()


