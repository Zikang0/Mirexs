"""
模型下载器（Model Downloader）

职责：
- 按 `ModelProfile` 中的 url/path 信息，将模型权重下载/缓存到本地目录。
- 支持 sha256 校验与断点续传（MVP：提供基础断点/原子写入策略）。

注意：
本项目默认“本地优先”，下载行为属于 I/O 操作：
- 推荐在上层以异步方式调用（本模块提供 sync 实现，便于 `asyncio.to_thread` 包装）。
- 对网络不通/权限受限场景必须可降级（抛出明确异常）。
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .model_registry import ModelProfile, ModelRegistry


class ModelDownloadError(Exception):
    """模型下载/校验失败。"""


ProgressCallback = Callable[[int, Optional[int]], None]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


class ModelDownloader:
    """模型下载与缓存管理。"""

    def __init__(
        self,
        registry: ModelRegistry,
        *,
        download_dir: Optional[os.PathLike] = None,
        allow_network: bool = True,
        timeout_seconds: int = 60,
    ):
        self.registry = registry
        self.download_dir = Path(download_dir) if download_dir else registry.models_dir
        self.allow_network = bool(allow_network)
        self.timeout_seconds = max(5, int(timeout_seconds))

    def is_available(self, model: ModelProfile) -> bool:
        """判断模型权重是否已在本地可用。"""
        path = self._resolve_target_path(model)
        return path.exists()

    def ensure_available(
        self,
        model: ModelProfile,
        *,
        force: bool = False,
        progress: Optional[ProgressCallback] = None,
    ) -> Path:
        """
        确保模型权重在本地存在；若不存在则下载。

        返回：最终文件路径（可能是已有文件）。
        """
        target_path = self._resolve_target_path(model)
        if target_path.exists() and not force:
            self._verify_checksum_if_needed(model, target_path)
            return target_path

        # model.path 已指定但不存在：尝试从 url 下载到该路径（若 path 是相对路径则落在 repo root 下）
        url = model.url
        if not url:
            raise ModelDownloadError(f"模型 {model.model_id} 本地不存在且未配置 url，无法下载")

        if not self.allow_network:
            raise ModelDownloadError("当前配置禁止网络下载（allow_network=False）")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        self._download_to_file(url, target_path, expected_sha256=model.sha256, progress=progress)
        return target_path

    def _resolve_target_path(self, model: ModelProfile) -> Path:
        # 复用 registry 的路径解析逻辑
        return self.registry.resolve_model_path(model)

    def _verify_checksum_if_needed(self, model: ModelProfile, path: Path) -> None:
        if not model.sha256:
            return
        actual = self._sha256_file(path)
        if actual.lower() != str(model.sha256).lower():
            raise ModelDownloadError(
                f"模型校验失败: {model.model_id} sha256 不匹配（expected={model.sha256}, actual={actual}）"
            )

    def _sha256_file(self, path: Path, chunk_size: int = 1024 * 1024) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    def _download_to_file(
        self,
        url: str,
        target_path: Path,
        *,
        expected_sha256: Optional[str],
        progress: Optional[ProgressCallback],
    ) -> None:
        """
        下载到目标路径（原子写入策略：先写临时文件，再替换）。

        - 若 url 为本地路径（file:// 或 绝对/相对路径），则走本地复制。
        - HTTP/HTTPS 通过 requests 进行流式下载。
        """
        # 本地路径/文件协议
        if url.startswith("file://"):
            src = Path(url[len("file://") :])
            src = src if src.is_absolute() else (_repo_root() / src)
            if not src.exists():
                raise ModelDownloadError(f"本地源文件不存在: {src}")
            self._copy_atomic(src, target_path, expected_sha256=expected_sha256)
            return

        maybe_path = Path(url)
        if maybe_path.exists():
            src = maybe_path if maybe_path.is_absolute() else (_repo_root() / maybe_path)
            if not src.exists():
                raise ModelDownloadError(f"本地源文件不存在: {src}")
            self._copy_atomic(src, target_path, expected_sha256=expected_sha256)
            return

        # 网络下载
        if not url.startswith(("http://", "https://")):
            raise ModelDownloadError(f"不支持的 url 协议: {url}")

        try:
            import requests  # type: ignore
        except Exception as e:
            raise ModelDownloadError("缺少依赖：请安装 requests 以支持 HTTP 下载") from e

        with tempfile.NamedTemporaryFile(
            mode="wb", delete=False, dir=str(target_path.parent), prefix=target_path.name, suffix=".part"
        ) as tmp:
            tmp_path = Path(tmp.name)

        try:
            h = hashlib.sha256() if expected_sha256 else None
            downloaded = 0

            r = requests.get(url, stream=True, timeout=self.timeout_seconds)
            try:
                r.raise_for_status()
                total = r.headers.get("Content-Length")
                total_int = int(total) if total and total.isdigit() else None

                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        f.write(chunk)
                        downloaded += len(chunk)
                        if h is not None:
                            h.update(chunk)
                        if progress:
                            progress(downloaded, total_int)
            finally:
                try:
                    r.close()
                except Exception:
                    pass

            if expected_sha256 and h is not None:
                actual = h.hexdigest()
                if actual.lower() != expected_sha256.lower():
                    raise ModelDownloadError(f"下载文件 sha256 不匹配（expected={expected_sha256}, actual={actual}）")

            # 原子替换
            tmp_path.replace(target_path)
        except Exception:
            # 失败时尽量清理临时文件
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
            raise

    def _copy_atomic(self, src: Path, dst: Path, *, expected_sha256: Optional[str]) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb", delete=False, dir=str(dst.parent), prefix=dst.name, suffix=".copy.part"
        ) as tmp:
            tmp_path = Path(tmp.name)

        try:
            shutil.copyfile(src, tmp_path)
            if expected_sha256:
                actual = self._sha256_file(tmp_path)
                if actual.lower() != expected_sha256.lower():
                    raise ModelDownloadError(
                        f"复制文件 sha256 不匹配（expected={expected_sha256}, actual={actual}）"
                    )
            tmp_path.replace(dst)
        except Exception:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
            raise
