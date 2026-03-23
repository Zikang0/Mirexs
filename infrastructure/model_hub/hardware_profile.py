"""
硬件画像（Hardware Profile）

该模块为“多模型智能路由”提供硬件侧的可用资源快照与缓存能力。

设计目标：
1) **统一口径**：向上只暴露路由所需的关键字段（VRAM/RAM/CPU/OS 等）。
2) **本地优先**：不依赖云端；尽量使用本机可用能力（psutil/GPUtil/nvidia-smi）。
3) **可降级**：当依赖缺失或平台受限时，返回“尽力而为”的快照，保证路由可继续运行。
4) **可缓存**：默认 30s 缓存一次，避免每次路由都调用系统命令。
"""

from __future__ import annotations

import asyncio
import os
import platform
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


def _bytes_to_gb(value_bytes: float) -> float:
    return float(value_bytes) / (1024.0**3)


def _clamp_non_negative(value: float) -> float:
    return float(value) if value > 0 else 0.0


@dataclass(frozen=True)
class HardwareProfile:
    """路由层使用的硬件快照（稳定 Schema）。"""

    gpu_name: str = "Unknown"
    vram_total_gb: float = 0.0
    vram_free_gb: float = 0.0
    cuda_version: Optional[str] = None

    cpu_cores_logical: int = 0
    ram_total_gb: float = 0.0
    ram_free_gb: float = 0.0

    os: str = field(default_factory=lambda: platform.system().lower())
    is_apple_silicon: bool = field(
        default_factory=lambda: platform.system() == "Darwin"
        and platform.machine().lower() in {"arm64", "aarch64"}
    )

    timestamp: float = field(default_factory=lambda: time.time())

    # 原始硬件信息（可选，用于调试/审计；不建议跨边界直接依赖该字段）
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为可 JSON 化的 dict。"""
        return {
            "gpu_name": self.gpu_name,
            "vram_total_gb": self.vram_total_gb,
            "vram_free_gb": self.vram_free_gb,
            "cuda_version": self.cuda_version,
            "cpu_cores_logical": self.cpu_cores_logical,
            "ram_total_gb": self.ram_total_gb,
            "ram_free_gb": self.ram_free_gb,
            "os": self.os,
            "is_apple_silicon": self.is_apple_silicon,
            "timestamp": self.timestamp,
            "raw": self.raw,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HardwareProfile":
        """从 dict 反序列化（宽松模式：缺字段使用默认值）。"""
        return cls(
            gpu_name=str(data.get("gpu_name", "Unknown")),
            vram_total_gb=float(data.get("vram_total_gb", 0.0) or 0.0),
            vram_free_gb=float(data.get("vram_free_gb", 0.0) or 0.0),
            cuda_version=data.get("cuda_version"),
            cpu_cores_logical=int(data.get("cpu_cores_logical", 0) or 0),
            ram_total_gb=float(data.get("ram_total_gb", 0.0) or 0.0),
            ram_free_gb=float(data.get("ram_free_gb", 0.0) or 0.0),
            os=str(data.get("os", platform.system().lower())),
            is_apple_silicon=bool(data.get("is_apple_silicon", False)),
            timestamp=float(data.get("timestamp", time.time()) or time.time()),
            raw=dict(data.get("raw", {}) or {}),
        )


class HardwareProfiler:
    """硬件画像采集器（带缓存）。"""

    def __init__(self, cache_ttl_seconds: int = 30):
        self.cache_ttl_seconds = max(1, int(cache_ttl_seconds))
        self._cached: Optional[HardwareProfile] = None
        self._cached_at: float = 0.0
        self._lock = asyncio.Lock()

    async def get_snapshot(self, *, force_refresh: bool = False) -> HardwareProfile:
        """获取硬件快照（默认使用缓存；必要时刷新）。"""
        async with self._lock:
            now = time.time()
            if (
                not force_refresh
                and self._cached is not None
                and (now - self._cached_at) <= self.cache_ttl_seconds
            ):
                return self._cached

            profile = await asyncio.to_thread(self._collect_snapshot_sync)
            self._cached = profile
            self._cached_at = now
            return profile

    def _collect_snapshot_sync(self) -> HardwareProfile:
        """同步采集硬件快照（可能调用系统命令）。"""
        os_name = platform.system().lower()
        cpu_cores_logical = int(os.cpu_count() or 0)

        ram_total_gb, ram_free_gb = self._probe_ram_gb()
        (
            gpu_name,
            vram_total_gb,
            vram_free_gb,
            cuda_version,
            gpu_raw,
        ) = self._probe_gpu()

        raw: Dict[str, Any] = {}
        if gpu_raw:
            raw["gpu"] = gpu_raw

        # 尝试补充 platform_adapters 的完整检测结果（不强依赖）
        try:
            from infrastructure.platform_adapters.hardware_detector import HardwareDetector

            raw["hardware_detector"] = HardwareDetector().detect_all()
        except Exception:
            # 不应因为“调试信息采集失败”而影响主逻辑
            pass

        return HardwareProfile(
            gpu_name=gpu_name,
            vram_total_gb=_clamp_non_negative(vram_total_gb),
            vram_free_gb=_clamp_non_negative(vram_free_gb),
            cuda_version=cuda_version,
            cpu_cores_logical=cpu_cores_logical,
            ram_total_gb=_clamp_non_negative(ram_total_gb),
            ram_free_gb=_clamp_non_negative(ram_free_gb),
            os=os_name,
            raw=raw,
        )

    def _probe_ram_gb(self) -> Tuple[float, float]:
        """探测内存总量与空闲量（GB）。"""
        try:
            import psutil  # type: ignore

            mem = psutil.virtual_memory()
            return _bytes_to_gb(mem.total), _bytes_to_gb(getattr(mem, "available", mem.free))
        except Exception:
            # psutil 不可用或探测失败：返回 0，由路由层做降级决策
            return 0.0, 0.0

    def _probe_gpu(self) -> Tuple[str, float, float, Optional[str], Dict[str, Any]]:
        """探测 GPU 与显存信息（尽量提供 free/total）。"""
        # 1) 优先尝试 nvidia-smi（对 NVIDIA 最准确，且可拿到 free）
        smi = self._probe_nvidia_smi()
        if smi is not None:
            name, total_gb, free_gb, cuda_ver, raw = smi
            return name, total_gb, free_gb, cuda_ver, raw

        # 2) 尝试 GPUtil（跨平台，但依赖安装）
        gputil = self._probe_gputil()
        if gputil is not None:
            name, total_gb, free_gb, raw = gputil
            return name, total_gb, free_gb, None, raw

        # 3) 最后回退：仅返回 Unknown
        return "Unknown", 0.0, 0.0, None, {}

    def _probe_gputil(self) -> Optional[Tuple[str, float, float, Dict[str, Any]]]:
        try:
            import GPUtil  # type: ignore

            gpus = GPUtil.getGPUs()
            if not gpus:
                return None
            gpu = gpus[0]
            total_mb = float(getattr(gpu, "memoryTotal", 0.0) or 0.0)
            used_mb = float(getattr(gpu, "memoryUsed", 0.0) or 0.0)
            free_mb = float(getattr(gpu, "memoryFree", max(0.0, total_mb - used_mb)) or 0.0)
            raw = {
                "name": getattr(gpu, "name", "Unknown"),
                "memory_total_mb": total_mb,
                "memory_used_mb": used_mb,
                "memory_free_mb": free_mb,
                "load": float(getattr(gpu, "load", 0.0) or 0.0),
                "uuid": getattr(gpu, "uuid", None),
            }
            return str(raw["name"]), total_mb / 1024.0, free_mb / 1024.0, raw
        except Exception:
            return None

    def _probe_nvidia_smi(
        self,
    ) -> Optional[Tuple[str, float, float, Optional[str], Dict[str, Any]]]:
        """使用 nvidia-smi 获取 GPU 名称/显存与 CUDA 版本。"""
        try:
            # 通过 query-gpu 结构化输出（单位 MB），避免解析表格
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,memory.free,driver_version",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None

            first_line = result.stdout.strip().splitlines()[0].strip()
            # 期望格式：Name, total, free, driver
            parts = [p.strip() for p in first_line.split(",")]
            if len(parts) < 4:
                return None

            name = parts[0]
            total_mb = float(parts[1])
            free_mb = float(parts[2])
            driver_version = parts[3]

            cuda_version = self._probe_cuda_version_from_smi()

            raw = {
                "name": name,
                "memory_total_mb": total_mb,
                "memory_free_mb": free_mb,
                "driver_version": driver_version,
                "cuda_version": cuda_version,
            }
            return name, total_mb / 1024.0, free_mb / 1024.0, cuda_version, raw
        except FileNotFoundError:
            return None
        except Exception:
            return None

    def _probe_cuda_version_from_smi(self) -> Optional[str]:
        """从 `nvidia-smi` banner 中解析 CUDA Version（如果存在）。"""
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return None
            # 示例：| NVIDIA-SMI 551.23       Driver Version: 551.23       CUDA Version: 12.4     |
            match = re.search(r"CUDA Version:\s*([0-9]+(?:\.[0-9]+)?)", result.stdout)
            return match.group(1) if match else None
        except Exception:
            return None

