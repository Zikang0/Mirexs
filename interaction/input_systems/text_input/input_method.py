"""
输入法模块：支持多语言输入法切换和管理
"""

import os
import json
import time
import threading
from typing import Dict, List, Optional, Any, Set, Tuple
import logging
from collections import defaultdict
from dataclasses import dataclass, field
import pickle

from infrastructure.communication.message_bus import MessageBus
from config.system import ConfigManager
from utils.ai_utilities.model_utils import ModelLoader

logger = logging.getLogger(__name__)


class InputMethodType:
    """输入法类型常量"""
    PINYIN = "pinyin"  # 拼音输入法
    WUBI = "wubi"      # 五笔输入法
    CANGJIE = "cangjie" # 仓颉输入法
    BOSHOMIA = "boshomia" # 嘸蝦米
    ENGLISH = "english"  # 英文输入法
    KOREAN = "korean"   # 韩文输入法
    JAPANESE = "japanese" # 日文输入法
    CUSTOM = "custom"   # 自定义输入法


@dataclass
class InputMethod:
    """输入法定义"""
    id: str
    name: str
    type: str
    language: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    enabled: bool = True
    priority: int = 0
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "language": self.language,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "enabled": self.enabled,
            "priority": self.priority
        }


@dataclass
class Candidate:
    """输入候选"""
    text: str
    code: str = ""  # 输入码
    weight: float = 1.0
    source: str = ""  # 来源
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "text": self.text,
            "code": self.code,
            "weight": self.weight,
            "source": self.source
        }


class InputMethodEngine:
    """输入法引擎基类"""
    
    def __init__(self, ime_id: str, config: Dict[str, Any]):
        self.ime_id = ime_id
        self.config = config
        self.is_active = False
        self.current_input = ""
        self.candidates = []
        
    def activate(self) -> bool:
        """激活输入法"""
        self.is_active = True
        return True
    
    def deactivate(self) -> None:
        """停用输入法"""
        self.is_active = False
    
    def process_input(self, key: str) -> List[Candidate]:
        """处理输入"""
        raise NotImplementedError
    
    def reset(self) -> None:
        """重置输入状态"""
        self.current_input = ""
        self.candidates = []
    
    def get_candidates(self) -> List[Candidate]:
        """获取当前候选"""
        return self.candidates
    
    def select_candidate(self, index: int) -> Optional[str]:
        """选择候选"""
        if 0 <= index < len(self.candidates):
            return self.candidates[index].text
        return None


class PinyinIME(InputMethodEngine):
    """拼音输入法引擎"""
    
    def __init__(self, ime_id: str, config: Dict[str, Any]):
        super().__init__(ime_id, config)
        self.pinyin_dict = {}
        self.user_dict = {}
        self._load_dictionaries()
    
    def _load_dictionaries(self) -> None:
        """加载字典"""
        try:
            # 加载拼音字典
            dict_path = self.config.get("pinyin_dict_path", "data/models/input_method/pinyin_dict.pkl")
            if os.path.exists(dict_path):
                with open(dict_path, 'rb') as f:
                    self.pinyin_dict = pickle.load(f)
            
            # 加载用户字典
            user_dict_path = self.config.get("user_dict_path", "data/user_data/input_method/pinyin_user.pkl")
            if os.path.exists(user_dict_path):
                with open(user_dict_path, 'rb') as f:
                    self.user_dict = pickle.load(f)
                    
        except Exception as e:
            logger.error(f"Failed to load pinyin dictionaries: {e}")
    
    def process_input(self, key: str) -> List[Candidate]:
        """处理拼音输入"""
        if not key.isalpha():
            return []
        
        self.current_input += key.lower()
        
        # 查找匹配的拼音
        candidates = []
        
        # 从系统字典查找
        if self.current_input in self.pinyin_dict:
            system_candidates = self.pinyin_dict[self.current_input]
            for text, weight in system_candidates[:10]:  # 取前10个
                candidates.append(Candidate(
                    text=text,
                    code=self.current_input,
                    weight=weight,
                    source="system"
                ))
        
        # 从用户字典查找
        if self.current_input in self.user_dict:
            user_candidates = self.user_dict[self.current_input]
            for text, weight in user_candidates:
                candidates.append(Candidate(
                    text=text,
                    code=self.current_input,
                    weight=weight * 1.2,  # 用户字典权重更高
                    source="user"
                ))
        
        # 按权重排序
        candidates.sort(key=lambda x: x.weight, reverse=True)
        self.candidates = candidates
        
        return candidates
    
    def learn_word(self, pinyin: str, word: str, weight: float = 1.0) -> None:
        """学习新词"""
        if pinyin not in self.user_dict:
            self.user_dict[pinyin] = []
        
        # 添加或更新权重
        for i, (existing_word, existing_weight) in enumerate(self.user_dict[pinyin]):
            if existing_word == word:
                self.user_dict[pinyin][i] = (word, existing_weight + weight)
                return
        
        # 新词
        self.user_dict[pinyin].append((word, weight))
        
        # 按权重排序
        self.user_dict[pinyin].sort(key=lambda x: x[1], reverse=True)
        
        # 限制大小
        if len(self.user_dict[pinyin]) > 100:
            self.user_dict[pinyin] = self.user_dict[pinyin][:100]
    
    def save_user_dict(self) -> bool:
        """保存用户字典"""
        try:
            user_dict_path = self.config.get("user_dict_path", "data/user_data/input_method/pinyin_user.pkl")
            os.makedirs(os.path.dirname(user_dict_path), exist_ok=True)
            
            with open(user_dict_path, 'wb') as f:
                pickle.dump(self.user_dict, f)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save user dictionary: {e}")
            return False


class EnglishIME(InputMethodEngine):
    """英文输入法引擎"""
    
    def process_input(self, key: str) -> List[Candidate]:
        """处理英文输入"""
        # 英文输入法直接返回输入的字符
        if key.isalpha() or key in " .,!?;:'\"-":
            self.current_input += key
            candidate = Candidate(
                text=self.current_input,
                code=self.current_input,
                weight=1.0,
                source="direct"
            )
            self.candidates = [candidate]
            return self.candidates
        
        return []


class InputMethodManager:
    """输入法管理器"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化输入法管理器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.message_bus = MessageBus()
        
        # 输入法注册表
        self.ime_registry = {}  # ime_id -> InputMethod
        self.ime_engines = {}   # ime_id -> InputMethodEngine
        
        # 当前状态
        self.current_ime = None
        self.active_ime = None
        self.ime_history = []  # 最近使用的输入法
        
        # 配置
        self.auto_switch = True
        self.switch_shortcut = "ctrl+space"
        self.cycle_shortcut = "ctrl+shift"
        
        # 线程安全
        self.lock = threading.RLock()
        
        # 加载配置
        self.load_config()
        
        # 加载输入法
        self.load_input_methods()
        
        logger.info("InputMethodManager initialized")
    
    def load_config(self) -> None:
        """加载配置"""
        try:
            config = self.config_manager.get_config("input_method_config")
            
            # 基本配置
            self.auto_switch = config.get("auto_switch", True)
            self.switch_shortcut = config.get("switch_shortcut", "ctrl+space")
            self.cycle_shortcut = config.get("cycle_shortcut", "ctrl+shift")
            self.default_language = config.get("default_language", "zh-CN")
            self.default_ime = config.get("default_ime", "pinyin")
            
            # 热键配置
            hotkeys = config.get("hotkeys", {})
            self.hotkey_ime_map = hotkeys.get("ime_mapping", {})
            
            # 学习配置
            learning = config.get("learning", {})
            self.enable_learning = learning.get("enable_learning", True)
            self.learning_rate = learning.get("learning_rate", 0.1)
            
            logger.debug(f"Input method config loaded: default_ime={self.default_ime}")
        except Exception as e:
            logger.error(f"Failed to load input method config: {e}")
    
    def load_input_methods(self) -> None:
        """加载输入法"""
        try:
            # 从配置文件加载输入法列表
            ime_config_path = "config/input_methods/installed.json"
            if os.path.exists(ime_config_path):
                with open(ime_config_path, 'r', encoding='utf-8') as f:
                    ime_list = json.load(f)
                    
                for ime_data in ime_list:
                    ime = InputMethod(**ime_data)
                    self.ime_registry[ime.id] = ime
                    
                    # 创建引擎实例
                    engine = self._create_engine(ime)
                    if engine:
                        self.ime_engines[ime.id] = engine
            
            # 加载系统内置输入法
            self._load_builtin_imes()
            
            # 设置默认输入法
            self._set_default_ime()
            
            logger.info(f"Loaded {len(self.ime_registry)} input methods")
            
        except Exception as e:
            logger.error(f"Failed to load input methods: {e}")
    
    def _load_builtin_imes(self) -> None:
        """加载系统内置输入法"""
        # 拼音输入法
        pinyin_ime = InputMethod(
            id="pinyin_zh",
            name="智能拼音",
            type=InputMethodType.PINYIN,
            language="zh-CN",
            description="智能拼音输入法，支持词频调整和用户词典",
            author="Mirexs",
            enabled=True,
            priority=100
        )
        self.ime_registry[pinyin_ime.id] = pinyin_ime
        
        # 英文输入法
        english_ime = InputMethod(
            id="english_us",
            name="English",
            type=InputMethodType.ENGLISH,
            language="en-US",
            description="英文输入法",
            author="Mirexs",
            enabled=True,
            priority=90
        )
        self.ime_registry[english_ime.id] = english_ime
        
        # 五笔输入法
        wubi_ime = InputMethod(
            id="wubi_zh",
            name="五笔输入法",
            type=InputMethodType.WUBI,
            language="zh-CN",
            description="五笔字形输入法",
            author="Mirexs",
            enabled=True,
            priority=80
        )
        self.ime_registry[wubi_ime.id] = wubi_ime
    
    def _create_engine(self, ime: InputMethod) -> Optional[InputMethodEngine]:
        """创建输入法引擎实例"""
        try:
            if ime.type == InputMethodType.PINYIN:
                config = ime.config.copy()
                config.update({
                    "pinyin_dict_path": f"data/models/input_method/{ime.language}/pinyin_dict.pkl",
                    "user_dict_path": f"data/user_data/input_method/{ime.id}_user.pkl"
                })
                return PinyinIME(ime.id, config)
                
            elif ime.type == InputMethodType.ENGLISH:
                return EnglishIME(ime.id, ime.config)
                
            elif ime.type == InputMethodType.WUBI:
                # TODO: 实现五笔引擎
                pass
                
            elif ime.type == InputMethodType.CUSTOM:
                # 加载自定义引擎
                engine_class = self._load_custom_engine(ime)
                if engine_class:
                    return engine_class(ime.id, ime.config)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create engine for {ime.id}: {e}")
            return None
    
    def _load_custom_engine(self, ime: InputMethod):
        """加载自定义引擎"""
        # TODO: 实现自定义引擎的动态加载
        return None
    
    def _set_default_ime(self) -> None:
        """设置默认输入法"""
        # 根据系统语言选择默认输入法
        system_language = self.default_language
        
        # 查找适合系统语言的输入法
        suitable_imes = [
            ime for ime in self.ime_registry.values()
            if ime.enabled and ime.language == system_language
        ]
        
        if suitable_imes:
            # 按优先级排序
            suitable_imes.sort(key=lambda x: x.priority, reverse=True)
            self.current_ime = suitable_imes[0].id
            self.active_ime = self.current_ime
            
            # 激活引擎
            if self.current_ime in self.ime_engines:
                self.ime_engines[self.current_ime].activate()
            
            logger.info(f"Default IME set to: {self.current_ime}")
        else:
            logger.warning(f"No suitable IME found for language: {system_language}")
    
    def switch_ime(self, ime_id: str) -> bool:
        """
        切换到指定输入法
        
        Args:
            ime_id: 输入法ID
            
        Returns:
            bool: 是否切换成功
        """
        with self.lock:
            if ime_id not in self.ime_registry:
                logger.error(f"IME not found: {ime_id}")
                return False
            
            ime = self.ime_registry[ime_id]
            if not ime.enabled:
                logger.error(f"IME is disabled: {ime_id}")
                return False
            
            # 停用当前输入法
            if self.active_ime and self.active_ime in self.ime_engines:
                self.ime_engines[self.active_ime].deactivate()
            
            # 激活新输入法
            if ime_id in self.ime_engines:
                self.ime_engines[ime_id].activate()
            
            # 更新状态
            old_ime = self.active_ime
            self.active_ime = ime_id
            self.current_ime = ime_id
            
            # 添加到历史
            if ime_id not in self.ime_history:
                self.ime_history.append(ime_id)
            else:
                # 移动到列表末尾
                self.ime_history.remove(ime_id)
                self.ime_history.append(ime_id)
            
            # 限制历史大小
            if len(self.ime_history) > 10:
                self.ime_history = self.ime_history[-10:]
            
            # 通知其他组件
            self.message_bus.publish("ime_switched", {
                "old_ime": old_ime,
                "new_ime": ime_id,
                "ime_info": ime.to_dict(),
                "timestamp": time.time()
            })
            
            logger.info(f"Switched IME from {old_ime} to {ime_id}")
            return True
    
    def cycle_ime(self, direction: int = 1) -> bool:
        """
        循环切换输入法
        
        Args:
            direction: 方向（1=下一个，-1=上一个）
            
        Returns:
            bool: 是否切换成功
        """
        with self.lock:
            # 获取启用的输入法列表
            enabled_imes = [
                ime_id for ime_id, ime in self.ime_registry.items()
                if ime.enabled
            ]
            
            if not enabled_imes:
                return False
            
            # 按优先级排序
            enabled_imes.sort(key=lambda x: self.ime_registry[x].priority, reverse=True)
            
            # 查找当前输入法的位置
            if self.active_ime not in enabled_imes:
                current_index = 0
            else:
                current_index = enabled_imes.index(self.active_ime)
            
            # 计算下一个位置
            next_index = (current_index + direction) % len(enabled_imes)
            
            # 切换到下一个输入法
            return self.switch_ime(enabled_imes[next_index])
    
    def process_key(self, key: str) -> List[Dict[str, Any]]:
        """
        处理按键输入
        
        Args:
            key: 按键字符
            
        Returns:
            List[Dict[str, Any]]: 候选列表
        """
        with self.lock:
            if not self.active_ime or self.active_ime not in self.ime_engines:
                return []
            
            engine = self.ime_engines[self.active_ime]
            candidates = engine.process_input(key)
            
            # 转换为字典格式
            candidate_dicts = [candidate.to_dict() for candidate in candidates]
            
            # 发布候选更新
            self.message_bus.publish("ime_candidates_updated", {
                "ime_id": self.active_ime,
                "candidates": candidate_dicts,
                "current_input": engine.current_input,
                "timestamp": time.time()
            })
            
            return candidate_dicts
    
    def select_candidate(self, index: int) -> Optional[str]:
        """
        选择候选
        
        Args:
            index: 候选索引
            
        Returns:
            str: 选中的文本，如果没有选中则返回None
        """
        with self.lock:
            if not self.active_ime or self.active_ime not in self.ime_engines:
                return None
            
            engine = self.ime_engines[self.active_ime]
            selected_text = engine.select_candidate(index)
            
            if selected_text:
                # 学习用户选择
                self._learn_selection(engine, selected_text)
                
                # 重置输入状态
                engine.reset()
                
                # 发布选择事件
                self.message_bus.publish("ime_candidate_selected", {
                    "ime_id": self.active_ime,
                    "selected_text": selected_text,
                    "index": index,
                    "timestamp": time.time()
                })
                
                logger.debug(f"Selected candidate: {selected_text}")
            
            return selected_text
    
    def _learn_selection(self, engine: InputMethodEngine, selected_text: str) -> None:
        """学习用户选择"""
        if not self.enable_learning:
            return
        
        # 如果是拼音输入法，学习这个词
        if isinstance(engine, PinyinIME):
            engine.learn_word(engine.current_input, selected_text, self.learning_rate)
    
    def reset_input(self) -> None:
        """重置输入状态"""
        with self.lock:
            if self.active_ime and self.active_ime in self.ime_engines:
                self.ime_engines[self.active_ime].reset()
                
                # 发布重置事件
                self.message_bus.publish("ime_input_reset", {
                    "ime_id": self.active_ime,
                    "timestamp": time.time()
                })
    
    def register_ime(self, ime_definition: Dict[str, Any]) -> bool:
        """
        注册新输入法
        
        Args:
            ime_definition: 输入法定义
            
        Returns:
            bool: 是否注册成功
        """
        try:
            ime = InputMethod(**ime_definition)
            
            with self.lock:
                # 检查是否已存在
                if ime.id in self.ime_registry:
                    logger.warning(f"IME already registered: {ime.id}")
                    return False
                
                # 创建引擎
                engine = self._create_engine(ime)
                if not engine:
                    logger.error(f"Failed to create engine for IME: {ime.id}")
                    return False
                
                # 注册
                self.ime_registry[ime.id] = ime
                self.ime_engines[ime.id] = engine
                
                logger.info(f"Registered new IME: {ime.id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to register IME: {e}")
            return False
    
    def unregister_ime(self, ime_id: str) -> bool:
        """
        注销输入法
        
        Args:
            ime_id: 输入法ID
            
        Returns:
            bool: 是否注销成功
        """
        with self.lock:
            if ime_id not in self.ime_registry:
                return False
            
            # 如果是当前活动输入法，先切换到其他输入法
            if self.active_ime == ime_id:
                # 查找其他可用的输入法
                other_imes = [
                    id for id in self.ime_registry.keys()
                    if id != ime_id and self.ime_registry[id].enabled
                ]
                
                if other_imes:
                    self.switch_ime(other_imes[0])
                else:
                    self.active_ime = None
                    self.current_ime = None
            
            # 移除
            del self.ime_registry[ime_id]
            if ime_id in self.ime_engines:
                del self.ime_engines[ime_id]
            
            # 从历史中移除
            if ime_id in self.ime_history:
                self.ime_history.remove(ime_id)
            
            logger.info(f"Unregistered IME: {ime_id}")
            return True
    
    def save_user_data(self) -> bool:
        """
        保存用户数据
        
        Returns:
            bool: 是否保存成功
        """
        try:
            # 保存所有输入法的用户数据
            for ime_id, engine in self.ime_engines.items():
                if isinstance(engine, PinyinIME):
                    engine.save_user_dict()
            
            # 保存输入法配置
            config_data = {
                "current_ime": self.current_ime,
                "ime_history": self.ime_history,
                "auto_switch": self.auto_switch
            }
            
            config_path = "data/user_data/input_method/config.json"
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            logger.info("Input method user data saved")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save user data: {e}")
            return False
    
    def load_user_data(self) -> bool:
        """
        加载用户数据
        
        Returns:
            bool: 是否加载成功
        """
        try:
            config_path = "data/user_data/input_method/config.json"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                self.current_ime = config_data.get("current_ime", self.current_ime)
                self.ime_history = config_data.get("ime_history", [])
                self.auto_switch = config_data.get("auto_switch", self.auto_switch)
                
                # 切换到保存的输入法
                if self.current_ime and self.current_ime in self.ime_registry:
                    self.switch_ime(self.current_ime)
                
                logger.info("Input method user data loaded")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to load user data: {e}")
            return False
    
    def get_ime_list(self) -> List[Dict[str, Any]]:
        """
        获取输入法列表
        
        Returns:
            List[Dict[str, Any]]: 输入法信息列表
        """
        with self.lock:
            ime_list = []
            for ime in self.ime_registry.values():
                ime_dict = ime.to_dict()
                ime_dict["is_active"] = (ime.id == self.active_ime)
                ime_dict["has_engine"] = (ime.id in self.ime_engines)
                ime_list.append(ime_dict)
            
            # 按优先级排序
            ime_list.sort(key=lambda x: x["priority"], reverse=True)
            return ime_list
    
    def get_current_ime_info(self) -> Optional[Dict[str, Any]]:
        """
        获取当前输入法信息
        
        Returns:
            Dict[str, Any]: 输入法信息，如果没有活动输入法则返回None
        """
        if not self.active_ime or self.active_ime not in self.ime_registry:
            return None
        
        ime = self.ime_registry[self.active_ime]
        info = ime.to_dict()
        info["is_active"] = True
        
        # 添加入引擎状态
        if self.active_ime in self.ime_engines:
            engine = self.ime_engines[self.active_ime]
            info["engine_status"] = {
                "is_active": engine.is_active,
                "current_input": engine.current_input,
                "candidates_count": len(engine.candidates)
            }
        
        return info
    
    def auto_detect_language(self, text: str) -> Optional[str]:
        """
        自动检测文本语言
        
        Args:
            text: 要检测的文本
            
        Returns:
            str: 语言代码，如果无法检测则返回None
        """
        if not text:
            return None
        
        # 简单的语言检测
        # 统计中文字符
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        chinese_ratio = chinese_chars / len(text) if text else 0
        
        # 统计英文字母
        english_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
        english_ratio = english_chars / len(text) if text else 0
        
        # 检测日文假名
        hiragana_chars = sum(1 for c in text if '\u3040' <= c <= '\u309f')
        katakana_chars = sum(1 for c in text if '\u30a0' <= c <= '\u30ff')
        japanese_ratio = (hiragana_chars + katakana_chars) / len(text) if text else 0
        
        # 检测韩文
        korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7a3')
        korean_ratio = korean_chars / len(text) if text else 0
        
        # 确定主要语言
        if chinese_ratio > 0.3:
            return "zh-CN"
        elif english_ratio > 0.7:
            return "en-US"
        elif japanese_ratio > 0.3:
            return "ja-JP"
        elif korean_ratio > 0.3:
            return "ko-KR"
        else:
            return None
    
    def auto_switch_ime(self, text: str) -> bool:
        """
        根据文本自动切换输入法
        
        Args:
            text: 文本内容
            
        Returns:
            bool: 是否切换成功
        """
        if not self.auto_switch:
            return False
        
        detected_language = self.auto_detect_language(text)
        if not detected_language:
            return False
        
        # 查找适合该语言的输入法
        suitable_imes = [
            ime_id for ime_id, ime in self.ime_registry.items()
            if ime.enabled and ime.language == detected_language
        ]
        
        if suitable_imes and (not self.active_ime or self.ime_registry[self.active_ime].language != detected_language):
            # 按优先级排序
            suitable_imes.sort(key=lambda x: self.ime_registry[x].priority, reverse=True)
            return self.switch_ime(suitable_imes[0])
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取输入法统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self.lock:
            return {
                "total_imes": len(self.ime_registry),
                "active_ime": self.active_ime,
                "current_ime": self.current_ime,
                "ime_history_size": len(self.ime_history),
                "auto_switch_enabled": self.auto_switch,
                "engines_loaded": len(self.ime_engines),
                "languages_supported": list(set(ime.language for ime in self.ime_registry.values()))
            }

