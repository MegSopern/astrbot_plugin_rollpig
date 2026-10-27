from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, StarTools
from astrbot.core import AstrBotConfig

from .rollpig.adapter import AtTargetResolver, PigPresenter
from .rollpig.config import PluginSettings
from .rollpig.messages import CATALOG_UNAVAILABLE
from .rollpig.models import Pig
from .rollpig.renderer import CanvasSpec, PigCardRenderer
from .rollpig.repository import PigRepository
from .rollpig.service import RollPigService
from .rollpig.storage import BoardStore
from .rollpig.text import FontLibrary, TextMetrics

PLUGIN_NAME = "astrbot_plugin_rollpig"
DATA_FILE_NAME = "rollpig_today.json"

# 触发词是唯一事实来源：既作为指令名/别名，也作为「免唤醒词」模式的首尾匹配词
COMMAND_NAME = "今日小猪"
TRIGGER_WORDS = (
    "今日小猪",
    "抽小猪",
    "我的小猪",
    "rollpig",
    "pig",
    "猪咪",
    "猪",
    "🐖",
    "🐷",
    "㊗️",
)
COMMAND_ALIASES = {word for word in TRIGGER_WORDS if word != COMMAND_NAME}
# 免唤醒匹配规则：消息以触发词开头或结尾即可命中（不区分大小写）
WAKE_FREE_PATTERN = "(?i)(?:^(?:{0})|(?:{0})$)".format(
    "|".join(map(re.escape, TRIGGER_WORDS))
)


class RollPigPlugin(Star):
    """每日抽取专属小猪，并渲染成卡片发送。"""

    def __init__(self, context: Context, config: AstrBotConfig | None = None):
        super().__init__(context)
        # AstrBot < 4.27.0 的 Star 基类只注入 context，不提供 self.logger，
        # 直接用 self.logger 会在 __init__ 抛 AttributeError 导致插件加载失败。
        self.logger = getattr(self, "logger", None) or logging.getLogger(
            f"astrbot.plugin.{PLUGIN_NAME}"
        )
        self.config = config or {}
        self.settings = PluginSettings.from_mapping(
            self.config,
            context.get_config().get("admins_id", []),
        )

        resource_dir = Path(__file__).parent / "resource"
        font_dir = resource_dir / "font"
        data_dir = StarTools.get_data_dir(PLUGIN_NAME)
        data_dir.mkdir(parents=True, exist_ok=True)
        font_dir.mkdir(parents=True, exist_ok=True)  # 兼容旧版：允许用户自行补充字体

        self.repository = PigRepository(
            catalog_path=resource_dir / "pig.json",
            image_dir=resource_dir / "image",
            logger=self.logger,
        )
        self.fonts = FontLibrary(font_dir, self.logger)
        self.renderer = PigCardRenderer(
            repository=self.repository,
            fonts=self.fonts,
            metrics=TextMetrics(),
            spec=CanvasSpec(),
            logger=self.logger,
        )
        self.service = RollPigService(
            BoardStore(data_dir / DATA_FILE_NAME, self.logger),
            self.repository,
        )
        self.presenter = PigPresenter(self.settings, self.logger)
        self.targeting = AtTargetResolver(self.settings)

    @filter.command(COMMAND_NAME, alias=COMMAND_ALIASES)
    async def roll_pig(self, event: AstrMessageEvent):
        """抽取今日小猪"""
        await self._draw_and_send(event)

    @filter.regex(WAKE_FREE_PATTERN)
    async def roll_pig_wake_free(self, event: AstrMessageEvent):
        """免唤醒词触发（需开启配置项 wake_free_trigger）"""
        if not self.settings.wake_free_trigger:
            return
        text = event.get_message_str().strip()
        if (
            (event.is_at_or_wake_command or event.is_private_chat())
            and text in TRIGGER_WORDS
        ):
            # 该消息已由原有指令路径命中，交回 roll_pig，避免重复回复
            return
        await self._draw_and_send(event)

    async def _draw_and_send(self, event: AstrMessageEvent) -> None:
        decision = self.targeting.resolve(event)
        if decision.rejected:
            await event.send(event.plain_result(decision.message))
            return

        pig = self.service.draw(decision.user_id)
        if pig is None:
            await event.send(event.plain_result(CATALOG_UNAVAILABLE))
            return

        await self._send_card(event, pig, decision.user_id)

    async def _send_card(self, event: AstrMessageEvent, pig: Pig, user_id: str) -> None:
        """渲染并发送卡片；渲染或发送失败时降级为原始图片 + 文本。"""
        # 图片合成是 CPU 密集操作，放到线程池避免阻塞事件循环
        image_path = await asyncio.to_thread(self.renderer.render, pig)
        if image_path is not None and image_path.exists():
            try:
                mention = self.presenter.should_mention(event)
                await event.send(
                    event.chain_result(
                        self.presenter.card_chain(user_id, mention=mention)
                    )
                )
                await event.send(event.image_result(str(image_path.absolute())))
                return
            except Exception as exc:
                self.logger.error("发送合成图片失败：%s", exc)
            finally:
                self._remove_temp_file(image_path)

        await event.send(
            event.chain_result(
                self.presenter.fallback_chain(pig, self.repository.find_image(pig.id))
            )
        )

    def _remove_temp_file(self, path: Path) -> None:
        """清理渲染产生的临时文件。"""
        try:
            path.unlink(missing_ok=True)
        except Exception as exc:
            self.logger.warning("清理临时图片失败：%s", exc)

    async def terminate(self):
        """插件卸载清理"""
        self.logger.info("今日小猪插件已卸载")
