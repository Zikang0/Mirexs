"""
消息总线单元测试。
"""

import unittest

from infrastructure.communication.message_bus import MessageBus, MessageTopic


class TestMessageBus(unittest.IsolatedAsyncioTestCase):
    """验证消息总线的同步/异步兼容行为。"""

    async def test_async_publish_dispatches_enum_topic(self):
        bus = MessageBus()
        received = []

        async def handler(message):
            received.append(message.payload["value"])

        bus.subscribe(MessageTopic.USER_INPUT, handler)
        message_id = await bus.publish(MessageTopic.USER_INPUT, {"value": 1})

        self.assertIsInstance(message_id, str)
        self.assertEqual(received, [1])

    def test_sync_publish_dispatches_string_topic(self):
        bus = MessageBus()
        received = []

        def handler(message):
            received.append(message.payload["value"])

        bus.subscribe("text_input_command", handler)
        message_id = bus.publish("text_input_command", {"value": 2})

        self.assertIsInstance(message_id, str)
        self.assertEqual(received, [2])

    async def test_send_message_alias_reuses_publish_pipeline(self):
        bus = MessageBus()
        received = []

        async def handler(message):
            received.append(message.source)

        bus.subscribe("system_alerts", handler)
        await bus.send_message("system_alerts", {"ok": True}, source="monitor")

        self.assertEqual(received, ["monitor"])
