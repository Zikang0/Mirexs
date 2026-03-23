"""
符号链接/目录联接管理器（Symlink Manager）

为什么需要：
- `data/`、`data/models/` 等路径在代码与配置中是“稳定契约”；
  但真实存储位置可能需要迁移到更快/更大/更便宜的介质。
- 通过 symlink/junction 实现“路径不变，位置可变”，对上层透明。

实现策略：
- Linux/macOS：优先使用 symlink
- Windows：优先使用目录 Junction（`mklink /J`），因为普通 symlink 可能需要管理员权限或开发者模式
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional


class LinkType(str, Enum):
    AUTO = "auto"
    SYMLINK = "symlink"
    JUNCTION = "junction"  # Windows 目录联接
    HARDLINK = "hardlink"  # 文件硬链接（同盘）


class SymlinkManager:
    """创建/验证/移除链接。"""

    def __init__(self, *, prefer_junction_on_windows: bool = True):
        self.prefer_junction_on_windows = bool(prefer_junction_on_windows)
        self._is_windows = platform.system().lower() == "windows"

    def ensure_link(
        self,
        link_path: os.PathLike,
        target_path: os.PathLike,
        *,
        link_type: LinkType = LinkType.AUTO,
        overwrite: bool = True,
    ) -> None:
        """
        确保 link_path 指向 target_path。

        - 若已正确指向，则不做任何事
        - 若存在但不正确，且 overwrite=True，则删除后重建
        """
        link = Path(link_path)
        target = Path(target_path)

        if not target.exists():
            raise FileNotFoundError(f"target_path 不存在: {target}")

        if link.exists() or link.is_symlink():
            if self._points_to(link, target):
                return
            if not overwrite:
                raise FileExistsError(f"link_path 已存在且指向其他位置: {link}")
            self._remove_path(link)

        link.parent.mkdir(parents=True, exist_ok=True)

        resolved_type = self._resolve_link_type(link_type, link, target)
        if resolved_type == LinkType.SYMLINK:
            self._create_symlink(link, target)
        elif resolved_type == LinkType.JUNCTION:
            self._create_junction(link, target)
        elif resolved_type == LinkType.HARDLINK:
            self._create_hardlink(link, target)
        else:
            raise ValueError(f"不支持的 link_type: {resolved_type}")

    def _resolve_link_type(self, link_type: LinkType, link: Path, target: Path) -> LinkType:
        if link_type != LinkType.AUTO:
            return link_type
        if self._is_windows and self.prefer_junction_on_windows and target.is_dir():
            return LinkType.JUNCTION
        return LinkType.SYMLINK

    def _create_symlink(self, link: Path, target: Path) -> None:
        try:
            os.symlink(str(target), str(link), target_is_directory=target.is_dir())
        except Exception as e:
            # Windows 下 symlink 可能无权限：目录回退到 junction
            if self._is_windows and target.is_dir():
                self._create_junction(link, target)
                return
            raise RuntimeError(f"创建 symlink 失败: {link} -> {target}: {e}") from e

    def _create_junction(self, link: Path, target: Path) -> None:
        if not self._is_windows:
            raise RuntimeError("Junction 仅支持 Windows")
        if not target.is_dir():
            raise RuntimeError("Junction 仅支持目录")
        # mklink 是 cmd 内建命令，需通过 cmd /c 调用
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"创建 junction 失败: {result.stdout.strip()} {result.stderr.strip()}".strip())

    def _create_hardlink(self, link: Path, target: Path) -> None:
        if target.is_dir():
            raise RuntimeError("hardlink 仅支持文件")
        try:
            os.link(str(target), str(link))
        except Exception as e:
            raise RuntimeError(f"创建 hardlink 失败: {link} -> {target}: {e}") from e

    def _points_to(self, link: Path, target: Path) -> bool:
        try:
            if link.is_symlink():
                return link.resolve() == target.resolve()
        except Exception:
            pass

        # Windows junction 检测：通过 resolve 可能失败，退化为比较绝对路径前缀
        try:
            return link.resolve() == target.resolve()
        except Exception:
            return str(link).lower() == str(target).lower()

    def _remove_path(self, path: Path) -> None:
        try:
            if path.is_symlink():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except FileNotFoundError:
            return
