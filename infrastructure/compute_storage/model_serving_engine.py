"""
模型服务引擎：统一管理 AI 模型注册、加载与推理。

当前实现重点：
- 缺少可选依赖时自动降级到 mock，而不是直接崩溃
- 保持异步接口稳定，供上层模块按现有方式调用
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class ModelType(Enum):
    """模型类型枚举。"""

    SPEECH_ASR = "speech_asr"
    SPEECH_TTS = "speech_tts"
    VISION_FACE = "vision_face"
    VISION_EMOTION = "vision_emotion"
    NLP_LLM = "nlp_llm"
    NLP_EMBEDDING = "nlp_embedding"
    THREED_MODEL = "3d_model"


@dataclass
class ModelConfig:
    """模型配置。"""

    model_id: str
    model_type: ModelType
    model_path: str
    model_format: str
    device: str
    memory_usage: int
    load_timeout: int = 30


class ModelInstance:
    """模型实例。"""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.model: Any = None
        self.is_loaded = False
        self.load_time: Optional[float] = None
        self.inference_count = 0
        self.last_used: Optional[float] = None

    async def load_model(self) -> None:
        """异步加载模型。"""
        try:
            logger.info("正在加载模型: %s", self.config.model_id)

            if self.config.model_type == ModelType.SPEECH_ASR:
                await self._load_speech_asr_model()
            elif self.config.model_type == ModelType.NLP_LLM:
                await self._load_llm_model()
            elif self.config.model_type == ModelType.VISION_FACE:
                await self._load_vision_model()
            else:
                self.model = MockGenericModel(self.config.model_id)

            self.is_loaded = True
            self.load_time = time.time()
            logger.info("模型加载完成: %s", self.config.model_id)
        except Exception as exc:
            logger.error("模型加载失败 %s: %s", self.config.model_id, exc)
            raise

    async def _load_speech_asr_model(self) -> None:
        """加载语音识别模型。"""
        try:
            import whisper  # type: ignore

            self.model = whisper.load_model("base")
        except ImportError:
            logger.warning("Whisper 未安装，使用 MockASRModel")
            self.model = MockASRModel()

    async def _load_llm_model(self) -> None:
        """加载大语言模型。"""
        try:
            import ollama  # type: ignore

            self.model = ollama
        except ImportError:
            logger.warning("Ollama 未安装，使用 MockLLM")
            self.model = MockLLM()

    async def _load_vision_model(self) -> None:
        """加载视觉模型。"""
        try:
            import insightface  # type: ignore

            app = insightface.app.FaceAnalysis()
            app.prepare(ctx_id=0)
            self.model = app
        except ImportError:
            logger.warning("InsightFace 未安装，使用 MockVisionModel")
            self.model = MockVisionModel()


class ModelServingEngine:
    """模型服务引擎。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.models: Dict[str, ModelInstance] = {}
        self.model_registry: Dict[ModelType, List[str]] = {}
        self.loading_lock = asyncio.Lock()
        self.initialized = False

    async def initialize(self) -> None:
        """初始化模型服务引擎。"""
        if self.initialized:
            return

        logger.info("初始化模型服务引擎...")
        await self._register_core_models()
        self.initialized = True
        logger.info("模型服务引擎初始化完成")

    async def _register_core_models(self) -> None:
        """注册核心模型。"""
        core_models = [
            ModelConfig(
                model_id="whisper_base",
                model_type=ModelType.SPEECH_ASR,
                model_path="models/speech/whisper-base",
                model_format="pytorch",
                device="cuda",
                memory_usage=1024,
            ),
            ModelConfig(
                model_id="llama3.1_8b",
                model_type=ModelType.NLP_LLM,
                model_path="models/nlp/llama3.1-8b",
                model_format="gguf",
                device="cuda",
                memory_usage=8192,
            ),
            ModelConfig(
                model_id="insightface",
                model_type=ModelType.VISION_FACE,
                model_path="models/vision/insightface",
                model_format="onnx",
                device="cuda",
                memory_usage=512,
            ),
        ]

        for config in core_models:
            await self.register_model(config)

    async def register_model(self, config: ModelConfig) -> bool:
        """注册模型。"""
        async with self.loading_lock:
            if config.model_id in self.models:
                logger.warning("模型已存在: %s", config.model_id)
                return False

            self.models[config.model_id] = ModelInstance(config)
            self.model_registry.setdefault(config.model_type, []).append(config.model_id)
            logger.info("模型注册成功: %s", config.model_id)
            return True

    async def get_model(self, model_id: str, auto_load: bool = True) -> Optional[ModelInstance]:
        """获取模型实例。"""
        instance = self.models.get(model_id)
        if instance is None:
            logger.error("模型未找到: %s", model_id)
            return None

        if auto_load and not instance.is_loaded:
            await instance.load_model()

        return instance

    async def inference(self, model_id: str, input_data: Any, **kwargs: Any) -> Any:
        """执行模型推理。"""
        instance = await self.get_model(model_id)
        if instance is None or not instance.is_loaded:
            raise ValueError(f"模型不可用: {model_id}")

        instance.inference_count += 1
        instance.last_used = time.time()

        if instance.config.model_type == ModelType.SPEECH_ASR:
            return await self._speech_asr_inference(instance, input_data, **kwargs)
        if instance.config.model_type == ModelType.NLP_LLM:
            return await self._llm_inference(instance, input_data, **kwargs)
        if instance.config.model_type == ModelType.VISION_FACE:
            return await self._vision_inference(instance, input_data, **kwargs)

        raise ValueError(f"不支持的模型类型: {instance.config.model_type}")

    async def _speech_asr_inference(self, instance: ModelInstance, audio_data: Any, **kwargs: Any) -> str:
        if hasattr(instance.model, "transcribe"):
            result = instance.model.transcribe(audio_data)
            if isinstance(result, dict):
                return str(result.get("text", ""))
            return str(result)
        return "mock transcription"

    async def _llm_inference(self, instance: ModelInstance, prompt: str, **kwargs: Any) -> str:
        if hasattr(instance.model, "generate"):
            return str(instance.model.generate(prompt))
        return f"LLM响应: {prompt}"

    async def _vision_inference(self, instance: ModelInstance, image_data: Any, **kwargs: Any) -> Any:
        if hasattr(instance.model, "get"):
            return instance.model.get(image_data)
        return []


class MockASRModel:
    """Whisper 缺失时的回退模型。"""

    def transcribe(self, audio_data: Any) -> Dict[str, str]:
        return {"text": "mock transcription"}


class MockLLM:
    """LLM 缺失时的回退模型。"""

    def generate(self, prompt: str) -> str:
        return f"模拟LLM响应: {prompt}"


class MockVisionModel:
    """视觉模型缺失时的回退模型。"""

    def get(self, image: Any) -> List[Dict[str, Any]]:
        return [{"bbox": [0, 0, 100, 100], "confidence": 0.5}]


class MockGenericModel:
    """通用回退模型。"""

    def __init__(self, model_id: str):
        self.model_id = model_id


model_serving_engine = ModelServingEngine()
