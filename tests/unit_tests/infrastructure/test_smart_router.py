"""
SmartModelRouter 单元测试。

关注点：
- `router_config.yaml` 能被正确解析并生效（policy/eager_load/cloud 开关等）
- 显式参数优先级高于配置（例如 eager_load 显式传入应覆盖配置）
"""

from __future__ import annotations

import pytest


def test_router_config_is_loaded_and_applied(tmp_path) -> None:
    pytest.importorskip("yaml")

    from infrastructure.model_hub.smart_model_router import SmartModelRouter, TaskType

    cfg = tmp_path / "router_config.yaml"
    cfg.write_text(
        "\n".join(
            [
                "meta:",
                "  schema_version: \"2.0.0\"",
                "router:",
                "  enabled: true",
                "  eager_load: true",
                "  allow_cloud_models: true",
                "  policy_version: \"test-policy\"",
                "  policy:",
                "    vram_overcommit_ratio: 1.30",
                "    weights:",
                "      capability: 0.10",
                "      hardware_fit: 0.20",
                "      latency: 0.30",
                "      context_fit: 0.20",
                "      reliability: 0.20",
                "    latency_budget_ms:",
                "      coding: 123",
                "  constraints:",
                "    allow_empty_candidates_fallback: false",
                "  fallback:",
                "    strategy: \"static\"",
                "    static_model_key: \"some_model_id\"",
                "",
            ]
        ),
        encoding="utf-8",
    )

    router = SmartModelRouter(router_config_path=cfg)
    assert router.policy_version == "test-policy"
    assert router.eager_load is True
    assert router.allow_cloud_models is True
    assert router.allow_empty_candidates_fallback is False
    assert router.fallback_strategy == "static"
    assert router.static_model_key == "some_model_id"

    assert router.policy.vram_overcommit_ratio == pytest.approx(1.30)
    assert router.policy.weights["capability"] == pytest.approx(0.10)
    assert router.policy.latency_budget_ms[TaskType.CODING] == 123


def test_explicit_eager_load_overrides_config(tmp_path) -> None:
    pytest.importorskip("yaml")

    from infrastructure.model_hub.smart_model_router import SmartModelRouter

    cfg = tmp_path / "router_config.yaml"
    cfg.write_text(
        "\n".join(
            [
                "router:",
                "  eager_load: true",
                "",
            ]
        ),
        encoding="utf-8",
    )

    router = SmartModelRouter(router_config_path=cfg, eager_load=False)
    assert router.eager_load is False
