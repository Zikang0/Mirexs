"""
迁移向导（Migration Wizard）。

不是 GUI，而是面向代码调用的“分步决策器”：
- 评估源目录与候选目标
- 给出推荐目标
- 生成可执行计划
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from .storage_orchestrator import OrchestratorConfig, StorageOrchestrator, StorageTarget


@dataclass
class MigrationRecommendation:
    """单个候选目标的建议结果。"""

    target: StorageTarget
    estimated_total_bytes: int
    free_bytes: int
    feasible: bool
    reasons: List[str] = field(default_factory=list)


@dataclass
class MigrationWizardResult:
    """向导输出。"""

    source_root: Path
    recommended_target: Optional[StorageTarget]
    recommendations: List[MigrationRecommendation]


class MigrationWizard:
    """迁移向导。"""

    def __init__(self, orchestrator: Optional[StorageOrchestrator] = None):
        self.orchestrator = orchestrator or StorageOrchestrator()

    def assess_targets(
        self,
        source_root: Path,
        targets: Iterable[StorageTarget],
    ) -> MigrationWizardResult:
        """评估候选目标并给出推荐。"""
        source_root = Path(source_root).resolve()
        estimated_bytes = self.orchestrator._estimate_directory_size(source_root)
        recommendations: List[MigrationRecommendation] = []

        for target in targets:
            free_bytes = self.orchestrator.get_free_space(target.root_path)
            feasible = free_bytes >= estimated_bytes
            reasons: List[str] = []

            if feasible:
                reasons.append("可容纳当前数据规模")
            else:
                reasons.append("剩余空间不足")

            if target.supports_links:
                reasons.append("支持路径联接/符号链接")
            else:
                reasons.append("不支持联接，需要保留复制模式")

            if target.remote_path:
                reasons.append("具备云端镜像目标")

            recommendations.append(
                MigrationRecommendation(
                    target=target,
                    estimated_total_bytes=estimated_bytes,
                    free_bytes=free_bytes,
                    feasible=feasible,
                    reasons=reasons,
                )
            )

        feasible_targets = [item.target for item in recommendations if item.feasible]
        recommended_target = None
        if feasible_targets:
            recommended_target = self.orchestrator.choose_best_target(source_root, feasible_targets)

        return MigrationWizardResult(
            source_root=source_root,
            recommended_target=recommended_target,
            recommendations=sorted(
                recommendations,
                key=lambda item: (
                    0 if item.feasible else 1,
                    item.target.priority,
                    -item.free_bytes,
                    item.target.name,
                ),
            ),
        )

    def create_execution_plan(
        self,
        source_root: Path,
        targets: Iterable[StorageTarget],
        *,
        preferred_target: Optional[str] = None,
        config: Optional[OrchestratorConfig] = None,
    ) -> dict:
        """根据评估结果生成执行计划摘要。"""
        config = config or OrchestratorConfig()
        result = self.assess_targets(source_root, targets)

        target = result.recommended_target
        if preferred_target is not None:
            target = next(
                (item.target for item in result.recommendations if item.target.name == preferred_target),
                None,
            )

        if target is None:
            raise RuntimeError("没有可执行的迁移目标")

        plan = self.orchestrator.build_plan(source_root=source_root, target=target)
        return {
            "source_root": str(result.source_root),
            "target": target.name,
            "destination_root": str(plan.destination_root),
            "total_files": len(plan.items),
            "total_bytes": plan.total_bytes,
            "mode": config.mode,
            "dry_run": config.dry_run,
        }
