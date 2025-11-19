from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional
from loguru import logger

# Import parser from backend
from backend.parser_simplified import KadArbitrParser  # type: ignore


class ParserService:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def collect_links(self, case_number: str, on_progress: Optional[Callable[[str], None]] = None) -> List[Dict[str, Any]]:
        # Run blocking selenium logic in thread executor to avoid blocking event loop
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._collect_links_blocking, case_number, on_progress)

    def _collect_links_blocking(self, case_number: str, on_progress: Optional[Callable[[str], None]]) -> List[Dict[str, Any]]:
        parser = KadArbitrParser()
        try:
            if on_progress:
                on_progress("Инициализация браузера...")
            links = parser.collect_document_links(case_number)
            return links or []
        finally:
            try:
                parser.close()
            except Exception:
                pass


parser_service = ParserService()


