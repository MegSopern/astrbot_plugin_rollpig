"""领域模型：小猪档案、当日抽取记录与抽取结果。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from . import messages


@dataclass(frozen=True, slots=True)
class Pig:
    """一只小猪的档案（值对象，与资源文件中的一条记录一一对应）。"""

    id: str
    name: str
    description: str
    analysis: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> Pig:
        """由 JSON 记录构造；缺字段时回退到统一占位文案。"""
        return cls(
            id=str(raw.get("id", "")),
            name=str(raw.get("name", messages.UNKNOWN_NAME)),
            description=str(raw.get("description", messages.UNKNOWN_DESCRIPTION)),
            analysis=str(raw.get("analysis", messages.UNKNOWN_ANALYSIS)),
        )

    def to_mapping(self) -> dict[str, str]:
        """序列化为与资源文件一致的 JSON 记录。"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "analysis": self.analysis,
        }


@dataclass(slots=True)
class DailyBoard:
    """某一天的抽取记录（用户 ID → 小猪）。"""

    day: str
    records: dict[str, Pig] = field(default_factory=dict)

    @classmethod
    def empty(cls, day: str) -> DailyBoard:
        """构造某一天的空记录板。"""
        return cls(day=day)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any], day: str) -> DailyBoard:
        """由持久化结构恢复记录板，跳过结构异常的条目。"""
        records: dict[str, Pig] = {}
        stored = raw.get("records")
        if isinstance(stored, Mapping):
            for user_id, record in stored.items():
                if isinstance(record, Mapping):
                    records[str(user_id)] = Pig.from_mapping(record)
        return cls(day=day, records=records)

    def to_mapping(self) -> dict[str, Any]:
        """序列化为持久化结构。"""
        return {
            "date": self.day,
            "records": {user_id: pig.to_mapping() for user_id, pig in self.records.items()},
        }

    def get(self, user_id: str) -> Pig | None:
        """读取用户当天已抽到的小猪。"""
        return self.records.get(user_id)

    def put(self, user_id: str, pig: Pig) -> None:
        """记录用户当天抽到的小猪。"""
        self.records[user_id] = pig
