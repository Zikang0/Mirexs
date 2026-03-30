"""
存储编排器（Storage Orchestrator）。

负责把数据迁移过程串起来：
- 目标存储评估
- 迁移计划生成与执行
- 完整性校验
- 可选路径联接与云端镜像
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .cloud_sync_adapter import CloudSyncAdapter, NullCloudSyncAdapter
from .data_migrator import DataMigrator, MigrationPlan
from .migration_validator import MigrationValidator, ValidationReport
from .symlink_manager import LinkType, SymlinkManager


@dataclass
class StorageTarget:
    """迁移目标描述。"""

    name: str
    root_path: Path
    kind: str = "local"
    priority: int = 100
    remote_path: Optional[str] = None
    supports_links: bool = True

    def resolve_destination(self, source_root: Path) -> Path:
        return self.root_path / source_root.name


@dataclass
class OrchestratorConfig:
    """编排配置。"""

    mode: str = "copy"
    dry_run: bool = False
    overwrite: bool = False
    create_link_after_move: bool = False
    link_type: LinkType = LinkType.AUTO
    check_size: bool = True
    check_hash: bool = False
    hash_sample_rate: float = 0.1
    max_hash_file_mb: int = 2048
    free_space_buffer_ratio: float = 0.1
    upload_to_cloud: bool = False


class StorageOrchestrator:
    """存储迁移编排器。"""

    def __init__(
        self,
        *,
        migrator: Optional[DataMigrator] = None,
        validator: Optional[MigrationValidator] = None,
        symlink_manager: Optional[SymlinkManager] = None,
        cloud_adapter: Optional[CloudSyncAdapter] = None,
    ):
        self.migrator = migrator or DataMigrator()
        self.validator = validator or MigrationValidator()
        self.symlink_manager = symlink_manager or SymlinkManager()
        self.cloud_adapter = cloud_adapter or NullCloudSyncAdapter()

    def choose_best_target(self, source_root: Path, targets: Iterable[StorageTarget]) -> StorageTarget:
        """按优先级与剩余空间选择最优目标。"""
        source_root = Path(source_root).resolve()
        source_size = self._estimate_directory_size(source_root)
        candidates: List[tuple[int, int, StorageTarget]] = []

        for target in targets:
            free_bytes = self.get_free_space(target.root_path)
            score = target.priority
            if free_bytes >= source_size:
                score -= 1000
            candidates.append((score, -free_bytes, target))

        if not candidates:
            raise ValueError("没有可用的存储目标")

        candidates.sort(key=lambda item: (item[0], item[1], item[2].name))
        return candidates[0][2]

    def build_plan(
        self,
        source_root: Path,
        target: StorageTarget,
        *,
        include: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> MigrationPlan:
        """生成迁移计划。"""
        source_root = Path(source_root).resolve()
        destination_root = target.resolve_destination(source_root).resolve()
        return self.migrator.build_plan(
            source_root=source_root,
            destination_root=destination_root,
            include=include,
            exclude=exclude,
        )

    def execute_migration(
        self,
        source_root: Path,
        target: StorageTarget,
        *,
        include: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
        config: Optional[OrchestratorConfig] = None,
    ) -> Dict[str, object]:
        """执行迁移并返回可审计结果。"""
        config = config or OrchestratorConfig()
        source_root = Path(source_root).resolve()
        target.root_path.mkdir(parents=True, exist_ok=True)

        plan = self.build_plan(
            source_root=source_root,
            target=target,
            include=include,
            exclude=exclude,
        )
        self._ensure_target_capacity(plan, target, config)

        self.migrator.execute_plan(
            plan,
            mode=config.mode,
            overwrite=config.overwrite,
            dry_run=config.dry_run,
        )

        validation_report = ValidationReport(ok=True, checked_files=0, sampled_hash_files=0, issues=[])
        if not config.dry_run:
            validation_report = self.validator.validate(
                plan,
                check_size=config.check_size,
                check_hash=config.check_hash,
                hash_sample_rate=config.hash_sample_rate,
                max_hash_file_mb=config.max_hash_file_mb,
            )

            if config.create_link_after_move and config.mode == "move":
                self.symlink_manager.ensure_link(
                    link_path=source_root,
                    target_path=plan.destination_root,
                    link_type=config.link_type,
                    overwrite=True,
                )

            if config.upload_to_cloud and target.remote_path:
                if not self.cloud_adapter.is_available():
                    raise RuntimeError("cloud_adapter 不可用，无法执行云端同步")
                self.cloud_adapter.upload_directory(
                    source_dir=plan.destination_root,
                    remote_path=target.remote_path,
                    overwrite=config.overwrite,
                )

        return {
            "source_root": str(plan.source_root),
            "destination_root": str(plan.destination_root),
            "target": target.name,
            "mode": config.mode,
            "dry_run": config.dry_run,
            "total_files": len(plan.items),
            "total_bytes": plan.total_bytes,
            "validation": validation_report,
        }

    def get_free_space(self, path: Path) -> int:
        """获取路径所在磁盘的剩余空间。"""
        disk_usage = shutil.disk_usage(Path(path).resolve())
        return int(disk_usage.free)

    def _ensure_target_capacity(
        self,
        plan: MigrationPlan,
        target: StorageTarget,
        config: OrchestratorConfig,
    ) -> None:
        free_bytes = self.get_free_space(target.root_path)
        required_bytes = int(plan.total_bytes * (1.0 + max(0.0, config.free_space_buffer_ratio)))
        if free_bytes < required_bytes:
            raise RuntimeError(
                f"目标空间不足: target={target.name}, free={free_bytes}, required={required_bytes}"
            )

    def _estimate_directory_size(self, source_root: Path) -> int:
        total_size = 0
        for file_path in source_root.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
