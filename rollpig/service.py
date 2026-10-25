"""抽取用例：当天记录优先，未抽过则随机发放。"""

from __future__ import annotations

import random
from datetime import date
from typing import Callable, Sequence

from .models import Pig
from .repository import PigRepository
from .storage import BoardStore


class RollPigService:
    """「今日小猪」业务用例。

    时间源与随机源均可注入，便于测试每日刷新与抽签逻辑。
    """

    def __init__(
        self,
        store: BoardStore,
        repository: PigRepository,
        *,
        chooser: Callable[[Sequence[Pig]], Pig] | None = None,
        clock: Callable[[], date] | None = None,
    ) -> None:
        self._store = store
        self._repository = repository
        self._chooser = chooser or random.choice
        self._clock = clock or date.today

    def draw(self, user_id: str) -> Pig | None:
        """为用户抽取今日小猪；当天已抽过则直接返回原结果，资源为空时返回 ``None``。"""
        board = self._store.load(self._clock().isoformat())

        cached = board.get(user_id)
        if cached is not None:
            return cached

        if not self._repository:
            return None

        pig = self._chooser(self._repository.pigs)
        board.put(user_id, pig)
        self._store.save(board)
        return pig
