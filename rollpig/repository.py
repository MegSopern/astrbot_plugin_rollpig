"""小猪档案仓库：加载资源目录中的档案与图片。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping

from .models import Pig

IMAGE_EXTENSIONS: tuple[str, ...] = ("png", "jpg", "jpeg", "webp", "gif")


class PigRepository:
    """只读资源仓库：``pig.json`` 档案 + ``image/`` 图片。

    资源文件属于插件包内容，加载失败时仅记录日志、不写回插件目录。
    """

    def __init__(
        self,
        catalog_path: Path,
        image_dir: Path,
        logger: logging.Logger,
    ) -> None:
        self._catalog_path = catalog_path
        self._image_dir = image_dir
        self._logger = logger
        self._pigs = self._load_catalog()

    @property
    def pigs(self) -> tuple[Pig, ...]:
        """全部小猪档案。"""
        return self._pigs

    def __len__(self) -> int:
        return len(self._pigs)

    def __bool__(self) -> bool:
        return bool(self._pigs)

    def _load_catalog(self) -> tuple[Pig, ...]:
        """读取档案文件，失败时返回空元组。"""
        try:
            raw: Any = json.loads(self._catalog_path.read_text("utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            self._logger.error("小猪信息为空或不存在，请检查资源文件！（%s）", exc)
            return ()
        except json.JSONDecodeError as exc:
            self._logger.error("小猪信息解析失败：%s（%s）", self._catalog_path, exc)
            return ()

        if not isinstance(raw, list):
            self._logger.error("小猪信息格式错误，应为列表：%s", self._catalog_path)
            return ()

        pigs = tuple(
            Pig.from_mapping(item) for item in raw if isinstance(item, Mapping)
        )
        if not pigs:
            self._logger.error("小猪信息为空或不存在，请检查资源文件！")
        return pigs

    def find_image(self, pig_id: str) -> Path | None:
        """按 ID 在图片目录中查找图片，支持多种扩展名。"""
        for extension in IMAGE_EXTENSIONS:
            candidate = self._image_dir / f"{pig_id}.{extension}"
            if candidate.exists():
                self._logger.debug("找到的小猪图片文件：%s", candidate.absolute())
                return candidate
        self._logger.warning("未找到小猪ID %s 对应的图片文件", pig_id)
        return None
