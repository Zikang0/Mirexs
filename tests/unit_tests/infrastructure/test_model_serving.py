"""
模型服务引擎单元测试。
"""

import unittest

from infrastructure.compute_storage.model_serving_engine import (
    MockASRModel,
    MockLLM,
    ModelConfig,
    ModelServingEngine,
    ModelType,
)


class TestModelServingEngine(unittest.IsolatedAsyncioTestCase):
    """验证模型注册、推理与 mock 回退行为。"""

    async def asyncSetUp(self):
        self.engine = ModelServingEngine()

    async def test_register_model_records_registry(self):
        config = ModelConfig(
            model_id="test_llm",
            model_type=ModelType.NLP_LLM,
            model_path="models/test",
            model_format="mock",
            device="cpu",
            memory_usage=128,
        )

        registered = await self.engine.register_model(config)

        self.assertTrue(registered)
        self.assertIn("test_llm", self.engine.model_registry[ModelType.NLP_LLM])

    async def test_llm_inference_uses_loaded_model(self):
        config = ModelConfig(
            model_id="mock_llm",
            model_type=ModelType.NLP_LLM,
            model_path="models/mock",
            model_format="mock",
            device="cpu",
            memory_usage=128,
        )
        await self.engine.register_model(config)
        instance = await self.engine.get_model("mock_llm", auto_load=False)
        instance.model = MockLLM()
        instance.is_loaded = True

        result = await self.engine.inference("mock_llm", "hello")

        self.assertIn("hello", result)

    async def test_asr_inference_supports_mock_model(self):
        config = ModelConfig(
            model_id="mock_asr",
            model_type=ModelType.SPEECH_ASR,
            model_path="models/mock_asr",
            model_format="mock",
            device="cpu",
            memory_usage=64,
        )
        await self.engine.register_model(config)
        instance = await self.engine.get_model("mock_asr", auto_load=False)
        instance.model = MockASRModel()
        instance.is_loaded = True

        result = await self.engine.inference("mock_asr", b"audio")

        self.assertEqual(result, "mock transcription")
