"""
云盘同步适配器（Cloud Sync Adapter）

说明：
本项目在架构上支持“可选云端增强”，但默认本地优先。
对“存储迁移”而言，云盘更像是一个可选的备份/分发目的地，而非强依赖。

为避免在仓库中绑定具体云厂商 SDK，本模块提供：
- CloudSyncAdapter：抽象接口（可扩展 OneDrive/阿里云盘等）
- NullCloudSyncAdapter：默认空实现（禁用云端）
- LocalFolderSyncAdapter：使用本地文件夹模拟云盘（便于测试与离线环境）
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class CloudSyncAdapter:
    """云同步适配器接口。"""

    name: str = "cloud"

    def upload_directory(self, source_dir: Path, remote_path: str, *, overwrite: bool = False) -> None:
        """上传目录到云端路径。"""
        raise NotImplementedError

    def download_directory(self, remote_path: str, destination_dir: Path, *, overwrite: bool = False) -> None:
        """从云端路径下载目录到本地。"""
        raise NotImplementedError

    def is_available(self) -> bool:
        """当前适配器是否可用（认证/网络/路径等）。"""
        return True


class NullCloudSyncAdapter(CloudSyncAdapter):
    """禁用云端：所有操作直接抛出异常，便于调用方做明确降级。"""

    name = "disabled"

    def is_available(self) -> bool:
        return False

    def upload_directory(self, source_dir: Path, remote_path: str, *, overwrite: bool = False) -> None:
        raise RuntimeError("云同步未启用（NullCloudSyncAdapter）")

    def download_directory(self, remote_path: str, destination_dir: Path, *, overwrite: bool = False) -> None:
        raise RuntimeError("云同步未启用（NullCloudSyncAdapter）")


@dataclass
class LocalFolderSyncAdapter(CloudSyncAdapter):
    """
    使用本地文件夹模拟“云端根目录”。

    适用场景：
    - 离线环境/单机验证迁移与同步流程
    - CI 环境中不引入真实云 SDK
    """

    root_dir: Path
    name: str = "local_folder"

    def is_available(self) -> bool:
        try:
            self.root_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    def upload_directory(self, source_dir: Path, remote_path: str, *, overwrite: bool = False) -> None:
        if not source_dir.exists():
            raise FileNotFoundError(f"source_dir 不存在: {source_dir}")
        dest = self.root_dir / remote_path
        if dest.exists():
            if not overwrite:
                raise FileExistsError(f"远端路径已存在且 overwrite=False: {dest}")
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, dest)

    def download_directory(self, remote_path: str, destination_dir: Path, *, overwrite: bool = False) -> None:
        src = self.root_dir / remote_path
        if not src.exists():
            raise FileNotFoundError(f"远端路径不存在: {src}")
        if destination_dir.exists():
            if not overwrite:
                raise FileExistsError(f"destination_dir 已存在且 overwrite=False: {destination_dir}")
            shutil.rmtree(destination_dir)
        destination_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, destination_dir)
