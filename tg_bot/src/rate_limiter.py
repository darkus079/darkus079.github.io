from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, Tuple

from loguru import logger

from config import settings


class GlobalDailyCounter:
    def __init__(self):
        self.reset_ts = self._day_start()
        self.global_count = 0
        self.user_count: Dict[int, int] = defaultdict(int)

    def _day_start(self) -> int:
        t = time.gmtime()
        return int(time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1)))

    def _ensure_day(self) -> None:
        if time.time() - self.reset_ts >= 86400:
            self.reset_ts = self._day_start()
            self.global_count = 0
            self.user_count.clear()

    def try_consume(self, user_id: int, n: int = 1) -> Tuple[bool, str]:
        self._ensure_day()
        if self.global_count + n > settings.GLOBAL_DAILY_LIMIT:
            return False, "Глобальный дневной лимит исчерпан. Попробуйте завтра."
        if self.user_count[user_id] + n > settings.PER_USER_DAILY_LIMIT:
            return False, "Ваш дневной лимит исчерпан. Попробуйте завтра."
        self.global_count += n
        self.user_count[user_id] += n
        return True, ""


global_counter = GlobalDailyCounter()


