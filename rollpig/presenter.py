"""消息链组装：把领域对象转换成 AstrBot 消息组件。"""

from __future__ import annotations

import logging
from pathlib import Path

import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent

from . import messages
from .config import PluginSettings
from .models import Pig


class PigPresenter:
    """负责「说什么」：卡片前置文案与降级文案。"""

    def __init__(self, settings: PluginSettings, logger: logging.Logger) -> None:
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
