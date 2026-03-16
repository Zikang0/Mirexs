"""
文本输入系统包初始化模块
整合所有文本输入子系统，提供统一的接口和管理功能
"""

import threading
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from infrastructure.communication.message_bus import MessageBus
from config.system import ConfigManager
from utils.common_utilities import file_utils, validation_utils
from utils.system_utilities import performance_utils, logging_utils

from .keyboard_handler import KeyboardHandler, KeyEvent, KeyEventType
from .handwriting_recog import HandwritingRecognizer, Stroke, StrokePoint, RecognitionResult
from .voice_typing import VoiceTyping, VoiceTypingResult
from .predictive_text import PredictiveText, PredictionCandidate
from .auto_correction import AutoCorrection, CorrectionCandidate
from .input_method import InputMethodManager, InputMethod, InputMethodEngine, Candidate
from .shortcut_manager import ShortcutManager, Shortcut
from .input_metrics import InputMetricsCollector, InputMetrics, InputSession

logger = logging.getLogger(__name__)


@dataclass
class TextInputConfig:
    """文本输入系统配置"""
    keyboard_enabled: bool = True
    handwriting_enabled: bool = True
    voice_typing_enabled: bool = True
    predictive_text_enabled: bool = True
    auto_correction_enabled: bool = True
    input_method_enabled: bool = True
    shortcuts_enabled: bool = True
    metrics_enabled: bool = True
    
    # 性能配置
    realtime_processing: bool = True
    batch_processing: bool = False
    max_concurrent_operations: int = 10
    
    # 语言配置
    default_language: str = "zh-CN"
    supported_languages: List[str] = field(default_factory=lambda: ["zh-CN", "en-US"])
    
    # 存储配置
    save_user_data: bool = True
    auto_save_interval: int = 300  # 秒
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "keyboard_enabled": self.keyboard_enabled,
            "handwriting_enabled": self.handwriting_enabled,
            "voice_typing_enabled": self.voice_typing_enabled,
            "predictive_text_enabled": self.predictive_text_enabled,
            "auto_correction_enabled": self.auto_correction_enabled,
            "input_method_enabled": self.input_method_enabled,
            "shortcuts_enabled": self.shortcuts_enabled,
            "metrics_enabled": self.metrics_enabled,
            "realtime_processing": self.realtime_processing,
            "batch_processing": self.batch_processing,
            "max_concurrent_operations": self.max_concurrent_operations,
            "default_language": self.default_language,
            "supported_languages": self.supported_languages,
            "save_user_data": self.save_user_data,
            "auto_save_interval": self.auto_save_interval
        }


class TextInputSystem:
    """文本输入系统管理器 - 整合所有文本输入子系统"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化文本输入系统
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.message_bus = MessageBus()
        
        # 配置
        self.config = TextInputConfig()
        
        # 子系统实例
        self.keyboard_handler = None
        self.handwriting_recognizer = None
        self.voice_typing = None
        self.predictive_text = None
        self.auto_correction = None
        self.input_method_manager = None
        self.shortcut_manager = None
        self.metrics_collector = None
        
        # 状态管理
        self.is_initialized = False
        self.is_active = False
        self.current_language = "zh-CN"
        
        # 线程安全
        self.lock = threading.RLock()
        
        # 回调注册
        self.text_input_callbacks = []  # (callback_type, callback_func)
        self.error_handlers = []
        
        # 会话管理
        self.input_sessions = {}
        self.current_session_id = None
        
        # 初始化日志
        self._init_logging()
        
        logger.info("TextInputSystem initialized (not activated)")
    
    def _init_logging(self) -> None:
        """初始化日志系统"""
        log_config = {
            "name": "text_input_system",
            "level": logging.INFO,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file_path": "logs/text_input_system.log"
        }
        logging_utils.setup_logger(log_config)
    
    def initialize(self) -> bool:
        """
        初始化文本输入系统
        
        Returns:
            bool: 是否初始化成功
        """
        if self.is_initialized:
            logger.warning("Text input system already initialized")
            return True
        
        try:
            with self.lock:
                # 1. 加载配置
                self._load_config()
                
                # 2. 初始化子系统
                subsystems_initialized = []
                
                # 键盘处理子系统
                if self.config.keyboard_enabled:
                    if self._init_keyboard_handler():
                        subsystems_initialized.append("keyboard")
                
                # 手写识别子系统
                if self.config.handwriting_enabled:
                    if self._init_handwriting_recognizer():
                        subsystems_initialized.append("handwriting")
                
                # 语音打字子系统
                if self.config.voice_typing_enabled:
                    if self._init_voice_typing():
                        subsystems_initialized.append("voice_typing")
                
                # 预测文本子系统
                if self.config.predictive_text_enabled:
                    if self._init_predictive_text():
                        subsystems_initialized.append("predictive_text")
                
                # 自动校正子系统
                if self.config.auto_correction_enabled:
                    if self._init_auto_correction():
                        subsystems_initialized.append("auto_correction")
                
                # 输入法子系统
                if self.config.input_method_enabled:
                    if self._init_input_method_manager():
                        subsystems_initialized.append("input_method")
                
                # 快捷键管理子系统
                if self.config.shortcuts_enabled and self.keyboard_handler:
                    if self._init_shortcut_manager():
                        subsystems_initialized.append("shortcuts")
                
                # 指标收集子系统
                if self.config.metrics_enabled:
                    if self._init_metrics_collector():
                        subsystems_initialized.append("metrics")
                
                # 3. 注册消息处理器
                self._register_message_handlers()
                
                # 4. 设置默认语言
                self.current_language = self.config.default_language
                
                # 5. 标记为已初始化
                self.is_initialized = True
                
                logger.info(f"Text input system initialized with subsystems: {subsystems_initialized}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize text input system: {e}")
            return False
    
    def _load_config(self) -> None:
        """加载配置"""
        try:
            config_data = self.config_manager.get_config("text_input_config")
            
            # 更新配置对象
            if config_data:
                for key, value in config_data.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
            
            logger.debug("Text input config loaded")
        except Exception as e:
            logger.error(f"Failed to load text input config: {e}")
    
    def _init_keyboard_handler(self) -> bool:
        """初始化键盘处理子系统"""
        try:
            self.keyboard_handler = KeyboardHandler(self.config_manager)
            
            # 注册键盘事件回调
            self.keyboard_handler.register_key_handler(self._handle_keyboard_input)
            
            logger.info("Keyboard handler initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize keyboard handler: {e}")
            return False
    
    def _init_handwriting_recognizer(self) -> bool:
        """初始化手写识别子系统"""
        try:
            self.handwriting_recognizer = HandwritingRecognizer(self.config_manager)
            logger.info("Handwriting recognizer initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize handwriting recognizer: {e}")
            return False
    
    def _init_voice_typing(self) -> bool:
        """初始化语音打字子系统"""
        try:
            self.voice_typing = VoiceTyping(self.config_manager)
            
            # 注册语音打字结果回调
            self.voice_typing.register_result_callback(self._handle_voice_typing_result)
            
            logger.info("Voice typing initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize voice typing: {e}")
            return False
    
    def _init_predictive_text(self) -> bool:
        """初始化预测文本子系统"""
        try:
            self.predictive_text = PredictiveText(self.config_manager)
            logger.info("Predictive text initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize predictive text: {e}")
            return False
    
    def _init_auto_correction(self) -> bool:
        """初始化自动校正子系统"""
        try:
            self.auto_correction = AutoCorrection(self.config_manager)
            logger.info("Auto correction initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize auto correction: {e}")
            return False
    
    def _init_input_method_manager(self) -> bool:
        """初始化输入法管理子系统"""
        try:
            self.input_method_manager = InputMethodManager(self.config_manager)
            
            # 加载用户数据
            self.input_method_manager.load_user_data()
            
            logger.info("Input method manager initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize input method manager: {e}")
            return False
    
    def _init_shortcut_manager(self) -> bool:
        """初始化快捷键管理子系统"""
        try:
            if not self.keyboard_handler:
                logger.error("Keyboard handler required for shortcut manager")
                return False
            
            self.shortcut_manager = ShortcutManager(self.config_manager, self.keyboard_handler)
            logger.info("Shortcut manager initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize shortcut manager: {e}")
            return False
    
    def _init_metrics_collector(self) -> bool:
        """初始化指标收集子系统"""
        try:
            self.metrics_collector = InputMetricsCollector(self.config_manager)
            logger.info("Metrics collector initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize metrics collector: {e}")
            return False
    
    def _register_message_handlers(self) -> None:
        """注册消息处理器"""
        # 注册文本输入相关消息
        self.message_bus.subscribe("text_input_command", self._handle_command_message)
        self.message_bus.subscribe("text_input_config_update", self._handle_config_update)
        self.message_bus.subscribe("text_input_language_change", self._handle_language_change)
        
        # 注册错误处理
        self.message_bus.subscribe("text_input_error", self._handle_error_message)
    
    def activate(self) -> bool:
        """
        激活文本输入系统
        
        Returns:
            bool: 是否激活成功
        """
        if not self.is_initialized:
            if not self.initialize():
                return False
        
        if self.is_active:
            logger.warning("Text input system already active")
            return True
        
        try:
            with self.lock:
                # 启动子系统
                subsystems_activated = []
                
                # 启动键盘监听
                if self.keyboard_handler and self.config.keyboard_enabled:
                    if self.keyboard_handler.start_listening():
                        subsystems_activated.append("keyboard")
                
                # 启动手写识别
                if self.handwriting_recognizer and self.config.handwriting_enabled:
                    if self.handwriting_recognizer.start_recognition():
                        subsystems_activated.append("handwriting")
                
                # 启动语音打字
                if self.voice_typing and self.config.voice_typing_enabled:
                    if self.voice_typing.start_listening():
                        subsystems_activated.append("voice_typing")
                
                # 启动预测文本（不需要显式启动）
                if self.predictive_text and self.config.predictive_text_enabled:
                    subsystems_activated.append("predictive_text")
                
                # 启动自动校正（不需要显式启动）
                if self.auto_correction and self.config.auto_correction_enabled:
                    subsystems_activated.append("auto_correction")
                
                # 启动输入法管理（不需要显式启动）
                if self.input_method_manager and self.config.input_method_enabled:
                    subsystems_activated.append("input_method")
                
                # 启动快捷键管理（不需要显式启动）
                if self.shortcut_manager and self.config.shortcuts_enabled:
                    subsystems_activated.append("shortcuts")
                
                # 启动指标收集
                if self.metrics_collector and self.config.metrics_enabled:
                    if self.metrics_collector.start_collection():
                        subsystems_activated.append("metrics")
                
                # 开始新的输入会话
                self._start_new_session()
                
                self.is_active = True
                
                # 发布系统激活事件
                self.message_bus.publish("text_input_system_activated", {
                    "timestamp": time.time(),
                    "subsystems": subsystems_activated,
                    "language": self.current_language
                })
                
                logger.info(f"Text input system activated with subsystems: {subsystems_activated}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to activate text input system: {e}")
            return False
    
    def deactivate(self) -> None:
        """停用文本输入系统"""
        if not self.is_active:
            return
        
        try:
            with self.lock:
                # 停止子系统
                if self.keyboard_handler:
                    self.keyboard_handler.stop_listening()
                
                if self.handwriting_recognizer:
                    self.handwriting_recognizer.stop_recognition()
                
                if self.voice_typing:
                    self.voice_typing.stop_listening()
                
                if self.metrics_collector:
                    self.metrics_collector.stop_collection()
                
                # 结束当前会话
                self._end_current_session()
                
                # 保存用户数据
                self._save_user_data()
                
                self.is_active = False
                
                # 发布系统停用事件
                self.message_bus.publish("text_input_system_deactivated", {
                    "timestamp": time.time()
                })
                
                logger.info("Text input system deactivated")
                
        except Exception as e:
            logger.error(f"Error during deactivation: {e}")
    
    def _start_new_session(self) -> str:
        """开始新的输入会话"""
        if self.metrics_collector:
            session_id = self.metrics_collector.start_new_session()
            self.current_session_id = session_id
            
            # 记录会话开始
            self.input_sessions[session_id] = {
                "start_time": time.time(),
                "subsystems_used": [],
                "input_count": 0
            }
            
            return session_id
        return ""
    
    def _end_current_session(self) -> Optional[str]:
        """结束当前输入会话"""
        if self.metrics_collector and self.current_session_id:
            session_id = self.metrics_collector.end_current_session()
            
            if session_id and session_id in self.input_sessions:
                self.input_sessions[session_id]["end_time"] = time.time()
            
            self.current_session_id = None
            return session_id
        return None
    
    def _save_user_data(self) -> None:
        """保存用户数据"""
        if not self.config.save_user_data:
            return
        
        try:
            # 保存输入法用户数据
            if self.input_method_manager:
                self.input_method_manager.save_user_data()
            
            # 保存预测文本数据
            if self.predictive_text:
                self.predictive_text.save_models()
            
            # 保存快捷键数据
            if self.shortcut_manager:
                self.shortcut_manager.save_user_shortcuts()
            
            logger.debug("User data saved")
            
        except Exception as e:
            logger.error(f"Failed to save user data: {e}")
    
    def _handle_keyboard_input(self, key_event: KeyEvent) -> None:
        """
        处理键盘输入
        
        Args:
            key_event: 键盘事件
        """
        try:
            # 更新会话统计
            if self.current_session_id:
                session = self.input_sessions.get(self.current_session_id)
                if session:
                    session["input_count"] += 1
                    if "keyboard" not in session["subsystems_used"]:
                        session["subsystems_used"].append("keyboard")
            
            # 如果是普通按键，传递给输入法处理
            if (key_event.event_type == KeyEventType.KEY_DOWN and 
                not key_event.modifiers and 
                len(key_event.key_name) == 1 and 
                key_event.key_name.isprintable()):
                
                if self.input_method_manager:
                    candidates = self.input_method_manager.process_key(key_event.key_name)
                    if candidates:
                        # 发布候选词更新
                        self.message_bus.publish("input_method_candidates", {
                            "candidates": candidates,
                            "source": "keyboard",
                            "timestamp": time.time()
                        })
            
            # 调用注册的回调函数
            for callback_type, callback_func in self.text_input_callbacks:
                if callback_type == "keyboard":
                    try:
                        callback_func(key_event)
                    except Exception as e:
                        logger.error(f"Error in keyboard callback: {e}")
            
        except Exception as e:
            logger.error(f"Error handling keyboard input: {e}")
            self._handle_error(e, "keyboard_input")
    
    def _handle_voice_typing_result(self, result: VoiceTypingResult, processed_text: str) -> None:
        """
        处理语音打字结果
        
        Args:
            result: 语音识别结果
            processed_text: 处理后的文本
        """
        try:
            # 更新会话统计
            if self.current_session_id:
                session = self.input_sessions.get(self.current_session_id)
                if session:
                    session["input_count"] += 1
                    if "voice_typing" not in session["subsystems_used"]:
                        session["subsystems_used"].append("voice_typing")
            
            # 处理文本（自动校正、预测等）
            final_text = self._process_text(processed_text)
            
            # 发布最终文本
            self.message_bus.publish("text_input_final", {
                "text": final_text,
                "source": "voice_typing",
                "confidence": result.confidence,
                "language": result.language,
                "timestamp": time.time()
            })
            
            # 调用注册的回调函数
            for callback_type, callback_func in self.text_input_callbacks:
                if callback_type == "voice":
                    try:
                        callback_func(final_text, result)
                    except Exception as e:
                        logger.error(f"Error in voice callback: {e}")
            
        except Exception as e:
            logger.error(f"Error handling voice typing result: {e}")
            self._handle_error(e, "voice_typing")
    
    def _process_text(self, text: str) -> str:
        """
        处理文本（应用校正、预测等）
        
        Args:
            text: 原始文本
            
        Returns:
            str: 处理后的文本
        """
        processed_text = text
        
        # 应用自动校正
        if self.auto_correction and self.config.auto_correction_enabled:
            corrections = self.auto_correction.check_text(processed_text)
            for correction in corrections[:3]:  # 应用前3个校正
                if correction.confidence > 0.8:
                    processed_text = self.auto_correction.apply_correction(processed_text, correction)
        
        # 应用预测文本（如果需要）
        if self.predictive_text and self.config.predictive_text_enabled:
            # 学习这个文本
            self.predictive_text.learn_from_input(processed_text)
        
        return processed_text
    
    def _handle_command_message(self, message: Dict[str, Any]) -> None:
        """处理命令消息"""
        command = message.get("command")
        
        if command == "activate":
            self.activate()
        elif command == "deactivate":
            self.deactivate()
        elif command == "toggle":
            if self.is_active:
                self.deactivate()
            else:
                self.activate()
        elif command == "set_language":
            language = message.get("language")
            self.set_language(language)
        elif command == "start_voice_typing":
            if self.voice_typing:
                self.voice_typing.start_listening()
        elif command == "stop_voice_typing":
            if self.voice_typing:
                self.voice_typing.stop_listening()
        elif command == "start_handwriting":
            if self.handwriting_recognizer:
                self.handwriting_recognizer.start_recognition()
        elif command == "stop_handwriting":
            if self.handwriting_recognizer:
                self.handwriting_recognizer.stop_recognition()
        elif command == "save_data":
            self._save_user_data()
        elif command == "reset":
            self.reset()
        elif command == "get_status":
            self._send_status()
    
    def _handle_config_update(self, message: Dict[str, Any]) -> None:
        """处理配置更新"""
        config_updates = message.get("config", {})
        
        if config_updates:
            # 更新配置
            for key, value in config_updates.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            # 重新配置子系统
            self._reconfigure_subsystems(config_updates)
            
            logger.info(f"Configuration updated: {list(config_updates.keys())}")
    
    def _reconfigure_subsystems(self, config_updates: Dict[str, Any]) -> None:
        """重新配置子系统"""
        # 这里可以实现根据配置变化动态调整子系统的逻辑
        # 例如：启用/禁用某些子系统、调整参数等
        
        # 示例：如果语言配置变化，更新所有子系统
        if "default_language" in config_updates:
            new_language = config_updates["default_language"]
            self.set_language(new_language)
    
    def _handle_language_change(self, message: Dict[str, Any]) -> None:
        """处理语言变更"""
        language = message.get("language")
        if language:
            self.set_language(language)
    
    def _handle_error_message(self, message: Dict[str, Any]) -> None:
        """处理错误消息"""
        error = message.get("error")
        source = message.get("source", "unknown")
        
        logger.error(f"Error from {source}: {error}")
        
        # 调用错误处理器
        for handler in self.error_handlers:
            try:
                handler(error, source)
            except Exception as e:
                logger.error(f"Error in error handler: {e}")
    
    def _handle_error(self, error: Exception, source: str) -> None:
        """处理错误"""
        error_info = {
            "error": str(error),
            "source": source,
            "timestamp": time.time(),
            "system_active": self.is_active,
            "session_id": self.current_session_id
        }
        
        # 发布错误事件
        self.message_bus.publish("text_input_error", error_info)
        
        # 调用错误处理器
        for handler in self.error_handlers:
            try:
                handler(error, source)
            except Exception as e:
                logger.error(f"Error in error handler: {e}")
    
    def _send_status(self) -> None:
        """发送系统状态"""
        status = self.get_status()
        
        self.message_bus.publish("text_input_status", {
            "status": status,
            "timestamp": time.time()
        })
    
    def set_language(self, language: str) -> bool:
        """
        设置当前语言
        
        Args:
            language: 语言代码
            
        Returns:
            bool: 是否设置成功
        """
        if language not in self.config.supported_languages:
            logger.error(f"Unsupported language: {language}")
            return False
        
        try:
            self.current_language = language
            
            # 更新所有支持语言的子系统
            subsystems_updated = []
            
            if self.handwriting_recognizer:
                if self.handwriting_recognizer.set_language(language):
                    subsystems_updated.append("handwriting")
            
            if self.voice_typing:
                if self.voice_typing.set_language(language):
                    subsystems_updated.append("voice_typing")
            
            if self.predictive_text:
                if self.predictive_text.set_language(language):
                    subsystems_updated.append("predictive_text")
            
            if self.auto_correction:
                # AutoCorrection需要重新加载模型
                subsystems_updated.append("auto_correction")
            
            if self.input_method_manager:
                # 输入法管理器可以根据语言自动切换
                subsystems_updated.append("input_method")
            
            logger.info(f"Language set to {language}, updated subsystems: {subsystems_updated}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set language: {e}")
            return False
    
    def register_callback(self, callback_type: str, callback_func: Callable) -> None:
        """
        注册回调函数
        
        Args:
            callback_type: 回调类型（keyboard, voice, handwriting, text, error）
            callback_func: 回调函数
        """
        valid_types = ["keyboard", "voice", "handwriting", "text", "error"]
        
        if callback_type not in valid_types:
            logger.error(f"Invalid callback type: {callback_type}")
            return
        
        if callback_type == "error":
            self.error_handlers.append(callback_func)
        else:
            self.text_input_callbacks.append((callback_type, callback_func))
        
        logger.debug(f"Registered {callback_type} callback")
    
    def unregister_callback(self, callback_type: str, callback_func: Callable) -> None:
        """
        注销回调函数
        
        Args:
            callback_type: 回调类型
            callback_func: 回调函数
        """
        if callback_type == "error":
            if callback_func in self.error_handlers:
                self.error_handlers.remove(callback_func)
        else:
            callback_pair = (callback_type, callback_func)
            if callback_pair in self.text_input_callbacks:
                self.text_input_callbacks.remove(callback_pair)
        
        logger.debug(f"Unregistered {callback_type} callback")
    
    def process_handwriting_strokes(self, strokes: List[Dict[str, Any]]) -> Optional[RecognitionResult]:
        """
        处理手写笔画
        
        Args:
            strokes: 笔画数据列表
            
        Returns:
            RecognitionResult: 识别结果
        """
        if not self.handwriting_recognizer or not self.config.handwriting_enabled:
            return None
        
        try:
            # 转换为Stroke对象
            stroke_objects = []
            for stroke_data in strokes:
                stroke = Stroke()
                for point_data in stroke_data.get("points", []):
                    point = StrokePoint(
                        x=point_data.get("x", 0),
                        y=point_data.get("y", 0),
                        pressure=point_data.get("pressure", 1.0),
                        timestamp=point_data.get("timestamp", time.time()),
                        is_end=point_data.get("is_end", False)
                    )
                    stroke.add_point(point)
                stroke_objects.append(stroke)
            
            # 执行识别
            result = self.handwriting_recognizer.recognize_strokes(stroke_objects)
            
            if result:
                # 更新会话统计
                if self.current_session_id:
                    session = self.input_sessions.get(self.current_session_id)
                    if session:
                        session["input_count"] += 1
                        if "handwriting" not in session["subsystems_used"]:
                            session["subsystems_used"].append("handwriting")
                
                # 发布识别结果
                self.message_bus.publish("handwriting_recognition_result", {
                    "result": result.to_dict(),
                    "timestamp": time.time()
                })
                
                # 处理文本
                processed_text = self._process_text(result.text)
                
                # 调用回调函数
                for callback_type, callback_func in self.text_input_callbacks:
                    if callback_type == "handwriting":
                        try:
                            callback_func(result, processed_text)
                        except Exception as e:
                            logger.error(f"Error in handwriting callback: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing handwriting strokes: {e}")
            self._handle_error(e, "handwriting")
            return None
    
    def predict_text(self, context: str, cursor_position: int = -1) -> List[Dict[str, Any]]:
        """
        预测文本
        
        Args:
            context: 上下文文本
            cursor_position: 光标位置
            
        Returns:
            List[Dict[str, Any]]: 预测结果列表
        """
        if not self.predictive_text or not self.config.predictive_text_enabled:
            return []
        
        try:
            predictions = self.predictive_text.predict(context, cursor_position)
            
            # 发布预测结果
            if predictions:
                self.message_bus.publish("predictive_text_result", {
                    "predictions": predictions,
                    "context": context,
                    "timestamp": time.time()
                })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting text: {e}")
            return []
    
    def check_text_corrections(self, text: str) -> List[Dict[str, Any]]:
        """
        检查文本校正
        
        Args:
            text: 要检查的文本
            
        Returns:
            List[Dict[str, Any]]: 校正建议列表
        """
        if not self.auto_correction or not self.config.auto_correction_enabled:
            return []
        
        try:
            corrections = self.auto_correction.check_text(text)
            
            # 发布校正结果
            if corrections:
                self.message_bus.publish("auto_correction_result", {
                    "corrections": [c.to_dict() for c in corrections],
                    "text": text,
                    "timestamp": time.time()
                })
            
            return [c.to_dict() for c in corrections]
            
        except Exception as e:
            logger.error(f"Error checking text corrections: {e}")
            return []
    
    def switch_input_method(self, ime_id: str) -> bool:
        """
        切换输入法
        
        Args:
            ime_id: 输入法ID
            
        Returns:
            bool: 是否切换成功
        """
        if not self.input_method_manager or not self.config.input_method_enabled:
            return False
        
        try:
            return self.input_method_manager.switch_ime(ime_id)
        except Exception as e:
            logger.error(f"Error switching input method: {e}")
            return False
    
    def register_shortcut(self, shortcut_definition: Dict[str, Any]) -> bool:
        """
        注册快捷键
        
        Args:
            shortcut_definition: 快捷键定义
            
        Returns:
            bool: 是否注册成功
        """
        if not self.shortcut_manager or not self.config.shortcuts_enabled:
            return False
        
        try:
            shortcut = Shortcut(**shortcut_definition)
            return self.shortcut_manager.register_shortcut(shortcut)
        except Exception as e:
            logger.error(f"Error registering shortcut: {e}")
            return False
    
    def reset(self) -> None:
        """重置文本输入系统"""
        logger.info("Resetting text input system...")
        
        with self.lock:
            # 停用系统
            self.deactivate()
            
            # 重置子系统
            if self.keyboard_handler:
                # 键盘处理器的重置逻辑
                pass
            
            if self.handwriting_recognizer:
                self.handwriting_recognizer.clear_strokes()
            
            if self.predictive_text:
                # 预测文本可以清理缓存
                pass
            
            if self.auto_correction:
                # 自动校正可以清理缓存
                pass
            
            # 清空会话
            self.input_sessions.clear()
            self.current_session_id = None
            
            # 清空回调
            self.text_input_callbacks.clear()
            self.error_handlers.clear()
            
            logger.info("Text input system reset")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        subsystems_status = {}
        
        if self.keyboard_handler:
            subsystems_status["keyboard"] = self.keyboard_handler.get_statistics()
        
        if self.handwriting_recognizer:
            subsystems_status["handwriting"] = self.handwriting_recognizer.get_statistics()
        
        if self.voice_typing:
            subsystems_status["voice_typing"] = self.voice_typing.get_statistics()
        
        if self.predictive_text:
            subsystems_status["predictive_text"] = self.predictive_text.get_statistics()
        
        if self.auto_correction:
            subsystems_status["auto_correction"] = self.auto_correction.get_statistics()
        
        if self.input_method_manager:
            subsystems_status["input_method"] = self.input_method_manager.get_statistics()
        
        if self.shortcut_manager:
            subsystems_status["shortcuts"] = self.shortcut_manager.get_statistics()
        
        if self.metrics_collector:
            subsystems_status["metrics"] = self.metrics_collector.get_statistics()
        
        return {
            "is_initialized": self.is_initialized,
            "is_active": self.is_active,
            "current_language": self.current_language,
            "current_session": self.current_session_id,
            "total_sessions": len(self.input_sessions),
            "config": self.config.to_dict(),
            "subsystems": subsystems_status,
            "callbacks_count": len(self.text_input_callbacks) + len(self.error_handlers),
            "timestamp": time.time()
        }
    
    def get_metrics_report(self, time_window: float = 3600) -> Dict[str, Any]:
        """
        获取指标报告
        
        Args:
            time_window: 时间窗口（秒）
            
        Returns:
            Dict[str, Any]: 指标报告
        """
        if not self.metrics_collector:
            return {}
        
        return self.metrics_collector.generate_report(time_window)
    
    def save_system_state(self, file_path: str) -> bool:
        """
        保存系统状态
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否保存成功
        """
        try:
            system_state = {
                "status": self.get_status(),
                "config": self.config.to_dict(),
                "current_language": self.current_language,
                "sessions": {
                    sid: data for sid, data in self.input_sessions.items()
                },
                "save_time": time.time()
            }
            
            file_utils.save_json(file_path, system_state)
            logger.info(f"System state saved to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save system state: {e}")
            return False
    
    def load_system_state(self, file_path: str) -> bool:
        """
        加载系统状态
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否加载成功
        """
        try:
            if not file_utils.file_exists(file_path):
                logger.error(f"State file not found: {file_path}")
                return False
            
            system_state = file_utils.load_json(file_path)
            
            # 应用配置
            if "config" in system_state:
                for key, value in system_state["config"].items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
            
            # 应用语言
            if "current_language" in system_state:
                self.current_language = system_state["current_language"]
            
            # 恢复会话
            if "sessions" in system_state:
                self.input_sessions.update(system_state["sessions"])
            
            logger.info(f"System state loaded from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load system state: {e}")
            return False


# 导出所有公共类和函数
__all__ = [
    # 系统主类
    "TextInputSystem",
    "TextInputConfig",
    
    # 键盘处理模块
    "KeyboardHandler",
    "KeyEvent",
    "KeyEventType",
    
    # 手写识别模块
    "HandwritingRecognizer",
    "Stroke",
    "StrokePoint",
    "RecognitionResult",
    
    # 语音打字模块
    "VoiceTyping",
    "VoiceTypingResult",
    
    # 预测文本模块
    "PredictiveText",
    "PredictionCandidate",
    
    # 自动校正模块
    "AutoCorrection",
    "CorrectionCandidate",
    
    # 输入法模块
    "InputMethodManager",
    "InputMethod",
    "InputMethodEngine",
    "Candidate",
    
    # 快捷键模块
    "ShortcutManager",
    "Shortcut",
    
    # 指标收集模块
    "InputMetricsCollector",
    "InputMetrics",
    "InputSession",
]


# 创建全局实例的函数
_text_input_system_instance = None
_text_input_system_lock = threading.Lock()


def get_text_input_system(config_manager: Optional[ConfigManager] = None) -> TextInputSystem:
    """
    获取文本输入系统单例实例
    
    Args:
        config_manager: 配置管理器（如果为None，需要外部创建）
        
    Returns:
        TextInputSystem: 文本输入系统实例
    """
    global _text_input_system_instance
    
    with _text_input_system_lock:
        if _text_input_system_instance is None:
            if config_manager is None:
                # 创建默认配置管理器
                # 在实际项目中，应该从外部传入
                config_manager = ConfigManager()
            
            _text_input_system_instance = TextInputSystem(config_manager)
        
        return _text_input_system_instance


def initialize_text_input_system(config_manager: Optional[ConfigManager] = None) -> bool:
    """
    初始化文本输入系统
    
    Args:
        config_manager: 配置管理器
        
    Returns:
        bool: 是否初始化成功
    """
    system = get_text_input_system(config_manager)
    return system.initialize()


def activate_text_input_system() -> bool:
    """
    激活文本输入系统
    
    Returns:
        bool: 是否激活成功
    """
    system = get_text_input_system()
    return system.activate()


def deactivate_text_input_system() -> None:
    """
    停用文本输入系统
    """
    system = get_text_input_system()
    system.deactivate()


# 简化的便捷函数
def process_text_input(text: str, source: str = "manual") -> Dict[str, Any]:
    """
    处理文本输入（便捷函数）
    
    Args:
        text: 输入的文本
        source: 输入来源
        
    Returns:
        Dict[str, Any]: 处理结果
    """
    system = get_text_input_system()
    
    if not system.is_active:
        logger.warning("Text input system is not active")
        return {"error": "System not active"}
    
    try:
        # 处理文本
        processed_text = system._process_text(text)
        
        # 发布结果
        system.message_bus.publish("text_input_processed", {
            "original_text": text,
            "processed_text": processed_text,
            "source": source,
            "timestamp": time.time()
        })
        
        return {
            "original_text": text,
            "processed_text": processed_text,
            "source": source,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Error processing text input: {e}")
        return {"error": str(e), "success": False}


# 版本信息
__version__ = "1.0.0"
__author__ = "Mirexs AI Team"
__description__ = "Mirexs文本输入系统 - 集成键盘、手写、语音、预测、校正、输入法和快捷键管理"


# 包初始化时执行的代码
def _initialize_package():
    """包初始化函数"""
    logger.info(f"Initializing Mirexs Text Input System v{__version__}")
    
    # 检查必要的依赖
    try:
        import torch
        import numpy as np
        import cv2
        
        logger.debug(f"Core dependencies: torch={torch.__version__}, numpy={np.__version__}, opencv={cv2.__version__}")
        
    except ImportError as e:
        logger.warning(f"Missing dependency: {e}")
    
    # 创建必要的目录结构
    _create_directories()


def _create_directories():
    """创建必要的目录结构"""
    directories = [
        "data/user_data/input_method",
        "data/user_data/shortcuts",
        "data/user_data/dictionaries",
        "data/models/input_method",
        "data/models/nlp/predictive",
        "data/models/nlp/correction",
        "data/models/vision/handwriting",
        "config/input_methods",
        "config/shortcuts",
        "config/keyboard_layouts",
        "logs/text_input"
    ]
    
    for directory in directories:
        try:
            import os
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create directory {directory}: {e}")


# 执行包初始化
_initialize_package()
