"""
迁移校验器（Migration Validator）

用于验证迁移后的数据是否完整、一致：
- 文件是否存在
- 大小是否一致
- 可选：sha256 校验（可配置抽样比例，避免对超大文件全量 hash）
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .data_migrator import MigrationPlan


@dataclass
class ValidationIssue:
    kind: str
    source: str
    destination: str
    message: str


@dataclass
class ValidationReport:
    ok: bool
    checked_files: int
    sampled_hash_files: int
    issues: List[ValidationIssue] = field(default_factory=list)


class MigrationValidator:
    """迁移完整性校验。"""

    def __init__(self, *, random_seed: Optional[int] = None):
        self._rng = random.Random(random_seed)

    def validate(
        self,
        plan: MigrationPlan,
        *,
        check_size: bool = True,
        check_hash: bool = False,
        hash_sample_rate: float = 0.1,
        max_hash_file_mb: int = 2048,
    ) -> ValidationReport:
        """
        校验迁移结果。

        - hash_sample_rate：0~1，表示抽样比例（仅在 check_hash=True 时生效）
        - max_hash_file_mb：超过该大小的文件默认跳过 hash（避免耗时过大）
        """
        issues: List[ValidationIssue] = []
        checked = 0
        sampled_hash = 0

        sample_rate = float(hash_sample_rate)
        if sample_rate < 0.0:
            sample_rate = 0.0
        if sample_rate > 1.0:
            sample_rate = 1.0

        max_hash_bytes = int(max(1, int(max_hash_file_mb)) * 1024 * 1024)

        for item in plan.items:
            checked += 1
            src = item.source
            dst = item.destination

            if not dst.exists():
                issues.append(
                    ValidationIssue(
                        kind="missing",
                        source=str(src),
                        destination=str(dst),
                        message="目标文件不存在",
                    )
                )
                continue

            if check_size:
                try:
                    if src.stat().st_size != dst.stat().st_size:
                        issues.append(
                            ValidationIssue(
                                kind="size_mismatch",
                                source=str(src),
                                destination=str(dst),
                                message=f"文件大小不一致 src={src.stat().st_size}, dst={dst.stat().st_size}",
                            )
                        )
                        continue
                except Exception as e:
                    issues.append(
                        ValidationIssue(
                            kind="stat_error",
                            source=str(src),
                            destination=str(dst),
                            message=f"读取文件信息失败: {e}",
                        )
                    )
                    continue

            if check_hash:
                # 抽样 + 大小阈值
                try:
                    size = dst.stat().st_size
                except Exception:
                    size = 0
                if size <= 0:
                    continue
                if size > max_hash_bytes:
                    continue
                if self._rng.random() > sample_rate:
                    continue

                sampled_hash += 1
                try:
                    src_hash = self._sha256(src)
                    dst_hash = self._sha256(dst)
                    if src_hash != dst_hash:
                        issues.append(
                            ValidationIssue(
                                kind="hash_mismatch",
                                source=str(src),
                                destination=str(dst),
                                message=f"sha256 不一致 src={src_hash}, dst={dst_hash}",
                            )
                        )
                except Exception as e:
                    issues.append(
                        ValidationIssue(
                            kind="hash_error",
                            source=str(src),
                            destination=str(dst),
                            message=f"计算 sha256 失败: {e}",
                        )
                    )

        return ValidationReport(ok=(len(issues) == 0), checked_files=checked, sampled_hash_files=sampled_hash, issues=issues)

    def _sha256(self, path: Path, chunk_size: int = 1024 * 1024) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
