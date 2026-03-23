"""
数据迁移引擎（Data Migrator）

提供“计划 -> 执行”的两阶段能力：
- 计划阶段：枚举源目录，生成 MigrationPlan（可审计、可预估空间）
- 执行阶段：按计划 copy/move，并提供进度回调与错误收敛

严谨性约束：
1) 默认不覆盖目标文件（overwrite=False），避免误删/误覆盖。
2) 写入采用临时文件 + 原子替换（尽量保证目标端一致性）。
3) 支持 dry_run：用于在生产环境先演练迁移计划。
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple


ProgressCallback = Callable[[int, int, Optional[str]], None]


@dataclass(frozen=True)
class MigrationItem:
    """单个迁移条目（文件级）。"""

    source: Path
    destination: Path
    size_bytes: int


@dataclass
class MigrationPlan:
    """迁移计划（可审计/可复用）。"""

    source_root: Path
    destination_root: Path
    items: List[MigrationItem] = field(default_factory=list)
    total_bytes: int = 0
    created_at: float = field(default_factory=lambda: time.time())


class DataMigrator:
    """核心迁移引擎。"""

    def __init__(self, *, max_file_size_for_hash_mb: int = 1024):
        # 超过该阈值默认不做“执行阶段哈希校验”，由 MigrationValidator 决定是否抽检
        self.max_file_size_for_hash_mb = max(1, int(max_file_size_for_hash_mb))

    def build_plan(
        self,
        source_root: os.PathLike,
        destination_root: os.PathLike,
        *,
        include: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> MigrationPlan:
        """
        生成迁移计划。

        include/exclude 为 glob 风格匹配（相对 source_root 的路径）。
        - include 为空：默认全部包含
        - exclude 命中则跳过
        """
        src_root = Path(source_root).resolve()
        dst_root = Path(destination_root).resolve()
        if not src_root.exists():
            raise FileNotFoundError(f"source_root 不存在: {src_root}")

        include_patterns = list(include or [])
        exclude_patterns = list(exclude or [])

        items: List[MigrationItem] = []
        total_bytes = 0

        for file_path in src_root.rglob("*"):
            if not file_path.is_file():
                continue

            rel = file_path.relative_to(src_root).as_posix()

            if include_patterns and not any(fnmatch.fnmatch(rel, p) for p in include_patterns):
                continue
            if exclude_patterns and any(fnmatch.fnmatch(rel, p) for p in exclude_patterns):
                continue

            dst_path = dst_root / rel
            size_bytes = file_path.stat().st_size
            items.append(MigrationItem(source=file_path, destination=dst_path, size_bytes=size_bytes))
            total_bytes += size_bytes

        plan = MigrationPlan(source_root=src_root, destination_root=dst_root, items=items, total_bytes=total_bytes)
        return plan

    def execute_plan(
        self,
        plan: MigrationPlan,
        *,
        mode: str = "copy",
        overwrite: bool = False,
        dry_run: bool = False,
        progress: Optional[ProgressCallback] = None,
    ) -> None:
        """
        执行迁移计划。

        mode:
        - copy：复制文件（源保留）
        - move：移动文件（源删除/迁移后可清理空目录）
        """
        if mode not in {"copy", "move"}:
            raise ValueError("mode 必须为 copy 或 move")

        done_bytes = 0
        total_bytes = int(plan.total_bytes or 0)

        for item in plan.items:
            if progress:
                progress(done_bytes, total_bytes, str(item.source))

            if dry_run:
                done_bytes += int(item.size_bytes or 0)
                continue

            item.destination.parent.mkdir(parents=True, exist_ok=True)

            if item.destination.exists() and not overwrite:
                raise FileExistsError(f"目标已存在且 overwrite=False: {item.destination}")

            if mode == "copy":
                self._copy_file_atomic(item.source, item.destination)
            else:
                # move：优先使用原子替换；跨盘可能退化为 copy+delete
                self._move_file_atomic(item.source, item.destination)

            done_bytes += int(item.size_bytes or 0)

        if progress:
            progress(done_bytes, total_bytes, None)

        if not dry_run and mode == "move":
            self._cleanup_empty_dirs(plan.source_root)

    def _copy_file_atomic(self, src: Path, dst: Path) -> None:
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, dir=str(dst.parent), suffix=".part") as tmp:
            tmp_path = Path(tmp.name)
        try:
            shutil.copy2(src, tmp_path)
            tmp_path.replace(dst)
        except Exception:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
            raise

    def _move_file_atomic(self, src: Path, dst: Path) -> None:
        try:
            src.replace(dst)  # 同盘原子移动
            return
        except Exception:
            # 跨盘/权限等：退化为 copy+unlink
            self._copy_file_atomic(src, dst)
            src.unlink()

    def _cleanup_empty_dirs(self, root: Path) -> None:
        # 自底向上删除空目录
        for dir_path in sorted([p for p in root.rglob("*") if p.is_dir()], key=lambda p: len(p.parts), reverse=True):
            try:
                if not any(dir_path.iterdir()):
                    dir_path.rmdir()
            except Exception:
                pass
