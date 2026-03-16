"""
输入系统集成模块
提供统一的输入系统管理接口，整合语音识别、计算机视觉和文本输入功能
"""

import asyncio
import logging
import threading
import time
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum

# 配置日志
logger = logging.getLogger(__name__)

# 导入子系统
try:
    from .speech_recognizer import (
        SpeechRecognitionManager,
        speech_recognition_manager,
        initialize_speech_recognition,
        get_speech_recognition_status,
        transcribe_audio,
        detect_wake_word,
        authenticate_user
    )
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"语音识别模块导入失败: {e}")
    SPEECH_RECOGNITION_AVAILABLE = False

try:
    from .computer_vision import (
        ComputerVisionSystem,
        computer_vision_system,
        get_computer_vision_system,
        initialize_computer_vision,
        process_image,
        get_vision_system_status
    )
    COMPUTER_VISION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"计算机视觉模块导入失败: {e}")
    COMPUTER_VISION_AVAILABLE = False

try:
    from .text_input import (
        TextInputSystem,
        TextInputConfig,
        get_text_input_system,
        initialize_text_input_system,
        process_text_input,
        get_text_input_status
    )
    TEXT_INPUT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"文本输入模块导入失败: {e}")
    TEXT_INPUT_AVAILABLE = False


class InputMode(Enum):
    """输入模式枚举"""
    SPEECH = "speech"
    VISION = "vision"
    TEXT = "text"
    MULTIMODAL = "multimodal"
    AUTOMATIC = "automatic"


@dataclass
class InputSystemConfig:
    """输入系统配置"""
    # 子系统启用状态
    speech_enabled: bool = True
    vision_enabled: bool = True
    text_enabled: bool = True
    
    # 输入模式配置
    default_mode: InputMode = InputMode.MULTIMODAL
    auto_mode_switch: bool = True
    mode_switch_threshold: float = 0.7  # 模式切换置信度阈值
    
    # 性能配置
    realtime_processing: bool = True
    parallel_processing: bool = True
    max_parallel_tasks: int = 5
    processing_timeout: float = 10.0  # 秒
    
    # 存储配置
    save_input_data: bool = True
    data_retention_days: int = 30
    auto_save_interval: int = 300  # 秒
    
    # 隐私配置
    anonymize_input: bool = True
    encrypt_stored_data: bool = True
    auto_clear_sensitive_data: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "speech_enabled": self.speech_enabled,
            "vision_enabled": self.vision_enabled,
            "text_enabled": self.text_enabled,
            "default_mode": self.default_mode.value,
            "auto_mode_switch": self.auto_mode_switch,
            "mode_switch_threshold": self.mode_switch_threshold,
            "realtime_processing": self.realtime_processing,
            "parallel_processing": self.parallel_processing,
            "max_parallel_tasks": self.max_parallel_tasks,
            "processing_timeout": self.processing_timeout,
            "save_input_data": self.save_input_data,
            "data_retention_days": self.data_retention_days,
            "auto_save_interval": self.auto_save_interval,
            "anonymize_input": self.anonymize_input,
            "encrypt_stored_data": self.encrypt_stored_data,
            "auto_clear_sensitive_data": self.auto_clear_sensitive_data
        }


class InputSystemManager:
    """输入系统管理器 - 整合所有输入子系统"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化输入系统管理器
        
        Args:
            config: 配置字典
        """
        # 配置
        self.config = InputSystemConfig()
        if config:
            self._update_config(config)
        
        # 子系统实例
        self.speech_system = None
        self.vision_system = None
        self.text_system = None
        
        # 状态管理
        self.is_initialized = False
        self.is_active = False
        self.current_mode = self.config.default_mode
        self.last_mode_switch_time = 0
        
        # 线程安全
        self.lock = threading.RLock()
        
        # 回调注册
        self.input_callbacks = []  # (input_type, callback_func)
        self.error_handlers = []
        
        # 会话管理
        self.input_sessions = {}
        self.current_session_id = None
        
        # 性能统计
        self.performance_stats = {
            "speech_processing_time": [],
            "vision_processing_time": [],
            "text_processing_time": [],
            "total_inputs": 0,
            "successful_inputs": 0,
            "failed_inputs": 0
        }
        
        logger.info("输入系统管理器初始化完成")
    
    def _update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        for key, value in config.items():
            if hasattr(self.config, key):
                # 处理特殊类型转换
                if key == "default_mode" and isinstance(value, str):
                    try:
                        value = InputMode(value)
                    except ValueError:
                        logger.warning(f"无效的输入模式: {value}, 使用默认值")
                        continue
                setattr(self.config, key, value)
    
    async def initialize(self) -> bool:
        """
        初始化输入系统
        
        Returns:
            bool: 是否初始化成功
        """
        if self.is_initialized:
            logger.warning("输入系统已初始化")
            return True
        
        try:
            logger.info("正在初始化输入系统...")
            
            # 初始化子系统
            subsystems_initialized = []
            
            # 初始化语音识别系统
            if self.config.speech_enabled and SPEECH_RECOGNITION_AVAILABLE:
                try:
                    if not speech_recognition_manager.is_initialized:
                        await initialize_speech_recognition()
                    self.speech_system = speech_recognition_manager
                    subsystems_initialized.append("speech")
                    logger.info("语音识别系统初始化成功")
                except Exception as e:
                    logger.error(f"语音识别系统初始化失败: {e}")
            
            # 初始化计算机视觉系统
            if self.config.vision_enabled and COMPUTER_VISION_AVAILABLE:
                try:
                    if not computer_vision_system.is_initialized:
                        await initialize_computer_vision()
                    self.vision_system = computer_vision_system
                    subsystems_initialized.append("vision")
                    logger.info("计算机视觉系统初始化成功")
                except Exception as e:
                    logger.error(f"计算机视觉系统初始化失败: {e}")
            
            # 初始化文本输入系统
            if self.config.text_enabled and TEXT_INPUT_AVAILABLE:
                try:
                    self.text_system = get_text_input_system()
                    if not self.text_system.is_initialized:
                        # 文本输入系统是同步初始化，我们使用异步包装
                        await asyncio.get_event_loop().run_in_executor(
                            None, initialize_text_input_system
                        )
                    subsystems_initialized.append("text")
                    logger.info("文本输入系统初始化成功")
                except Exception as e:
                    logger.error(f"文本输入系统初始化失败: {e}")
            
            # 检查是否有至少一个子系统初始化成功
            if not subsystems_initialized:
                logger.error("没有子系统初始化成功")
                return False
            
            self.is_initialized = True
            logger.info(f"输入系统初始化完成，激活的子系统: {subsystems_initialized}")
            
            return True
            
        except Exception as e:
            logger.error(f"输入系统初始化失败: {e}")
            return False
    
    async def activate(self) -> bool:
        """
        激活输入系统
        
        Returns:
            bool: 是否激活成功
        """
        if not self.is_initialized:
            if not await self.initialize():
                return False
        
        if self.is_active:
            logger.warning("输入系统已激活")
            return True
        
        try:
            logger.info("正在激活输入系统...")
            
            # 激活子系统
            subsystems_activated = []
            
            # 激活语音识别系统
            if self.speech_system and self.config.speech_enabled:
                try:
                    # 语音识别系统不需要显式激活
                    subsystems_activated.append("speech")
                except Exception as e:
                    logger.error(f"语音识别系统激活失败: {e}")
            
            # 激活计算机视觉系统
            if self.vision_system and self.config.vision_enabled:
                try:
                    # 计算机视觉系统不需要显式激活
                    subsystems_activated.append("vision")
                except Exception as e:
                    logger.error(f"计算机视觉系统激活失败: {e}")
            
            # 激活文本输入系统
            if self.text_system and self.config.text_enabled:
                try:
                    # 文本输入系统需要显式激活
                    if self.text_system.activate():
                        subsystems_activated.append("text")
                except Exception as e:
                    logger.error(f"文本输入系统激活失败: {e}")
            
            # 开始新的输入会话
            await self._start_new_session()
            
            self.is_active = True
            logger.info(f"输入系统激活完成，激活的子系统: {subsystems_activated}")
            
            return True
            
        except Exception as e:
            logger.error(f"输入系统激活失败: {e}")
            return False
    
    async def deactivate(self) -> None:
        """停用输入系统"""
        if not self.is_active:
            return
        
        try:
            logger.info("正在停用输入系统...")
            
            # 停用文本输入系统
            if self.text_system and self.config.text_enabled:
                try:
                    self.text_system.deactivate()
                except Exception as e:
                    logger.error(f"文本输入系统停用失败: {e}")
            
            # 结束当前会话
            await self._end_current_session()
            
            self.is_active = False
            logger.info("输入系统已停用")
            
        except Exception as e:
            logger.error(f"输入系统停用失败: {e}")
    
    async def _start_new_session(self) -> str:
        """开始新的输入会话"""
        session_id = f"session_{int(time.time())}_{threading.get_ident()}"
        self.current_session_id = session_id
        
        self.input_sessions[session_id] = {
            "start_time": time.time(),
            "mode": self.current_mode.value,
            "subsystems_used": [],
            "input_count": 0,
            "successful_inputs": 0,
            "failed_inputs": 0
        }
        
        logger.info(f"开始新的输入会话: {session_id}")
        return session_id
    
    async def _end_current_session(self) -> Optional[str]:
        """结束当前输入会话"""
        if not self.current_session_id:
            return None
        
        session_id = self.current_session_id
        if session_id in self.input_sessions:
            session = self.input_sessions[session_id]
            session["end_time"] = time.time()
            session["duration"] = session["end_time"] - session["start_time"]
            
            # 更新性能统计
            self.performance_stats["total_inputs"] += session["input_count"]
            self.performance_stats["successful_inputs"] += session["successful_inputs"]
            self.performance_stats["failed_inputs"] += session["failed_inputs"]
            
            logger.info(f"结束输入会话 {session_id}: {session}")
        
        self.current_session_id = None
        return session_id
    
    def set_input_mode(self, mode: Union[InputMode, str]) -> bool:
        """
        设置输入模式
        
        Args:
            mode: 输入模式
            
        Returns:
            bool: 是否设置成功
        """
        try:
            if isinstance(mode, str):
                mode = InputMode(mode)
            
            # 检查模式是否可用
            if mode == InputMode.SPEECH and (not self.speech_system or not self.config.speech_enabled):
                logger.error("语音输入模式不可用")
                return False
            elif mode == InputMode.VISION and (not self.vision_system or not self.config.vision_enabled):
                logger.error("视觉输入模式不可用")
                return False
            elif mode == InputMode.TEXT and (not self.text_system or not self.config.text_enabled):
                logger.error("文本输入模式不可用")
                return False
            elif mode == InputMode.MULTIMODAL:
                # 多模态模式需要至少两个子系统
                available_subsystems = 0
                if self.speech_system and self.config.speech_enabled:
                    available_subsystems += 1
                if self.vision_system and self.config.vision_enabled:
                    available_subsystems += 1
                if self.text_system and self.config.text_enabled:
                    available_subsystems += 1
                
                if available_subsystems < 2:
                    logger.error("多模态输入模式需要至少两个可用的子系统")
                    return False
            
            old_mode = self.current_mode
            self.current_mode = mode
            self.last_mode_switch_time = time.time()
            
            logger.info(f"输入模式已从 {old_mode.value} 切换为 {mode.value}")
            return True
            
        except ValueError as e:
            logger.error(f"无效的输入模式: {mode}")
            return False
        except Exception as e:
            logger.error(f"设置输入模式失败: {e}")
            return False
    
    async def process_input(self, 
                           input_data: Any, 
                           input_type: str,
                           mode: Optional[Union[InputMode, str]] = None,
                           **kwargs) -> Dict[str, Any]:
        """
        处理输入数据
        
        Args:
            input_data: 输入数据
            input_type: 输入类型 ('audio', 'image', 'text', 'strokes')
            mode: 处理模式，如果为None则使用当前模式
            **kwargs: 额外参数
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        if not self.is_active:
            if not await self.activate():
                return self._create_error_result("输入系统未激活")
        
        # 确定处理模式
        processing_mode = mode
        if processing_mode is None:
            processing_mode = self.current_mode
        
        if isinstance(processing_mode, str):
            try:
                processing_mode = InputMode(processing_mode)
            except ValueError:
                logger.warning(f"无效的处理模式: {processing_mode}, 使用当前模式")
                processing_mode = self.current_mode
        
        # 更新会话统计
        if self.current_session_id:
            session = self.input_sessions.get(self.current_session_id)
            if session:
                session["input_count"] += 1
        
        try:
            start_time = time.time()
            result = None
            
            # 根据模式处理输入
            if processing_mode == InputMode.SPEECH:
                result = await self._process_speech_input(input_data, **kwargs)
            elif processing_mode == InputMode.VISION:
                result = await self._process_vision_input(input_data, **kwargs)
            elif processing_mode == InputMode.TEXT:
                result = await self._process_text_input(input_data, **kwargs)
            elif processing_mode == InputMode.MULTIMODAL:
                result = await self._process_multimodal_input(input_data, input_type, **kwargs)
            elif processing_mode == InputMode.AUTOMATIC:
                result = await self._process_automatic_input(input_data, input_type, **kwargs)
            else:
                result = self._create_error_result(f"未知的处理模式: {processing_mode}")
            
            processing_time = time.time() - start_time
            
            # 更新性能统计
            if processing_mode == InputMode.SPEECH:
                self.performance_stats["speech_processing_time"].append(processing_time)
            elif processing_mode == InputMode.VISION:
                self.performance_stats["vision_processing_time"].append(processing_time)
            elif processing_mode == InputMode.TEXT:
                self.performance_stats["text_processing_time"].append(processing_time)
            
            # 更新会话统计
            if result.get("success", False):
                if self.current_session_id:
                    session = self.input_sessions.get(self.current_session_id)
                    if session:
                        session["successful_inputs"] += 1
                self.performance_stats["successful_inputs"] += 1
            else:
                if self.current_session_id:
                    session = self.input_sessions.get(self.current_session_id)
                    if session:
                        session["failed_inputs"] += 1
                self.performance_stats["failed_inputs"] += 1
            
            # 添加处理时间信息
            result["processing_time"] = processing_time
            result["mode"] = processing_mode.value
            
            return result
            
        except Exception as e:
            logger.error(f"输入处理失败: {e}")
            return self._create_error_result(str(e))
    
    async def _process_speech_input(self, audio_data: Any, **kwargs) -> Dict[str, Any]:
        """处理语音输入"""
        if not self.speech_system or not self.config.speech_enabled:
            return self._create_error_result("语音识别系统不可用")
        
        try:
            sample_rate = kwargs.get("sample_rate", 16000)
            
            # 检查是否需要唤醒词检测
            if kwargs.get("detect_wake_word", False):
                wake_result = await detect_wake_word(audio_data, sample_rate)
                if not wake_result.detected:
                    return {
                        "success": False,
                        "type": "wake_word_detection",
                        "message": "唤醒词未检测到",
                        "confidence": wake_result.confidence
                    }
            
            # 检查是否需要用户认证
            if kwargs.get("authenticate_user", False):
                auth_result = await authenticate_user(audio_data, sample_rate)
                if not auth_result.authenticated:
                    return {
                        "success": False,
                        "type": "authentication",
                        "message": "用户认证失败",
                        "confidence": auth_result.confidence
                    }
            
            # 转录音频
            language = kwargs.get("language", "auto")
            transcription_result = await transcribe_audio(audio_data, sample_rate, language)
            
            result = {
                "success": True,
                "type": "speech_transcription",
                "text": transcription_result.text,
                "confidence": transcription_result.confidence,
                "language": transcription_result.language,
                "alternatives": transcription_result.alternatives,
                "is_final": transcription_result.is_final
            }
            
            # 如果配置了自动模式切换，尝试根据结果确定是否需要切换模式
            if (self.config.auto_mode_switch and 
                transcription_result.confidence < self.config.mode_switch_threshold):
                result["suggested_mode_switch"] = True
                result["suggested_mode"] = InputMode.TEXT.value
            
            return result
            
        except Exception as e:
            logger.error(f"语音输入处理失败: {e}")
            return self._create_error_result(f"语音处理失败: {e}")
    
    async def _process_vision_input(self, image_data: Any, **kwargs) -> Dict[str, Any]:
        """处理视觉输入"""
        if not self.vision_system or not self.config.vision_enabled:
            return self._create_error_result("计算机视觉系统不可用")
        
        try:
            analysis_types = kwargs.get("analysis_types", None)
            
            # 处理图像
            vision_result = await process_image(image_data, analysis_types)
            
            result = {
                "success": vision_result.get("success", False),
                "type": "vision_analysis",
                "results": vision_result,
                "processed_modules": vision_result.get("processed_modules", [])
            }
            
            # 提取关键信息
            if vision_result.get("success", False):
                # 尝试提取文本（如果有OCR功能）
                extracted_text = self._extract_text_from_vision_result(vision_result)
                if extracted_text:
                    result["extracted_text"] = extracted_text
                
                # 检测用户意图
                user_intent = self._detect_user_intent_from_vision(vision_result)
                if user_intent:
                    result["detected_intent"] = user_intent
            
            return result
            
        except Exception as e:
            logger.error(f"视觉输入处理失败: {e}")
            return self._create_error_result(f"视觉处理失败: {e}")
    
    async def _process_text_input(self, text_data: Any, **kwargs) -> Dict[str, Any]:
        """处理文本输入"""
        if not self.text_system or not self.config.text_enabled:
            return self._create_error_result("文本输入系统不可用")
        
        try:
            source = kwargs.get("source", "direct")
            
            # 如果输入是笔画数据（手写）
            if isinstance(text_data, list) and all(isinstance(item, dict) for item in text_data):
                # 假设是手写笔画数据
                if hasattr(self.text_system, 'process_handwriting_strokes'):
                    result = self.text_system.process_handwriting_strokes(text_data)
                    
                    return {
                        "success": result is not None,
                        "type": "handwriting_recognition",
                        "text": result.text if result else "",
                        "confidence": result.confidence if result else 0.0,
                        "source": "handwriting"
                    }
            
            # 如果输入是文本
            if isinstance(text_data, str):
                # 处理文本输入
                text_result = process_text_input(text_data, source)
                
                return {
                    "success": text_result.get("success", False),
                    "type": "text_processing",
                    "original_text": text_data,
                    "processed_text": text_result.get("processed_text", text_data),
                    "source": source
                }
            
            return self._create_error_result("不支持的文本输入格式")
            
        except Exception as e:
            logger.error(f"文本输入处理失败: {e}")
            return self._create_error_result(f"文本处理失败: {e}")
    
    async def _process_multimodal_input(self, input_data: Any, input_type: str, **kwargs) -> Dict[str, Any]:
        """处理多模态输入"""
        results = {}
        
        # 根据输入类型确定主要处理方式
        if input_type == "audio":
            # 语音为主，视觉为辅
            speech_result = await self._process_speech_input(input_data, **kwargs)
            results["speech"] = speech_result
            
            # 如果语音识别成功，可以结合其他模态
            if speech_result.get("success", False) and kwargs.get("use_vision_context", False):
                # 这里可以添加从视觉获取上下文信息的逻辑
                pass
            
        elif input_type == "image":
            # 视觉为主，文本为辅
            vision_result = await self._process_vision_input(input_data, **kwargs)
            results["vision"] = vision_result
            
            # 如果提取到了文本，可以进一步处理
            if vision_result.get("extracted_text"):
                text_result = await self._process_text_input(vision_result["extracted_text"], **kwargs)
                results["text"] = text_result
            
        elif input_type == "text":
            # 文本为主，其他为辅
            text_result = await self._process_text_input(input_data, **kwargs)
            results["text"] = text_result
            
        else:
            return self._create_error_result(f"不支持的输入类型: {input_type}")
        
        # 整合结果
        combined_result = self._combine_multimodal_results(results)
        
        return {
            "success": combined_result.get("success", False),
            "type": "multimodal_processing",
            "results": results,
            "combined_result": combined_result,
            "primary_modality": input_type
        }
    
    async def _process_automatic_input(self, input_data: Any, input_type: str, **kwargs) -> Dict[str, Any]:
        """自动处理输入（智能选择最佳模式）"""
        # 根据输入类型和内容智能选择处理模式
        if input_type == "audio":
            # 对于音频，首先尝试语音识别
            result = await self._process_speech_input(input_data, **kwargs)
            
            # 如果语音识别置信度低，尝试其他模式
            if (result.get("success", False) and 
                result.get("confidence", 0) < self.config.mode_switch_threshold):
                # 可以尝试结合其他模态或切换到文本输入
                result["suggested_fallback"] = "text_input"
            
            return result
            
        elif input_type == "image":
            # 对于图像，使用视觉分析
            return await self._process_vision_input(input_data, **kwargs)
            
        elif input_type == "text":
            # 对于文本，直接处理
            return await self._process_text_input(input_data, **kwargs)
            
        else:
            # 未知类型，尝试多模态处理
            return await self._process_multimodal_input(input_data, input_type, **kwargs)
    
    def _extract_text_from_vision_result(self, vision_result: Dict[str, Any]) -> Optional[str]:
        """从视觉分析结果中提取文本"""
        # 这里可以实现OCR文本提取逻辑
        # 目前返回空字符串，实际项目中应该集成OCR功能
        return ""
    
    def _detect_user_intent_from_vision(self, vision_result: Dict[str, Any]) -> Optional[str]:
        """从视觉分析结果中检测用户意图"""
        # 这里可以实现意图检测逻辑
        # 例如：根据手势、表情等推断用户意图
        return None
    
    def _combine_multimodal_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """整合多模态结果"""
        combined = {
            "success": False,
            "confidence": 0.0,
            "primary_text": "",
            "supporting_evidence": []
        }
        
        # 简单的整合逻辑：选择置信度最高的结果
        best_result = None
        best_confidence = 0.0
        
        for modality, result in results.items():
            if result.get("success", False):
                confidence = result.get("confidence", 0.0)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_result = result
        
        if best_result:
            combined["success"] = True
            combined["confidence"] = best_confidence
            combined["primary_text"] = best_result.get("text", "")
            
            # 收集支持证据
            for modality, result in results.items():
                if modality != "primary" and result.get("success", False):
                    combined["supporting_evidence"].append({
                        "modality": modality,
                        "confidence": result.get("confidence", 0.0),
                        "info": result.get("type", "")
                    })
        
        return combined
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "success": False,
            "error": error_message,
            "timestamp": time.time()
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        subsystems_status = {}
        
        # 语音识别系统状态
        if self.speech_system and self.config.speech_enabled:
            subsystems_status["speech"] = get_speech_recognition_status()
        
        # 计算机视觉系统状态
        if self.vision_system and self.config.vision_enabled:
            subsystems_status["vision"] = get_vision_system_status()
        
        # 文本输入系统状态
        if self.text_system and self.config.text_enabled:
            subsystems_status["text"] = self.text_system.get_status()
        
        # 计算平均处理时间
        avg_speech_time = 0
        avg_vision_time = 0
        avg_text_time = 0
        
        if self.performance_stats["speech_processing_time"]:
            avg_speech_time = sum(self.performance_stats["speech_processing_time"]) / len(self.performance_stats["speech_processing_time"])
        
        if self.performance_stats["vision_processing_time"]:
            avg_vision_time = sum(self.performance_stats["vision_processing_time"]) / len(self.performance_stats["vision_processing_time"])
        
        if self.performance_stats["text_processing_time"]:
            avg_text_time = sum(self.performance_stats["text_processing_time"]) / len(self.performance_stats["text_processing_time"])
        
        return {
            "initialized": self.is_initialized,
            "active": self.is_active,
            "current_mode": self.current_mode.value,
            "config": self.config.to_dict(),
            "subsystems": subsystems_status,
            "current_session": self.current_session_id,
            "sessions_count": len(self.input_sessions),
            "performance": {
                "total_inputs": self.performance_stats["total_inputs"],
                "successful_inputs": self.performance_stats["successful_inputs"],
                "failed_inputs": self.performance_stats["failed_inputs"],
                "success_rate": (self.performance_stats["successful_inputs"] / max(self.performance_stats["total_inputs"], 1)) * 100,
                "avg_speech_processing_time": avg_speech_time,
                "avg_vision_processing_time": avg_vision_time,
                "avg_text_processing_time": avg_text_time
            }
        }
    
    def register_callback(self, callback_type: str, callback_func: Callable) -> None:
        """
        注册回调函数
        
        Args:
            callback_type: 回调类型 ('input_processed', 'mode_changed', 'error')
            callback_func: 回调函数
        """
        self.input_callbacks.append((callback_type, callback_func))
        logger.debug(f"注册了 {callback_type} 回调函数")
    
    def unregister_callback(self, callback_type: str, callback_func: Callable) -> None:
        """
        注销回调函数
        
        Args:
            callback_type: 回调类型
            callback_func: 回调函数
        """
        callback_pair = (callback_type, callback_func)
        if callback_pair in self.input_callbacks:
            self.input_callbacks.remove(callback_pair)
            logger.debug(f"注销了 {callback_type} 回调函数")
    
    async def shutdown(self) -> None:
        """关闭输入系统"""
        logger.info("正在关闭输入系统...")
        
        # 停用系统
        await self.deactivate()
        
        # 结束所有会话
        for session_id in list(self.input_sessions.keys()):
            if not self.input_sessions[session_id].get("end_time"):
                self.input_sessions[session_id]["end_time"] = time.time()
        
        # 清理资源
        self.is_initialized = False
        self.input_callbacks.clear()
        self.error_handlers.clear()
        
        logger.info("输入系统已关闭")


# 全局输入系统管理器实例
_input_system_manager_instance = None
_input_system_manager_lock = threading.Lock()


def get_input_system_manager(config: Optional[Dict[str, Any]] = None) -> InputSystemManager:
    """
    获取输入系统管理器单例实例
    
    Args:
        config: 配置字典
        
    Returns:
        InputSystemManager: 输入系统管理器实例
    """
    global _input_system_manager_instance
    
    with _input_system_manager_lock:
        if _input_system_manager_instance is None:
            _input_system_manager_instance = InputSystemManager(config)
        
        return _input_system_manager_instance


async def initialize_input_systems(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    初始化输入系统
    
    Args:
        config: 配置字典
        
    Returns:
        bool: 是否初始化成功
    """
    manager = get_input_system_manager(config)
    return await manager.initialize()


async def activate_input_systems() -> bool:
    """
    激活输入系统
    
    Returns:
        bool: 是否激活成功
    """
    manager = get_input_system_manager()
    return await manager.activate()


async def deactivate_input_systems() -> None:
    """
    停用输入系统
    """
    manager = get_input_system_manager()
    await manager.deactivate()


async def process_input(input_data: Any, input_type: str, **kwargs) -> Dict[str, Any]:
    """
    处理输入数据（便捷函数）
    
    Args:
        input_data: 输入数据
        input_type: 输入类型 ('audio', 'image', 'text', 'strokes')
        **kwargs: 额外参数
        
    Returns:
        Dict[str, Any]: 处理结果
    """
    manager = get_input_system_manager()
    return await manager.process_input(input_data, input_type, **kwargs)


def get_input_system_status() -> Dict[str, Any]:
    """
    获取输入系统状态（便捷函数）
    
    Returns:
        Dict[str, Any]: 系统状态
    """
    manager = get_input_system_manager()
    return manager.get_system_status()


def set_input_mode(mode: Union[InputMode, str]) -> bool:
    """
    设置输入模式（便捷函数）
    
    Args:
        mode: 输入模式
        
    Returns:
        bool: 是否设置成功
    """
    manager = get_input_system_manager()
    return manager.set_input_mode(mode)


async def shutdown_input_systems() -> None:
    """
    关闭输入系统（便捷函数）
    """
    manager = get_input_system_manager()
    await manager.shutdown()


# 导出主要类和方法
__all__ = [
    # 主管理器类
    "InputSystemManager",
    "InputSystemConfig",
    "InputMode",
    
    # 便捷函数
    "get_input_system_manager",
    "initialize_input_systems",
    "activate_input_systems",
    "deactivate_input_systems",
    "process_input",
    "get_input_system_status",
    "set_input_mode",
    "shutdown_input_systems",
    
    # 子系统可用性标志
    "SPEECH_RECOGNITION_AVAILABLE",
    "COMPUTER_VISION_AVAILABLE",
    "TEXT_INPUT_AVAILABLE",
    
    # 从子系统导入的主要类和函数
    # 语音识别
    "SpeechRecognitionManager",
    "speech_recognition_manager",
    "initialize_speech_recognition",
    "get_speech_recognition_status",
    "transcribe_audio",
    "detect_wake_word",
    "authenticate_user",
    
    # 计算机视觉
    "ComputerVisionSystem",
    "computer_vision_system",
    "get_computer_vision_system",
    "initialize_computer_vision",
    "process_image",
    "get_vision_system_status",
    
    # 文本输入
    "TextInputSystem",
    "TextInputConfig",
    "get_text_input_system",
    "initialize_text_input_system",
    "process_text_input",
    "get_text_input_status"
]


# 版本信息
__version__ = "1.0.0"
__author__ = "Mirexs AI Team"
__description__ = "Mirexs输入系统 - 集成语音识别、计算机视觉和文本输入"


# 包初始化时执行的代码
def _initialize_package():
    """包初始化函数"""
    logger.info(f"初始化 Mirexs 输入系统 v{__version__}")
    logger.info(f"描述: {__description__}")
    
    # 检查子系统可用性
    availability = {
        "语音识别": "可用" if SPEECH_RECOGNITION_AVAILABLE else "不可用",
        "计算机视觉": "可用" if COMPUTER_VISION_AVAILABLE else "不可用",
        "文本输入": "可用" if TEXT_INPUT_AVAILABLE else "不可用"
    }
    
    logger.info(f"子系统可用性: {availability}")


# 执行包初始化
_initialize_package()
