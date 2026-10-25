"""指令目标解析：抽自己，还是在开启 ``at_view_pig`` 后抽被 @ 的人。"""

from __future__ import annotations

from dataclasses import dataclass

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from . import messages
from .config import PluginSettings


@dataclass(frozen=True, slots=True)
class TargetDecision:
    """解析结果；``message`` 非空表示应当直接回绝，不再抽签。"""

    user_id: str
    message: str = ""

    @property
    def rejected(self) -> bool:
        """是否被回绝。"""
        return bool(self.message)


class AtTargetResolver:
    """按配置解析抽签对象。"""

    def __init__(self, settings: PluginSettings) -> None:
        self._settings = settings

    def resolve(self, event: AstrMessageEvent) -> TargetDecision:
        """解析本次指令的抽签对象。"""
        sender_id = event.get_sender_id()
        if not self._settings.at_view_pig:
            return TargetDecision(sender_id)

        mentioned = self._mentioned_ids(event)
        if len(mentioned) > 1:
            return TargetDecision(sender_id, messages.MULTI_TARGET_REJECTED)

        # 指令后面还带了内容，且确实存在被 @ 的人，才视为「查看他人」
        if len(event.message_str.strip().split()) < 2 or not mentioned:
            return TargetDecision(sender_id)

        target_id = mentioned[0]
        if self._settings.is_admin(target_id):
            return TargetDecision(sender_id, messages.ADMIN_TARGET_REJECTED)
        return TargetDecision(target_id)

    @staticmethod
    def _mentioned_ids(event: AstrMessageEvent) -> list[str]:
        """取出被 @ 的用户 ID（排除机器人自己）。"""
        return [
            str(segment.qq)
            for segment in event.get_messages()
            if isinstance(segment, Comp.At) and str(segment.qq) != event.get_self_id()
        ]
