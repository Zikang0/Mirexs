"""
模型管理器（Model Manager）

职责：
1) 连接 ModelRegistry（元数据）与 ModelDownloader（权重获取），并维护“生命周期状态”。
2) 为 SmartModelRouter 提供 `ensure_loaded(...)` 等能力，使路由与加载解耦。

实现边界（MVP 口径）：
- 本模块默认**不直接绑定具体推理引擎**（vLLM/llama.cpp/transformers），
  仅提供生命周期与淘汰策略的“控制面”。
- 真实的模型加载/卸载建议由 compute_storage 层实现，并以可注入 loader 形式接入。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from .model_downloader import ModelDownloader
from .model_registry import ModelProfile, ModelRegistry


class ModelManagerError(Exception):
    """模型管理器异常（下载/加载/淘汰等）。"""


class ModelLifecycleState(str, Enum):
    REGISTERED = "registered"
    DOWNLOADED = "downloaded"
    LOADED = "loaded"
    WARM = "warm"
    IN_USE = "in_use"
    EVICTED = "evicted"
    FAILED = "failed"


LoaderFn = Callable[[ModelProfile, Path], Awaitable[Any]]
UnloaderFn = Callable[[ModelProfile, Any], Awaitable[None]]


@dataclass
class ModelRuntimeRecord:
    """运行时记录（内存态）。"""

    model: ModelProfile
    local_path: Optional[Path] = None
    state: ModelLifecycleState = ModelLifecycleState.REGISTERED
    loaded_object: Any = None
    last_used_ts: float = 0.0
    load_ts: float = 0.0
    failure_count: int = 0
    last_error: Optional[str] = None

    def touch(self) -> None:
        self.last_used_ts = time.time()


class ModelManager:
    """
    模型生命周期管理器。

    - `ensure_downloaded`：确保权重到位
    - `ensure_loaded`：确保加载完成（可注入 loader）
    - `evict_if_needed`：按 LRU 淘汰
    """

    def __init__(
        self,
        registry: ModelRegistry,
        downloader: Optional[ModelDownloader] = None,
        *,
        max_loaded_models: int = 2,
        loader: Optional[LoaderFn] = None,
        unloader: Optional[UnloaderFn] = None,
    ):
        self.registry = registry
        self.downloader = downloader or ModelDownloader(registry)
        self.max_loaded_models = max(1, int(max_loaded_models))
        self._loader = loader
        self._unloader = unloader

        self._records: Dict[str, ModelRuntimeRecord] = {}
        self._lock = asyncio.Lock()

    def get_record(self, model_id: str) -> Optional[ModelRuntimeRecord]:
        return self._records.get(model_id)

    async def ensure_downloaded(self, model: ModelProfile, *, force: bool = False) -> Path:
        """确保模型权重下载完成并返回本地路径。"""
        try:
            path = await asyncio.to_thread(self.downloader.ensure_available, model, force=force)
        except Exception as e:
            raise ModelManagerError(f"下载模型失败: {model.model_id}: {e}") from e

        async with self._lock:
            rec = self._records.get(model.model_id) or ModelRuntimeRecord(model=model)
            rec.local_path = path
            rec.state = ModelLifecycleState.DOWNLOADED
            rec.last_error = None
            self._records[model.model_id] = rec
        return path

    async def ensure_loaded(self, model: ModelProfile, *, force_download: bool = False) -> ModelRuntimeRecord:
        """
        确保模型已“加载”。

        默认行为：
        - 若未提供 loader：仅标记为 LOADED（不做实际加载），用于联调与契约对齐。
        - 若提供 loader：执行 loader(model, local_path) 并保存 loaded_object。
        """
        async with self._lock:
            existing = self._records.get(model.model_id)
            if existing and existing.state in {ModelLifecycleState.LOADED, ModelLifecycleState.WARM, ModelLifecycleState.IN_USE}:
                existing.touch()
                return existing

        local_path = await self.ensure_downloaded(model, force=force_download)

        async with self._lock:
            rec = self._records.get(model.model_id) or ModelRuntimeRecord(model=model)
            rec.local_path = local_path
            self._records[model.model_id] = rec

        # 执行加载（可能较慢），不在锁内
        try:
            loaded_obj: Any = None
            if self._loader is not None:
                loaded_obj = await self._loader(model, local_path)

            async with self._lock:
                rec = self._records[model.model_id]
                rec.loaded_object = loaded_obj
                rec.state = ModelLifecycleState.LOADED
                rec.load_ts = time.time()
                rec.touch()
                rec.last_error = None
        except Exception as e:
            async with self._lock:
                rec = self._records.get(model.model_id) or ModelRuntimeRecord(model=model)
                rec.state = ModelLifecycleState.FAILED
                rec.failure_count += 1
                rec.last_error = str(e)
                self._records[model.model_id] = rec
            raise ModelManagerError(f"加载模型失败: {model.model_id}: {e}") from e

        await self.evict_if_needed()
        return self._records[model.model_id]

    async def mark_in_use(self, model_id: str) -> None:
        """标记模型正在使用（用于更精细的淘汰策略）。"""
        async with self._lock:
            rec = self._records.get(model_id)
            if not rec:
                return
            rec.state = ModelLifecycleState.IN_USE
            rec.touch()

    async def mark_idle(self, model_id: str) -> None:
        """标记模型空闲（允许淘汰）。"""
        async with self._lock:
            rec = self._records.get(model_id)
            if not rec:
                return
            if rec.state == ModelLifecycleState.IN_USE:
                rec.state = ModelLifecycleState.LOADED
            rec.touch()

    async def evict_if_needed(self) -> None:
        """按 LRU 淘汰，确保 loaded 数量不超过上限。"""
        async with self._lock:
            loaded = [
                r
                for r in self._records.values()
                if r.state in {ModelLifecycleState.LOADED, ModelLifecycleState.WARM, ModelLifecycleState.IN_USE}
            ]
            if len(loaded) <= self.max_loaded_models:
                return

            # 仅淘汰非 IN_USE 的最久未使用记录
            evictable = [r for r in loaded if r.state != ModelLifecycleState.IN_USE]
            evictable.sort(key=lambda r: (r.last_used_ts or 0.0))
            to_evict = evictable[: max(0, len(loaded) - self.max_loaded_models)]

        # 不在锁内执行卸载
        for rec in to_evict:
            await self._evict_one(rec.model.model_id)

    async def _evict_one(self, model_id: str) -> None:
        async with self._lock:
            rec = self._records.get(model_id)
            if not rec:
                return
            if rec.state == ModelLifecycleState.IN_USE:
                return
            model = rec.model
            loaded_obj = rec.loaded_object

        try:
            if self._unloader is not None and loaded_obj is not None:
                await self._unloader(model, loaded_obj)
        finally:
            async with self._lock:
                rec = self._records.get(model_id)
                if not rec:
                    return
                rec.loaded_object = None
                rec.state = ModelLifecycleState.EVICTED
                rec.touch()

