"""
存储迁移模块（Storage Migration）

目标：
- 在不破坏项目路径契约的前提下，将 `data/`（尤其是大体积模型/缓存）迁移到更合适的存储介质：
  SSD / 外接盘 / 云盘目录等。
- 通过符号链接/目录联接（Windows Junction）实现“路径不变、位置可变”。

该模块属于基础设施层的工具链：
- 不依赖上层业务逻辑，可独立调用；
- 设计为“可降级”：即使 symlink 不可用也能完成拷贝/校验。
"""

from .data_migrator import DataMigrator, MigrationPlan, MigrationItem
from .migration_validator import MigrationValidator, ValidationReport
from .storage_orchestrator import StorageOrchestrator, StorageTarget, OrchestratorConfig
from .symlink_manager import SymlinkManager, LinkType
from .cloud_sync_adapter import CloudSyncAdapter, LocalFolderSyncAdapter, NullCloudSyncAdapter
from .migration_wizard import MigrationWizard

__all__ = [
    "MigrationItem",
    "MigrationPlan",
    "DataMigrator",
    "ValidationReport",
    "MigrationValidator",
    "StorageTarget",
    "OrchestratorConfig",
    "StorageOrchestrator",
    "LinkType",
    "SymlinkManager",
    "CloudSyncAdapter",
    "NullCloudSyncAdapter",
    "LocalFolderSyncAdapter",
    "MigrationWizard",
]
