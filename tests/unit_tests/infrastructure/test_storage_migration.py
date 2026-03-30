"""
存储迁移链路单元测试。
"""

import tempfile
import unittest
from pathlib import Path

from infrastructure.storage_migration import (
    MigrationWizard,
    OrchestratorConfig,
    StorageOrchestrator,
    StorageTarget,
)


class TestStorageMigration(unittest.TestCase):
    """验证编排器与向导的基本可执行性。"""

    def test_execute_copy_migration_and_validate(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir:
            source_root = Path(source_dir) / "data"
            source_root.mkdir()
            (source_root / "example.txt").write_text("mirexs", encoding="utf-8")

            orchestrator = StorageOrchestrator()
            target = StorageTarget(name="local", root_path=Path(target_dir))

            result = orchestrator.execute_migration(
                source_root=source_root,
                target=target,
                config=OrchestratorConfig(mode="copy", dry_run=False),
            )

            migrated_file = Path(result["destination_root"]) / "example.txt"
            self.assertTrue(migrated_file.exists())
            self.assertTrue(result["validation"].ok)

    def test_wizard_recommends_feasible_target(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir:
            source_root = Path(source_dir) / "dataset"
            source_root.mkdir()
            (source_root / "data.bin").write_bytes(b"123456")

            wizard = MigrationWizard()
            targets = [StorageTarget(name="fast_disk", root_path=Path(target_dir), priority=1)]

            result = wizard.assess_targets(source_root, targets)

            self.assertIsNotNone(result.recommended_target)
            self.assertEqual(result.recommended_target.name, "fast_disk")
