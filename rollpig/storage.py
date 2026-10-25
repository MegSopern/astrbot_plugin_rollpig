"""持久化：通用 JSON 文件读写 + 当日记录存取。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping

from .models import DailyBoard


def _default_board() -> dict[str, Any]:
    """新建一份空白记录结构（每次返回新对象，避免共享可变默认值）。"""
    return {"date": "", "records": {}}


class JsonStore:
    """单个 JSON 文件的读写。

    读取失败（文件缺失 / 解析异常）时用默认值重建文件并返回默认值，
    保证业务层永远拿到可用数据。
    """

    def __init__(self, path: Path, logger: logging.Logger) -> None:
        self._path = path
        self._logger = logger

    def load(self, default: Any) -> Any:
        """读取 JSON；文件缺失或损坏时写入默认值并返回默认值。"""
        if not self._path.exists():
            self.save(default)
            return default
        try:
            return json.loads(self._path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            self._logger.error("JSON文件解析失败，重置为默认值：%s（%s）", self._path, exc)
            self.save(default)
            return default

    def save(self, data: Any) -> None:
        """写入 JSON（自动创建父目录）。"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )


class DailyBoardStore:
    """当日抽取记录的存取，负责日期校验与结构转换。"""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def load(self, day: str) -> DailyBoard:
        """读取指定日期的记录板；日期不匹配视为新的一天。"""
        raw = self._store.load(_default_board())
        if not isinstance(raw, Mapping) or raw.get("date") != day:
            return DailyBoard.empty(day)
        return DailyBoard.from_mapping(raw, day)

    def save(self, board: DailyBoard) -> None:
        """保存记录板。"""
        self._store.save(board.to_mapping())
