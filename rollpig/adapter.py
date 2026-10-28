"""AstrBot 适配层：入站事件 → 抽签对象，领域对象 → 消息链。

包内只有本模块依赖 AstrBot 的事件与消息组件，其余模块保持框架无关，
便于独立测试，也便于将来替换/扩展平台适配。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from . import messages
from .config import PluginSettings
from .models import Pig


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
    """入站：按配置解析抽签对象（自己 / 被 @ 的人）。"""

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


class PigPresenter:
    """出站：把领域对象转换成 AstrBot 消息链。"""

    def __init__(self, settings: PluginSettings, logger) -> None:
        self._settings = settings
        self._logger = logger

    def should_mention(self, event: AstrMessageEvent) -> bool:
        """群聊且开启 ``at_reply_user`` 时才 @ 用户。"""
        return bool(event.get_group_id()) and self._settings.at_reply_user

    def card_chain(
        self, user_id: str, *, mention: bool
    ) -> list[Comp.BaseMessageComponent]:
        """卡片前置消息链：可选 @ 用户 + 引导文案。"""
        chain: list[Comp.BaseMessageComponent] = []
        if mention:
            chain.append(Comp.At(qq=user_id))
        separator = messages.AT_SEPARATOR if mention else ""
        chain.append(Comp.Plain(f"{separator}{messages.CARD_PREFIX}"))
        return chain

    def fallback_chain(
        self, pig: Pig, image_path: Path | None
    ) -> list[Comp.BaseMessageComponent]:
        """降级消息链：原始图片 + 纯文本。"""
        text = messages.FALLBACK_TEMPLATE.format(
            name=pig.name,
            description=pig.description,
            analysis=pig.analysis,
        )
        chain: list[Comp.BaseMessageComponent] = []
        if image_path is not None and image_path.exists():
            try:
                chain.append(Comp.Image.fromFileSystem(str(image_path.absolute())))
            except Exception as exc:  # 图片文件不可读
                self._logger.error("发送原始图片失败：%s", exc)
                text += messages.IMAGE_SEND_FAILED_HINT
        chain.append(Comp.Plain(text))
        return chain
