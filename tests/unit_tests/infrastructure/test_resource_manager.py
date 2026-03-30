"""
资源管理器单元测试。
"""

import time
import unittest

from infrastructure.compute_storage.resource_manager import (
    ResourceManager,
    ResourceRequest,
    ResourceType,
    ResourceUsage,
)


class TestResourceManager(unittest.IsolatedAsyncioTestCase):
    """验证资源申请、释放与配置兼容行为。"""

    def setUp(self):
        self.resource_manager = ResourceManager(
            {
                "enable_gpu_monitor": False,
                "history_limit": 8,
            }
        )

    async def test_request_and_release_memory_resources(self):
        self.resource_manager.resource_usage[ResourceType.MEMORY] = ResourceUsage(
            resource_type=ResourceType.MEMORY,
            used=256,
            total=1024,
            percentage=25.0,
            timestamp=time.time(),
        )

        allocation = await self.resource_manager.request_resources(
            ResourceRequest(resource_type=ResourceType.MEMORY, amount=128)
        )

        self.assertIsNotNone(allocation)
        self.assertEqual(self.resource_manager.resource_usage[ResourceType.MEMORY].used, 384)

        await self.resource_manager.release_resources(allocation)
        self.assertEqual(self.resource_manager.resource_usage[ResourceType.MEMORY].used, 256)

    async def test_request_resources_rejects_insufficient_capacity(self):
        self.resource_manager.resource_usage[ResourceType.GPU] = ResourceUsage(
            resource_type=ResourceType.GPU,
            used=900,
            total=1024,
            percentage=87.89,
            timestamp=time.time(),
        )

        allocation = await self.resource_manager.request_resources(
            ResourceRequest(resource_type=ResourceType.GPU, amount=256)
        )

        self.assertIsNone(allocation)

    def test_constructor_accepts_config(self):
        self.assertFalse(self.resource_manager.enable_gpu_monitor)
        self.assertEqual(self.resource_manager.history_limit, 8)
