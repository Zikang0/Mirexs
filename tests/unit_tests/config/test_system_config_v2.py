"""
v2 配置加载与约定测试。

目标：
- 确保 `config/system/main_config.yaml` 满足 v2 最小校验
- 确保 `config.system.ConfigManager.get_config()` 能按约定加载 component_configs
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config.system import ConfigError, ConfigManager


def test_system_main_config_is_v2() -> None:
    manager = ConfigManager()
    config = manager.get_system_config()

    assert isinstance(config, dict)
    assert config.get("meta", {}).get("schema_version", "").startswith("2.")
    assert config.get("system", {}).get("version", "").startswith("2.")
    assert "paths" in config and isinstance(config["paths"], dict)
    assert "component_configs_dir" in config["paths"]


def test_component_config_resolution() -> None:
    manager = ConfigManager()

    text_input = manager.get_config("text_input_config")
    assert isinstance(text_input, dict)
    assert text_input.get("default_language") in {"zh-CN", "en-US"}

    shortcuts = manager.get_config("shortcuts")
    assert isinstance(shortcuts, dict)
    assert "system_shortcuts" in shortcuts


def test_missing_config_returns_default() -> None:
    manager = ConfigManager()

    assert manager.get_config("this_config_should_not_exist") == {}
    assert manager.get_config("this_config_should_not_exist", default={"ok": True}) == {"ok": True}


def test_main_config_schema_validation_rejects_v1(tmp_path: Path) -> None:
    # 构造一个最小可解析但 schema_version=1.x 的主配置
    config_root = tmp_path / "config"
    system_dir = config_root / "system"
    system_dir.mkdir(parents=True, exist_ok=True)

    (system_dir / "main_config.yaml").write_text(
        "\n".join(
            [
                "meta:",
                "  schema_version: \"1.0.0\"",
                "system:",
                "  version: \"1.0.0\"",
                "mode: {}",
                "logging: {}",
                "paths: {}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    manager = ConfigManager(str(config_root))
    with pytest.raises(ConfigError):
        manager.get_system_config(reload=True)

