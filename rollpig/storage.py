"""持久化：当日抽取记录的单文件 JSON 存取。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping

from .models import DailyBoard


def _empty_board() -> dict[str, Any]:
    """新建一份空白记录结构（每次返回新对象，避免共享可变默认值）。"""
    return {"date": "", "records": {}}


class BoardStore:
    """当日抽取记录的持久化。

    文件缺失或损坏时用默认结构重建，保证业务层永远拿到可用数据；
    日期不匹配视为新的一天。
    """

    def __init__(self, path: Path, logger: logging.Logger) -> None:
        self._path = path
        self._logger = logger

    def load(self, day: str) -> DailyBoard:
        """读取指定日期的记录板。"""
        raw = self._read()
        if not isinstance(raw, Mapping) or raw.get("date") != day:
            return DailyBoard.empty(day)
        return DailyBoard.from_mapping(raw, day)

    def save(self, board: DailyBoard) -> None:
        """保存记录板。"""
        self._write(board.to_mapping())

    def _read(self) -> Any:
        """读取原始 JSON；缺失或损坏时写入默认结构并返回它。"""
        if not self._path.exists():
            default = _empty_board()
            self._write(default)
            return default
        try:
            return json.loads(self._path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            self._logger.error("JSON文件解析失败，重置为默认值：%s（%s）", self._path, exc)
            default = _empty_board()
            self._write(default)
            return default

    def _write(self, data: Any) -> None:
        """写入 JSON（自动创建父目录）。"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
