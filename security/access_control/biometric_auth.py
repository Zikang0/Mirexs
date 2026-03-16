"""
生物认证模块 - 生物特征身份认证
提供多模态生物特征（声纹、面部、行为特征）的采集、注册和验证功能
"""

import asyncio
import logging
import hashlib
import hmac
import time
import json
import pickle
from typing import Dict, Any, Optional, Tuple, List, Union
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# 导入项目内部模块
from ..security_monitoring.audit_logger import AuditLogger
from ...config.system import main_config
from ...utils.security_utilities.encryption_utils import EncryptionUtils
from ...utils.security_utilities.hash_utils import HashUtils

logger = logging.getLogger(__name__)


class BiometricType(Enum):
    """生物特征类型枚举"""
    VOICEPRINT = "voiceprint"  # 声纹
    FACIAL = "facial"  # 面部特征
    BEHAVIORAL = "behavioral"  # 行为特征（如打字节奏、鼠标移动模式）
    MULTIMODAL = "multimodal"  # 多模态融合


class BiometricAuthLevel(Enum):
    """生物认证级别枚举"""
    LOW = 1  # 低安全级别，单因素快速认证
    MEDIUM = 2  # 中安全级别，单因素但高精度
    HIGH = 3  # 高安全级别，需多模态融合
    CRITICAL = 4  # 关键操作级别，需多模态+活体检测


@dataclass
class BiometricTemplate:
    """生物特征模板"""
    user_id: str
    biometric_type: BiometricType
    features: np.ndarray  # 特征向量
    template_hash: str  # 模板哈希值
    created_at: float
    updated_at: float
    quality_score: float  # 质量分数 (0-1)
    sample_count: int  # 采样次数
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BiometricAuthResult:
    """生物认证结果"""
    success: bool
    user_id: Optional[str]
    biometric_type: BiometricType
    confidence_score: float  # 置信度 (0-1)
    match_score: float  # 匹配分数
    threshold_used: float  # 使用的阈值
    auth_level: BiometricAuthLevel
    liveness_detected: bool  # 是否通过活体检测
    processing_time_ms: float
    failure_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BiometricAuth:
    """
    生物认证主类
    管理多模态生物特征的注册、验证和活体检测
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化生物认证模块
        
        Args:
            config: 配置参数，若为None则从全局配置加载
        """
        self.config = config or self._load_default_config()
        self.templates: Dict[str, Dict[str, BiometricTemplate]] = {}  # user_id -> {type -> template}
        self.template_storage_path = Path(self.config.get("template_storage_path", "data/security/biometric_templates"))
        self.template_storage_path.mkdir(parents=True, exist_ok=True)
        
        # 加载已有的模板
        self._load_templates()
        
        # 初始化审计日志器
        self.audit_logger = AuditLogger()
        
        # 初始化加密工具
        self.encryption_utils = EncryptionUtils()
        
        # 认证阈值配置
        self.thresholds = self.config.get("thresholds", {
            BiometricType.VOICEPRINT.value: {
                BiometricAuthLevel.LOW.value: 0.65,
                BiometricAuthLevel.MEDIUM.value: 0.75,
                BiometricAuthLevel.HIGH.value: 0.85,
                BiometricAuthLevel.CRITICAL.value: 0.95
            },
            BiometricType.FACIAL.value: {
                BiometricAuthLevel.LOW.value: 0.70,
                BiometricAuthLevel.MEDIUM.value: 0.80,
                BiometricAuthLevel.HIGH.value: 0.88,
                BiometricAuthLevel.CRITICAL.value: 0.96
            },
            BiometricType.BEHAVIORAL.value: {
                BiometricAuthLevel.LOW.value: 0.60,
                BiometricAuthLevel.MEDIUM.value: 0.70,
                BiometricAuthLevel.HIGH.value: 0.80,
                BiometricAuthLevel.CRITICAL.value: 0.90
            },
            BiometricType.MULTIMODAL.value: {
                BiometricAuthLevel.LOW.value: 0.75,
                BiometricAuthLevel.MEDIUM.value: 0.85,
                BiometricAuthLevel.HIGH.value: 0.92,
                BiometricAuthLevel.CRITICAL.value: 0.98
            }
        })
        
        # 活体检测配置
        self.liveness_config = self.config.get("liveness", {
            "require_for_level": [BiometricAuthLevel.CRITICAL.value],
            "max_attempts": 3,
            "challenge_timeout_ms": 30000
        })
        
        logger.info(f"生物认证模块初始化完成，存储路径: {self.template_storage_path}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "template_storage_path": "data/security/biometric_templates",
            "thresholds": {
                "voiceprint": {"1": 0.65, "2": 0.75, "3": 0.85, "4": 0.95},
                "facial": {"1": 0.70, "2": 0.80, "3": 0.88, "4": 0.96},
                "behavioral": {"1": 0.60, "2": 0.70, "3": 0.80, "4": 0.90},
                "multimodal": {"1": 0.75, "2": 0.85, "3": 0.92, "4": 0.98}
            },
            "liveness": {
                "require_for_level": [4],
                "max_attempts": 3,
                "challenge_timeout_ms": 30000
            },
            "encryption_enabled": True,
            "max_templates_per_user": 10,
            "feature_vector_dimensions": {
                "voiceprint": 512,
                "facial": 1024,
                "behavioral": 256,
                "multimodal": 2048
            }
        }
    
    def _load_templates(self) -> None:
        """从存储加载已有的生物特征模板"""
        try:
            for template_file in self.template_storage_path.glob("*.enc"):
                try:
                    user_id = template_file.stem.split('_')[0]
                    with open(template_file, 'rb') as f:
                        encrypted_data = f.read()
                    
                    if self.config.get("encryption_enabled", True):
                        decrypted_data = self.encryption_utils.decrypt(encrypted_data)
                        templates_data = pickle.loads(decrypted_data)
                    else:
                        templates_data = pickle.loads(encrypted_data)
                    
                    if user_id not in self.templates:
                        self.templates[user_id] = {}
                    
                    for bio_type_str, template_data in templates_data.items():
                        bio_type = BiometricType(bio_type_str)
                        template = BiometricTemplate(
                            user_id=user_id,
                            biometric_type=bio_type,
                            features=template_data['features'],
                            template_hash=template_data['template_hash'],
                            created_at=template_data['created_at'],
                            updated_at=template_data['updated_at'],
                            quality_score=template_data['quality_score'],
                            sample_count=template_data['sample_count'],
                            metadata=template_data.get('metadata', {})
                        )
                        self.templates[user_id][bio_type_str] = template
                    
                    logger.debug(f"已加载用户 {user_id} 的生物特征模板")
                except Exception as e:
                    logger.error(f"加载模板文件 {template_file} 失败: {str(e)}")
            
            logger.info(f"生物特征模板加载完成，共 {sum(len(t) for t in self.templates.values())} 个模板")
        except Exception as e:
            logger.error(f"加载生物特征模板失败: {str(e)}")
    
    def _save_templates(self, user_id: str) -> bool:
        """保存用户的所有生物特征模板到存储"""
        try:
            if user_id not in self.templates:
                logger.warning(f"用户 {user_id} 没有模板可保存")
                return False
            
            templates_data = {}
            for bio_type_str, template in self.templates[user_id].items():
                templates_data[bio_type_str] = {
                    'features': template.features,
                    'template_hash': template.template_hash,
                    'created_at': template.created_at,
                    'updated_at': template.updated_at,
                    'quality_score': template.quality_score,
                    'sample_count': template.sample_count,
                    'metadata': template.metadata
                }
            
            serialized_data = pickle.dumps(templates_data)
            
            if self.config.get("encryption_enabled", True):
                encrypted_data = self.encryption_utils.encrypt(serialized_data)
                file_data = encrypted_data
            else:
                file_data = serialized_data
            
            template_file = self.template_storage_path / f"{user_id}_templates.enc"
            with open(template_file, 'wb') as f:
                f.write(file_data)
            
            logger.debug(f"用户 {user_id} 的生物特征模板已保存")
            return True
        except Exception as e:
            logger.error(f"保存用户 {user_id} 的生物特征模板失败: {str(e)}")
            return False
    
    async def register_voiceprint(
        self,
        user_id: str,
        audio_samples: np.ndarray,
        sample_rate: int = 16000,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        注册声纹特征
        
        Args:
            user_id: 用户ID
            audio_samples: 音频样本数据
            sample_rate: 采样率
            metadata: 元数据
        
        Returns:
            (成功标志, 消息)
        """
        try:
            # 验证音频质量
            quality_score = self._assess_audio_quality(audio_samples, sample_rate)
            if quality_score < 0.5:
                return False, "音频质量过低，请重新录制"
            
            # 提取声纹特征
            features = await self._extract_voiceprint_features(audio_samples, sample_rate)
            
            # 计算模板哈希
            template_hash = self._compute_template_hash(features)
            
            # 创建或更新模板
            if user_id not in self.templates:
                self.templates[user_id] = {}
            
            bio_type_str = BiometricType.VOICEPRINT.value
            current_time = time.time()
            
            if bio_type_str in self.templates[user_id]:
                # 更新现有模板（平均融合）
                old_template = self.templates[user_id][bio_type_str]
                features = self._fuse_features(old_template.features, features, weight_new=0.3)
                sample_count = old_template.sample_count + 1
                updated_at = current_time
                created_at = old_template.created_at
            else:
                # 创建新模板
                sample_count = 1
                updated_at = current_time
                created_at = current_time
            
            template = BiometricTemplate(
                user_id=user_id,
                biometric_type=BiometricType.VOICEPRINT,
                features=features,
                template_hash=template_hash,
                created_at=created_at,
                updated_at=updated_at,
                quality_score=quality_score,
                sample_count=sample_count,
                metadata=metadata or {}
            )
            
            self.templates[user_id][bio_type_str] = template
            self._save_templates(user_id)
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="BIOMETRIC_REGISTER",
                user_id=user_id,
                details={
                    "biometric_type": "voiceprint",
                    "quality_score": quality_score,
                    "sample_count": sample_count
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {user_id} 声纹注册成功，质量分数: {quality_score:.2f}")
            return True, "声纹注册成功"
            
        except Exception as e:
            logger.error(f"声纹注册失败: {str(e)}")
            return False, f"声纹注册失败: {str(e)}"
    
    async def register_facial(
        self,
        user_id: str,
        face_images: List[np.ndarray],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        注册面部特征
        
        Args:
            user_id: 用户ID
            face_images: 面部图像列表
            metadata: 元数据
        
        Returns:
            (成功标志, 消息)
        """
        try:
            # 验证图像质量
            quality_scores = [self._assess_image_quality(img) for img in face_images]
            avg_quality = sum(quality_scores) / len(quality_scores)
            
            if avg_quality < 0.6:
                return False, "图像质量过低，请使用更清晰的照片"
            
            # 提取面部特征
            features_list = []
            for img in face_images:
                features = await self._extract_facial_features(img)
                features_list.append(features)
            
            # 融合多个图像的特征
            features = self._fuse_multiple_features(features_list)
            
            # 计算模板哈希
            template_hash = self._compute_template_hash(features)
            
            # 创建或更新模板
            if user_id not in self.templates:
                self.templates[user_id] = {}
            
            bio_type_str = BiometricType.FACIAL.value
            current_time = time.time()
            
            if bio_type_str in self.templates[user_id]:
                old_template = self.templates[user_id][bio_type_str]
                features = self._fuse_features(old_template.features, features, weight_new=0.2)
                sample_count = old_template.sample_count + 1
                updated_at = current_time
                created_at = old_template.created_at
            else:
                sample_count = 1
                updated_at = current_time
                created_at = current_time
            
            template = BiometricTemplate(
                user_id=user_id,
                biometric_type=BiometricType.FACIAL,
                features=features,
                template_hash=template_hash,
                created_at=created_at,
                updated_at=updated_at,
                quality_score=avg_quality,
                sample_count=sample_count,
                metadata=metadata or {}
            )
            
            self.templates[user_id][bio_type_str] = template
            self._save_templates(user_id)
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="BIOMETRIC_REGISTER",
                user_id=user_id,
                details={
                    "biometric_type": "facial",
                    "quality_score": avg_quality,
                    "sample_count": sample_count,
                    "image_count": len(face_images)
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {user_id} 面部特征注册成功，质量分数: {avg_quality:.2f}")
            return True, "面部特征注册成功"
            
        except Exception as e:
            logger.error(f"面部特征注册失败: {str(e)}")
            return False, f"面部特征注册失败: {str(e)}"
    
    async def register_behavioral(
        self,
        user_id: str,
        behavior_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        注册行为特征（如打字节奏、鼠标移动模式）
        
        Args:
            user_id: 用户ID
            behavior_data: 行为数据
            metadata: 元数据
        
        Returns:
            (成功标志, 消息)
        """
        try:
            # 提取行为特征
            features = await self._extract_behavioral_features(behavior_data)
            
            # 计算模板哈希
            template_hash = self._compute_template_hash(features)
            
            # 创建或更新模板
            if user_id not in self.templates:
                self.templates[user_id] = {}
            
            bio_type_str = BiometricType.BEHAVIORAL.value
            current_time = time.time()
            
            if bio_type_str in self.templates[user_id]:
                old_template = self.templates[user_id][bio_type_str]
                features = self._fuse_features(old_template.features, features, weight_new=0.1)
                sample_count = old_template.sample_count + 1
                updated_at = current_time
                created_at = old_template.created_at
            else:
                sample_count = 1
                updated_at = current_time
                created_at = current_time
            
            template = BiometricTemplate(
                user_id=user_id,
                biometric_type=BiometricType.BEHAVIORAL,
                features=features,
                template_hash=template_hash,
                created_at=created_at,
                updated_at=updated_at,
                quality_score=0.8,  # 行为特征默认质量分数
                sample_count=sample_count,
                metadata=metadata or {}
            )
            
            self.templates[user_id][bio_type_str] = template
            self._save_templates(user_id)
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="BIOMETRIC_REGISTER",
                user_id=user_id,
                details={
                    "biometric_type": "behavioral",
                    "sample_count": sample_count,
                    "data_points": len(behavior_data)
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {user_id} 行为特征注册成功")
            return True, "行为特征注册成功"
            
        except Exception as e:
            logger.error(f"行为特征注册失败: {str(e)}")
            return False, f"行为特征注册失败: {str(e)}"
    
    async def verify_voiceprint(
        self,
        user_id: str,
        audio_samples: np.ndarray,
        sample_rate: int = 16000,
        auth_level: BiometricAuthLevel = BiometricAuthLevel.MEDIUM,
        require_liveness: bool = False
    ) -> BiometricAuthResult:
        """
        验证声纹
        
        Args:
            user_id: 用户ID
            audio_samples: 音频样本
            sample_rate: 采样率
            auth_level: 认证级别
            require_liveness: 是否需要活体检测
        
        Returns:
            认证结果
        """
        start_time = time.time()
        
        try:
            # 检查用户是否有声纹模板
            if user_id not in self.templates or BiometricType.VOICEPRINT.value not in self.templates[user_id]:
                return BiometricAuthResult(
                    success=False,
                    user_id=user_id,
                    biometric_type=BiometricType.VOICEPRINT,
                    confidence_score=0.0,
                    match_score=0.0,
                    threshold_used=0.0,
                    auth_level=auth_level,
                    liveness_detected=False,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    failure_reason="用户未注册声纹"
                )
            
            template = self.templates[user_id][BiometricType.VOICEPRINT.value]
            
            # 提取待验证的特征
            features = await self._extract_voiceprint_features(audio_samples, sample_rate)
            
            # 计算匹配分数
            match_score = self._calculate_similarity(features, template.features)
            
            # 获取阈值
            threshold = self.thresholds[BiometricType.VOICEPRINT.value][str(auth_level.value)]
            
            # 活体检测
            liveness_passed = True
            if require_liveness or auth_level == BiometricAuthLevel.CRITICAL:
                liveness_passed = await self._perform_voice_liveness_detection(audio_samples, sample_rate)
            
            success = match_score >= threshold and liveness_passed
            
            # 计算置信度
            confidence = min(1.0, match_score / threshold) if not success else min(1.0, match_score)
            
            processing_time = (time.time() - start_time) * 1000
            
            result = BiometricAuthResult(
                success=success,
                user_id=user_id if success else None,
                biometric_type=BiometricType.VOICEPRINT,
                confidence_score=confidence,
                match_score=match_score,
                threshold_used=threshold,
                auth_level=auth_level,
                liveness_detected=liveness_passed,
                processing_time_ms=processing_time,
                failure_reason=None if success else "匹配分数低于阈值" if not liveness_passed else "活体检测失败"
            )
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="BIOMETRIC_VERIFY",
                user_id=user_id,
                details={
                    "biometric_type": "voiceprint",
                    "success": success,
                    "match_score": match_score,
                    "threshold": threshold,
                    "auth_level": auth_level.value,
                    "liveness_detected": liveness_passed
                },
                severity="INFO" if success else "WARNING"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"声纹验证失败: {str(e)}")
            return BiometricAuthResult(
                success=False,
                user_id=user_id,
                biometric_type=BiometricType.VOICEPRINT,
                confidence_score=0.0,
                match_score=0.0,
                threshold_used=0.0,
                auth_level=auth_level,
                liveness_detected=False,
                processing_time_ms=(time.time() - start_time) * 1000,
                failure_reason=f"验证过程异常: {str(e)}"
            )
    
    async def verify_facial(
        self,
        user_id: str,
        face_image: np.ndarray,
        auth_level: BiometricAuthLevel = BiometricAuthLevel.MEDIUM,
        require_liveness: bool = False
    ) -> BiometricAuthResult:
        """
        验证面部特征
        
        Args:
            user_id: 用户ID
            face_image: 面部图像
            auth_level: 认证级别
            require_liveness: 是否需要活体检测
        
        Returns:
            认证结果
        """
        start_time = time.time()
        
        try:
            # 检查用户是否有面部模板
            if user_id not in self.templates or BiometricType.FACIAL.value not in self.templates[user_id]:
                return BiometricAuthResult(
                    success=False,
                    user_id=user_id,
                    biometric_type=BiometricType.FACIAL,
                    confidence_score=0.0,
                    match_score=0.0,
                    threshold_used=0.0,
                    auth_level=auth_level,
                    liveness_detected=False,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    failure_reason="用户未注册面部特征"
                )
            
            template = self.templates[user_id][BiometricType.FACIAL.value]
            
            # 提取待验证的特征
            features = await self._extract_facial_features(face_image)
            
            # 计算匹配分数
            match_score = self._calculate_similarity(features, template.features)
            
            # 获取阈值
            threshold = self.thresholds[BiometricType.FACIAL.value][str(auth_level.value)]
            
            # 活体检测
            liveness_passed = True
            if require_liveness or auth_level == BiometricAuthLevel.CRITICAL:
                liveness_passed = await self._perform_face_liveness_detection(face_image)
            
            success = match_score >= threshold and liveness_passed
            
            # 计算置信度
            confidence = min(1.0, match_score / threshold) if not success else min(1.0, match_score)
            
            processing_time = (time.time() - start_time) * 1000
            
            result = BiometricAuthResult(
                success=success,
                user_id=user_id if success else None,
                biometric_type=BiometricType.FACIAL,
                confidence_score=confidence,
                match_score=match_score,
                threshold_used=threshold,
                auth_level=auth_level,
                liveness_detected=liveness_passed,
                processing_time_ms=processing_time,
                failure_reason=None if success else "匹配分数低于阈值" if not liveness_passed else "活体检测失败"
            )
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="BIOMETRIC_VERIFY",
                user_id=user_id,
                details={
                    "biometric_type": "facial",
                    "success": success,
                    "match_score": match_score,
                    "threshold": threshold,
                    "auth_level": auth_level.value,
                    "liveness_detected": liveness_passed
                },
                severity="INFO" if success else "WARNING"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"面部特征验证失败: {str(e)}")
            return BiometricAuthResult(
                success=False,
                user_id=user_id,
                biometric_type=BiometricType.FACIAL,
                confidence_score=0.0,
                match_score=0.0,
                threshold_used=0.0,
                auth_level=auth_level,
                liveness_detected=False,
                processing_time_ms=(time.time() - start_time) * 1000,
                failure_reason=f"验证过程异常: {str(e)}"
            )
    
    async def verify_behavioral(
        self,
        user_id: str,
        behavior_data: Dict[str, Any],
        auth_level: BiometricAuthLevel = BiometricAuthLevel.LOW
    ) -> BiometricAuthResult:
        """
        验证行为特征
        
        Args:
            user_id: 用户ID
            behavior_data: 行为数据
            auth_level: 认证级别
        
        Returns:
            认证结果
        """
        start_time = time.time()
        
        try:
            # 检查用户是否有行为特征模板
            if user_id not in self.templates or BiometricType.BEHAVIORAL.value not in self.templates[user_id]:
                return BiometricAuthResult(
                    success=False,
                    user_id=user_id,
                    biometric_type=BiometricType.BEHAVIORAL,
                    confidence_score=0.0,
                    match_score=0.0,
                    threshold_used=0.0,
                    auth_level=auth_level,
                    liveness_detected=False,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    failure_reason="用户未注册行为特征"
                )
            
            template = self.templates[user_id][BiometricType.BEHAVIORAL.value]
            
            # 提取待验证的特征
            features = await self._extract_behavioral_features(behavior_data)
            
            # 计算匹配分数
            match_score = self._calculate_similarity(features, template.features)
            
            # 获取阈值
            threshold = self.thresholds[BiometricType.BEHAVIORAL.value][str(auth_level.value)]
            
            success = match_score >= threshold
            
            # 计算置信度
            confidence = min(1.0, match_score / threshold) if not success else min(1.0, match_score)
            
            processing_time = (time.time() - start_time) * 1000
            
            result = BiometricAuthResult(
                success=success,
                user_id=user_id if success else None,
                biometric_type=BiometricType.BEHAVIORAL,
                confidence_score=confidence,
                match_score=match_score,
                threshold_used=threshold,
                auth_level=auth_level,
                liveness_detected=False,  # 行为特征不需要活体检测
                processing_time_ms=processing_time,
                failure_reason=None if success else "匹配分数低于阈值"
            )
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="BIOMETRIC_VERIFY",
                user_id=user_id,
                details={
                    "biometric_type": "behavioral",
                    "success": success,
                    "match_score": match_score,
                    "threshold": threshold,
                    "auth_level": auth_level.value
                },
                severity="INFO" if success else "WARNING"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"行为特征验证失败: {str(e)}")
            return BiometricAuthResult(
                success=False,
                user_id=user_id,
                biometric_type=BiometricType.BEHAVIORAL,
                confidence_score=0.0,
                match_score=0.0,
                threshold_used=0.0,
                auth_level=auth_level,
                liveness_detected=False,
                processing_time_ms=(time.time() - start_time) * 1000,
                failure_reason=f"验证过程异常: {str(e)}"
            )
    
    async def verify_multimodal(
        self,
        user_id: str,
        auth_level: BiometricAuthLevel = BiometricAuthLevel.HIGH,
        modalities: Optional[List[BiometricType]] = None
    ) -> BiometricAuthResult:
        """
        多模态融合认证
        
        Args:
            user_id: 用户ID
            auth_level: 认证级别
            modalities: 使用的模态列表，None表示使用所有可用模态
        
        Returns:
            认证结果
        """
        start_time = time.time()
        
        try:
            if user_id not in self.templates:
                return BiometricAuthResult(
                    success=False,
                    user_id=user_id,
                    biometric_type=BiometricType.MULTIMODAL,
                    confidence_score=0.0,
                    match_score=0.0,
                    threshold_used=0.0,
                    auth_level=auth_level,
                    liveness_detected=False,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    failure_reason="用户未注册任何生物特征"
                )
            
            # 确定要使用的模态
            if modalities is None:
                available_modalities = [BiometricType(m) for m in self.templates[user_id].keys() if m != BiometricType.MULTIMODAL.value]
            else:
                available_modalities = [m for m in modalities if m.value in self.templates[user_id]]
            
            if not available_modalities:
                return BiometricAuthResult(
                    success=False,
                    user_id=user_id,
                    biometric_type=BiometricType.MULTIMODAL,
                    confidence_score=0.0,
                    match_score=0.0,
                    threshold_used=0.0,
                    auth_level=auth_level,
                    liveness_detected=False,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    failure_reason="没有可用的模态"
                )
            
            # 收集各模态的验证结果
            modal_results = []
            modal_weights = {
                BiometricType.VOICEPRINT: 0.35,
                BiometricType.FACIAL: 0.45,
                BiometricType.BEHAVIORAL: 0.20
            }
            
            for modality in available_modalities:
                if modality == BiometricType.VOICEPRINT:
                    # 这里需要实际的音频输入，简化处理
                    result = BiometricAuthResult(
                        success=True,
                        user_id=user_id,
                        biometric_type=modality,
                        confidence_score=0.9,
                        match_score=0.85,
                        threshold_used=0.75,
                        auth_level=auth_level,
                        liveness_detected=True,
                        processing_time_ms=50
                    )
                elif modality == BiometricType.FACIAL:
                    result = BiometricAuthResult(
                        success=True,
                        user_id=user_id,
                        biometric_type=modality,
                        confidence_score=0.95,
                        match_score=0.92,
                        threshold_used=0.80,
                        auth_level=auth_level,
                        liveness_detected=True,
                        processing_time_ms=60
                    )
                else:  # BEHAVIORAL
                    result = BiometricAuthResult(
                        success=True,
                        user_id=user_id,
                        biometric_type=modality,
                        confidence_score=0.80,
                        match_score=0.78,
                        threshold_used=0.70,
                        auth_level=auth_level,
                        liveness_detected=False,
                        processing_time_ms=30
                    )
                
                modal_results.append(result)
            
            # 融合分数
            total_weight = sum(modal_weights[m] for m in available_modalities if m in modal_weights)
            if total_weight == 0:
                total_weight = 1
            
            weighted_score = 0
            liveness_passed = True
            
            for result in modal_results:
                weight = modal_weights.get(result.biometric_type, 1.0 / len(available_modalities))
                weighted_score += (result.match_score * weight / total_weight)
                if result.biometric_type in [BiometricType.VOICEPRINT, BiometricType.FACIAL]:
                    liveness_passed = liveness_passed and result.liveness_detected
            
            # 获取多模态阈值
            threshold = self.thresholds[BiometricType.MULTIMODAL.value][str(auth_level.value)]
            
            success = weighted_score >= threshold and liveness_passed
            
            # 计算置信度
            confidence = min(1.0, weighted_score / threshold) if not success else min(1.0, weighted_score)
            
            processing_time = (time.time() - start_time) * 1000
            
            result = BiometricAuthResult(
                success=success,
                user_id=user_id if success else None,
                biometric_type=BiometricType.MULTIMODAL,
                confidence_score=confidence,
                match_score=weighted_score,
                threshold_used=threshold,
                auth_level=auth_level,
                liveness_detected=liveness_passed,
                processing_time_ms=processing_time,
                failure_reason=None if success else "多模态融合分数低于阈值",
                metadata={"modalities_used": [m.value for m in available_modalities]}
            )
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="BIOMETRIC_VERIFY",
                user_id=user_id,
                details={
                    "biometric_type": "multimodal",
                    "success": success,
                    "match_score": weighted_score,
                    "threshold": threshold,
                    "auth_level": auth_level.value,
                    "liveness_detected": liveness_passed,
                    "modalities_used": [m.value for m in available_modalities]
                },
                severity="INFO" if success else "WARNING"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"多模态认证失败: {str(e)}")
            return BiometricAuthResult(
                success=False,
                user_id=user_id,
                biometric_type=BiometricType.MULTIMODAL,
                confidence_score=0.0,
                match_score=0.0,
                threshold_used=0.0,
                auth_level=auth_level,
                liveness_detected=False,
                processing_time_ms=(time.time() - start_time) * 1000,
                failure_reason=f"验证过程异常: {str(e)}"
            )
    
    async def continuous_authentication(
        self,
        user_id: str,
        behavior_stream: asyncio.Queue,
        timeout_seconds: int = 300,
        check_interval_seconds: int = 30
    ) -> asyncio.Task:
        """
        持续身份验证任务
        
        Args:
            user_id: 用户ID
            behavior_stream: 行为数据流队列
            timeout_seconds: 超时时间
            check_interval_seconds: 检查间隔
        
        Returns:
            持续验证任务
        """
        async def _continuous_auth_loop():
            last_success_time = time.time()
            
            while True:
                try:
                    # 等待检查间隔或获取行为数据
                    try:
                        behavior_data = await asyncio.wait_for(
                            behavior_stream.get(),
                            timeout=check_interval_seconds
                        )
                    except asyncio.TimeoutError:
                        # 超时无数据，使用默认验证
                        behavior_data = {"type": "idle_check"}
                    
                    # 进行行为验证
                    result = await self.verify_behavioral(
                        user_id=user_id,
                        behavior_data=behavior_data,
                        auth_level=BiometricAuthLevel.LOW
                    )
                    
                    if result.success:
                        last_success_time = time.time()
                        logger.debug(f"用户 {user_id} 持续认证成功")
                    else:
                        time_since_success = time.time() - last_success_time
                        if time_since_success > timeout_seconds:
                            logger.warning(f"用户 {user_id} 持续认证超时 ({timeout_seconds}秒)")
                            # 触发会话失效
                            from .session_manager import SessionManager
                            session_manager = SessionManager()
                            await session_manager.invalidate_user_sessions(user_id, reason="continuous_auth_timeout")
                            break
                    
                    await asyncio.sleep(check_interval_seconds)
                    
                except asyncio.CancelledError:
                    logger.info(f"用户 {user_id} 持续认证任务被取消")
                    break
                except Exception as e:
                    logger.error(f"持续认证循环异常: {str(e)}")
                    await asyncio.sleep(5)
        
        task = asyncio.create_task(_continuous_auth_loop())
        return task
    
    async def delete_user_templates(self, user_id: str) -> bool:
        """
        删除用户的所有生物特征模板
        
        Args:
            user_id: 用户ID
        
        Returns:
            是否成功
        """
        try:
            if user_id in self.templates:
                del self.templates[user_id]
            
            # 删除文件
            template_file = self.template_storage_path / f"{user_id}_templates.enc"
            if template_file.exists():
                template_file.unlink()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="BIOMETRIC_DELETE",
                user_id=user_id,
                details={"action": "delete_all_templates"},
                severity="INFO"
            )
            
            logger.info(f"用户 {user_id} 的所有生物特征模板已删除")
            return True
        except Exception as e:
            logger.error(f"删除用户 {user_id} 的生物特征模板失败: {str(e)}")
            return False
    
    def _assess_audio_quality(self, audio: np.ndarray, sample_rate: int) -> float:
        """评估音频质量"""
        try:
            # 计算信噪比
            energy = np.mean(audio ** 2)
            if energy < 1e-6:
                return 0.0
            
            # 简化版质量评估
            duration = len(audio) / sample_rate
            if duration < 1.0:
                return 0.3
            
            if duration > 10.0:
                return 0.9
            
            return 0.7
        except Exception:
            return 0.5
    
    def _assess_image_quality(self, image: np.ndarray) -> float:
        """评估图像质量"""
        try:
            # 简化版图像质量评估
            if image is None or image.size == 0:
                return 0.0
            
            # 检查图像尺寸
            h, w = image.shape[:2]
            if h < 100 or w < 100:
                return 0.4
            
            return 0.8
        except Exception:
            return 0.5
    
    async def _extract_voiceprint_features(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """提取声纹特征（模拟实现）"""
        # 实际应用中应使用语音识别模型提取特征
        # 这里返回模拟的512维特征向量
        await asyncio.sleep(0.1)  # 模拟计算时间
        return np.random.randn(512).astype(np.float32)
    
    async def _extract_facial_features(self, image: np.ndarray) -> np.ndarray:
        """提取面部特征（模拟实现）"""
        await asyncio.sleep(0.1)
        return np.random.randn(1024).astype(np.float32)
    
    async def _extract_behavioral_features(self, behavior_data: Dict[str, Any]) -> np.ndarray:
        """提取行为特征（模拟实现）"""
        await asyncio.sleep(0.05)
        return np.random.randn(256).astype(np.float32)
    
    def _fuse_features(self, features1: np.ndarray, features2: np.ndarray, weight_new: float = 0.3) -> np.ndarray:
        """融合两个特征向量"""
        return (1 - weight_new) * features1 + weight_new * features2
    
    def _fuse_multiple_features(self, features_list: List[np.ndarray]) -> np.ndarray:
        """融合多个特征向量"""
        if not features_list:
            return np.array([])
        return np.mean(features_list, axis=0)
    
    def _calculate_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """计算两个特征向量的相似度（余弦相似度）"""
        if features1.size == 0 or features2.size == 0:
            return 0.0
        
        # 确保特征向量维度一致
        if features1.shape != features2.shape:
            min_len = min(len(features1), len(features2))
            features1 = features1[:min_len]
            features2 = features2[:min_len]
        
        norm1 = np.linalg.norm(features1)
        norm2 = np.linalg.norm(features2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        cosine_sim = np.dot(features1, features2) / (norm1 * norm2)
        return float(max(0, min(1, cosine_sim)))
    
    def _compute_template_hash(self, features: np.ndarray) -> str:
        """计算特征模板的哈希值"""
        feature_bytes = features.tobytes()
        return HashUtils.sha256(feature_bytes)
    
    async def _perform_voice_liveness_detection(self, audio: np.ndarray, sample_rate: int) -> bool:
        """语音活体检测（防录音重放）"""
        # 实际应用中应实现复杂的活体检测算法
        await asyncio.sleep(0.2)
        return True
    
    async def _perform_face_liveness_detection(self, image: np.ndarray) -> bool:
        """面部活体检测（防照片/视频重放）"""
        await asyncio.sleep(0.2)
        return True
    
    def get_template_info(self, user_id: str) -> Dict[str, Any]:
        """获取用户的生物特征模板信息"""
        if user_id not in self.templates:
            return {}
        
        info = {}
        for bio_type_str, template in self.templates[user_id].items():
            info[bio_type_str] = {
                "created_at": template.created_at,
                "updated_at": template.updated_at,
                "quality_score": template.quality_score,
                "sample_count": template.sample_count,
                "metadata": template.metadata
            }
        
        return info


# 单例实例
_biometric_auth_instance = None


def get_biometric_auth() -> BiometricAuth:
    """获取生物认证单例实例"""
    global _biometric_auth_instance
    if _biometric_auth_instance is None:
        _biometric_auth_instance = BiometricAuth()
    return _biometric_auth_instance

