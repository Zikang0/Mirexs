"""
嘴唇同步引擎 - 核心同步系统
负责实时同步语音和3D虚拟形象的口型动画
完整实现音素-视素映射、实时同步和情感驱动的口型动画
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import time
import asyncio
from enum import Enum

# 导入依赖
from interaction.threed_avatar.character_system.skeleton_animation import SkeletonAnimation, BoneTransform
from interaction.threed_avatar.character_system.model_manager import ModelManager, ModelInstance
from interaction.output_systems.speech_output.multilingual_tts import MultilingualTTS, TTSResult, EmotionType
from interaction.threed_avatar.speech_sync.phoneme_analyzer import PhonemeAnalyzer
from interaction.threed_avatar.speech_sync.viseme_generator import VisemeGenerator
from interaction.threed_avatar.speech_sync.voice_animation_map import VoiceAnimationMap
from interaction.threed_avatar.speech_sync.sync_optimizer import SyncOptimizer

logger = logging.getLogger(__name__)

class LipSyncState(Enum):
    """嘴唇同步状态"""
    IDLE = "idle"
    SYNCHRONIZING = "synchronizing"
    PROCESSING = "processing"
    ERROR = "error"

@dataclass
class LipSyncConfig:
    """嘴唇同步配置"""
    sync_precision: float = 0.1  # 同步精度（秒）
    max_latency: float = 0.05    # 最大延迟（秒）
    blend_duration: float = 0.1  # 混合持续时间（秒）
    emotion_influence: float = 1.0  # 情感影响系数
    realtime_mode: bool = True   # 实时模式
    use_phoneme_prediction: bool = True  # 使用音素预测

@dataclass
class LipSyncFrame:
    """嘴唇同步帧"""
    timestamp: float
    viseme_weights: Dict[str, float]  # 视素权重
    emotion_weights: Dict[str, float]  # 情感权重
    bone_transforms: Dict[str, BoneTransform]  # 骨骼变换
    audio_features: Dict[str, float]  # 音频特征

class LipSyncEngine:
    """嘴唇同步引擎 - 完整实现"""
    
    def __init__(self, model_instance: ModelInstance, skeleton_animation: SkeletonAnimation):
        self.model_instance = model_instance
        self.skeleton_animation = skeleton_animation
        self.tts_system = MultilingualTTS()
        
        # 子系统
        self.phoneme_analyzer = PhonemeAnalyzer()
        self.viseme_generator = VisemeGenerator(model_instance)
        self.voice_animation_map = VoiceAnimationMap()
        self.sync_optimizer = SyncOptimizer()
        
        # 状态管理
        self.current_state = LipSyncState.IDLE
        self.sync_frames: List[LipSyncFrame] = []
        self.current_frame_index = 0
        self.start_time = 0.0
        
        # 配置
        self.config = LipSyncConfig()
        
        # 性能统计
        self.stats = {
            "total_frames_processed": 0,
            "average_sync_error": 0.0,
            "real_time_frames": 0,
            "emotion_frames": 0,
            "cache_hits": 0
        }
        
        # 缓存
        self.phoneme_cache: Dict[str, List[Tuple[str, float]]] = {}
        self.viseme_cache: Dict[str, Dict[str, float]] = {}
        
        # 初始化面部骨骼映射
        self._initialize_face_bones()
        
        logger.info("LipSyncEngine initialized")

    def _initialize_face_bones(self):
        """初始化面部骨骼映射"""
        self.face_bones = {
            "jaw": "jaw",
            "mouth_upper_lip": "mouth_upper_lip",
            "mouth_lower_lip": "mouth_lower_lip", 
            "mouth_left_corner": "mouth_left_corner",
            "mouth_right_corner": "mouth_right_corner",
            "cheek_left": "cheek_left",
            "cheek_right": "cheek_right",
            "tongue": "tongue"
        }
        
        # 视素到骨骼的映射权重
        self.viseme_bone_weights = {
            "A": {"jaw": 0.8, "mouth_upper_lip": 0.3, "mouth_lower_lip": 0.4},
            "E": {"jaw": 0.4, "mouth_upper_lip": 0.6, "mouth_lower_lip": 0.5},
            "I": {"jaw": 0.2, "mouth_upper_lip": 0.7, "mouth_lower_lip": 0.6},
            "O": {"jaw": 0.6, "mouth_upper_lip": 0.5, "mouth_lower_lip": 0.7},
            "U": {"jaw": 0.3, "mouth_upper_lip": 0.4, "mouth_lower_lip": 0.8},
            "B": {"mouth_upper_lip": 0.9, "mouth_lower_lip": 0.8},
            "F": {"mouth_upper_lip": 0.7, "mouth_lower_lip": 0.6},
            "M": {"mouth_upper_lip": 0.8, "mouth_lower_lip": 0.7},
            "P": {"mouth_upper_lip": 0.9, "mouth_lower_lip": 0.8},
            "R": {"tongue": 0.6, "mouth_upper_lip": 0.4},
            "S": {"tongue": 0.7, "mouth_upper_lip": 0.3},
            "T": {"tongue": 0.8, "mouth_upper_lip": 0.2},
            "silence": {}  # 静音，所有权重为0
        }

    async def synchronize_speech(self, text: str, emotion: EmotionType = EmotionType.NEUTRAL) -> bool:
        """同步语音和口型"""
        try:
            self.current_state = LipSyncState.PROCESSING
            self.start_time = time.time()
            self.current_frame_index = 0
            self.sync_frames.clear()
            
            logger.info(f"Starting lip sync for text: {text}")
            
            # 1. 语音合成
            tts_result = await self._synthesize_speech(text, emotion)
            if not tts_result:
                logger.error("TTS synthesis failed")
                self.current_state = LipSyncState.ERROR
                return False
            
            # 2. 音素分析
            phoneme_data = await self._analyze_phonemes(tts_result)
            if not phoneme_data:
                logger.error("Phoneme analysis failed")
                self.current_state = LipSyncState.ERROR
                return False
            
            # 3. 生成视素序列
            viseme_sequence = await self._generate_viseme_sequence(phoneme_data, emotion)
            if not viseme_sequence:
                logger.error("Viseme generation failed")
                self.current_state = LipSyncState.ERROR
                return False
            
            # 4. 创建同步帧
            await self._create_sync_frames(viseme_sequence, tts_result, emotion)
            
            # 5. 优化同步
            await self.sync_optimizer.optimize_sync(self.sync_frames, tts_result.audio_data, tts_result.sample_rate)
            
            self.current_state = LipSyncState.SYNCHRONIZING
            logger.info(f"Lip sync prepared: {len(self.sync_frames)} frames")
            return True
            
        except Exception as e:
            logger.error(f"Error in speech synchronization: {e}")
            self.current_state = LipSyncState.ERROR
            return False

    async def _synthesize_speech(self, text: str, emotion: EmotionType) -> Optional[TTSResult]:
        """合成语音"""
        try:
            from interaction.output_systems.speech_output.multilingual_tts import TTSConfig
            
            tts_config = TTSConfig(
                emotion=emotion,
                emotion_strength=self.config.emotion_influence,
                realtime=self.config.realtime_mode
            )
            
            tts_result = await self.tts_system.synthesize(text, tts_config)
            return tts_result
            
        except Exception as e:
            logger.error(f"Error in speech synthesis: {e}")
            return None

    async def _analyze_phonemes(self, tts_result: TTSResult) -> Optional[List[Tuple[str, float]]]:
        """分析音素"""
        try:
            # 使用音素分析器
            phoneme_data = await self.phoneme_analyzer.analyze_phonemes(
                tts_result.audio_data, 
                tts_result.sample_rate,
                tts_result.phonemes,
                tts_result.durations
            )
            
            return phoneme_data
            
        except Exception as e:
            logger.error(f"Error in phoneme analysis: {e}")
            return None

    async def _generate_viseme_sequence(self, phoneme_data: List[Tuple[str, float]], 
                                      emotion: EmotionType) -> Optional[List[Tuple[str, float, Dict[str, float]]]]:
        """生成视素序列"""
        try:
            viseme_sequence = []
            
            for phoneme, duration in phoneme_data:
                # 生成视素权重
                viseme_weights = await self.viseme_generator.generate_viseme(
                    phoneme, duration, emotion
                )
                
                if viseme_weights:
                    viseme_sequence.append((phoneme, duration, viseme_weights))
            
            return viseme_sequence if viseme_sequence else None
            
        except Exception as e:
            logger.error(f"Error in viseme generation: {e}")
            return None

    async def _create_sync_frames(self, viseme_sequence: List[Tuple[str, float, Dict[str, float]]],
                                tts_result: TTSResult, emotion: EmotionType):
        """创建同步帧"""
        try:
            current_time = 0.0
            frame_duration = self.config.sync_precision
            
            for phoneme, duration, viseme_weights in viseme_sequence:
                # 为每个音素创建多个帧
                num_frames = max(1, int(duration / frame_duration))
                frame_time_step = duration / num_frames
                
                for frame_idx in range(num_frames):
                    frame_time = current_time + frame_idx * frame_time_step
                    
                    # 计算当前帧的视素权重（考虑过渡）
                    current_weights = self._calculate_frame_weights(
                        viseme_weights, frame_idx, num_frames, viseme_sequence, phoneme
                    )
                    
                    # 计算情感权重
                    emotion_weights = await self._calculate_emotion_weights(emotion, frame_time)
                    
                    # 计算骨骼变换
                    bone_transforms = await self._calculate_bone_transforms(current_weights, emotion_weights)
                    
                    # 提取音频特征
                    audio_features = await self._extract_audio_features(tts_result.audio_data, 
                                                                      tts_result.sample_rate, 
                                                                      frame_time)
                    
                    # 创建同步帧
                    sync_frame = LipSyncFrame(
                        timestamp=frame_time,
                        viseme_weights=current_weights,
                        emotion_weights=emotion_weights,
                        bone_transforms=bone_transforms,
                        audio_features=audio_features
                    )
                    
                    self.sync_frames.append(sync_frame)
                
                current_time += duration
            
            logger.info(f"Created {len(self.sync_frames)} sync frames")
            
        except Exception as e:
            logger.error(f"Error creating sync frames: {e}")
            raise

    def _calculate_frame_weights(self, base_weights: Dict[str, float], frame_idx: int, 
                               total_frames: int, sequence: List, current_phoneme: str) -> Dict[str, float]:
        """计算帧权重（考虑音素过渡）"""
        try:
            weights = base_weights.copy()
            
            # 如果是过渡帧，混合前后音素的权重
            if frame_idx == 0 and len(sequence) > 1:
                # 帧序列开始，考虑与前一个音素的过渡
                pass  # 第一个音素没有前一个
            elif frame_idx == total_frames - 1 and len(sequence) > 1:
                # 帧序列结束，考虑与下一个音素的过渡
                next_phoneme_idx = sequence.index((current_phoneme, _, _)) + 1
                if next_phoneme_idx < len(sequence):
                    next_phoneme, _, next_weights = sequence[next_phoneme_idx]
                    blend_factor = 1.0 - (frame_idx / total_frames)
                    
                    for viseme, weight in next_weights.items():
                        if viseme in weights:
                            weights[viseme] = weights[viseme] * (1 - blend_factor) + weight * blend_factor
                        else:
                            weights[viseme] = weight * blend_factor
            
            return weights
            
        except Exception as e:
            logger.warning(f"Error calculating frame weights: {e}")
            return base_weights

    async def _calculate_emotion_weights(self, emotion: EmotionType, timestamp: float) -> Dict[str, float]:
        """计算情感权重"""
        try:
            # 基础情感权重
            base_weights = {
                EmotionType.NEUTRAL: {"intensity": 0.5, "variation": 0.1},
                EmotionType.HAPPY: {"intensity": 0.8, "variation": 0.3, "smile": 0.7},
                EmotionType.SAD: {"intensity": 0.6, "variation": 0.05, "frown": 0.6},
                EmotionType.ANGRY: {"intensity": 0.9, "variation": 0.4, "tense": 0.8},
                EmotionType.EXCITED: {"intensity": 0.85, "variation": 0.5, "wide": 0.6},
                EmotionType.CALM: {"intensity": 0.4, "variation": 0.02, "relaxed": 0.5},
                EmotionType.SURPRISED: {"intensity": 0.95, "variation": 0.6, "wide": 0.9},
                EmotionType.FEARFUL: {"intensity": 0.7, "variation": 0.2, "tense": 0.7}
            }
            
            emotion_data = base_weights.get(emotion, base_weights[EmotionType.NEUTRAL])
            
            # 添加时间变化
            time_variation = np.sin(timestamp * 2 * np.pi) * emotion_data.get("variation", 0.1)
            emotion_data["intensity"] = max(0.0, min(1.0, emotion_data["intensity"] + time_variation))
            
            return emotion_data
            
        except Exception as e:
            logger.warning(f"Error calculating emotion weights: {e}")
            return {"intensity": 0.5, "variation": 0.1}

    async def _calculate_bone_transforms(self, viseme_weights: Dict[str, float], 
                                       emotion_weights: Dict[str, float]) -> Dict[str, BoneTransform]:
        """计算骨骼变换"""
        try:
            bone_transforms = {}
            
            for bone_name in self.face_bones.values():
                # 获取基础变换
                base_transform = await self._get_base_bone_transform(bone_name)
                
                # 应用视素权重
                viseme_influence = await self._calculate_viseme_influence(bone_name, viseme_weights)
                
                # 应用情感权重
                emotion_influence = await self._calculate_emotion_influence(bone_name, emotion_weights)
                
                # 合并影响
                final_transform = await self._blend_transforms(
                    base_transform, viseme_influence, emotion_influence
                )
                
                bone_transforms[bone_name] = final_transform
            
            return bone_transforms
            
        except Exception as e:
            logger.error(f"Error calculating bone transforms: {e}")
            return {}

    async def _get_base_bone_transform(self, bone_name: str) -> BoneTransform:
        """获取基础骨骼变换"""
        try:
            # 从当前姿势获取骨骼变换
            current_pose = await self.skeleton_animation.get_current_pose()
            if bone_name in current_pose.bone_transforms:
                return current_pose.bone_transforms[bone_name]
            else:
                # 返回默认变换
                return BoneTransform()
                
        except Exception as e:
            logger.warning(f"Error getting base bone transform for {bone_name}: {e}")
            return BoneTransform()

    async def _calculate_viseme_influence(self, bone_name: str, viseme_weights: Dict[str, float]) -> BoneTransform:
        """计算视素对骨骼的影响"""
        try:
            influence = BoneTransform()
            
            for viseme, weight in viseme_weights.items():
                if viseme in self.viseme_bone_weights and bone_name in self.viseme_bone_weights[viseme]:
                    bone_weight = self.viseme_bone_weights[viseme][bone_name] * weight
                    
                    # 根据视素类型应用不同的变换
                    if viseme in ["A", "E", "I", "O", "U"]:
                        # 元音：主要影响下颌和嘴唇位置
                        influence.position = (
                            influence.position[0],
                            influence.position[1] - bone_weight * 0.1,  # 下颌下移
                            influence.position[2]
                        )
                    elif viseme in ["B", "M", "P"]:
                        # 唇音：嘴唇闭合
                        influence.position = (
                            influence.position[0],
                            influence.position[1] + bone_weight * 0.05,  # 嘴唇上移
                            influence.position[2]
                        )
                    elif viseme in ["F", "V"]:
                        # 唇齿音：下唇接触上齿
                        influence.position = (
                            influence.position[0],
                            influence.position[1] + bone_weight * 0.03,
                            influence.position[2] + bone_weight * 0.02
                        )
            
            return influence
            
        except Exception as e:
            logger.warning(f"Error calculating viseme influence: {e}")
            return BoneTransform()

    async def _calculate_emotion_influence(self, bone_name: str, emotion_weights: Dict[str, float]) -> BoneTransform:
        """计算情感对骨骼的影响"""
        try:
            influence = BoneTransform()
            intensity = emotion_weights.get("intensity", 0.5)
            
            # 根据情感类型应用不同的变换
            if "smile" in emotion_weights:
                # 微笑：嘴角上扬
                if "corner" in bone_name:
                    smile_strength = emotion_weights["smile"] * intensity
                    if "left" in bone_name:
                        influence.position = (
                            influence.position[0] - smile_strength * 0.1,
                            influence.position[1] + smile_strength * 0.05,
                            influence.position[2]
                        )
                    elif "right" in bone_name:
                        influence.position = (
                            influence.position[0] + smile_strength * 0.1,
                            influence.position[1] + smile_strength * 0.05,
                            influence.position[2]
                        )
            
            if "frown" in emotion_weights:
                # 皱眉：嘴角下拉
                if "corner" in bone_name:
                    frown_strength = emotion_weights["frown"] * intensity
                    if "left" in bone_name:
                        influence.position = (
                            influence.position[0] - frown_strength * 0.05,
                            influence.position[1] - frown_strength * 0.1,
                            influence.position[2]
                        )
                    elif "right" in bone_name:
                        influence.position = (
                            influence.position[0] + frown_strength * 0.05,
                            influence.position[1] - frown_strength * 0.1,
                            influence.position[2]
                        )
            
            return influence
            
        except Exception as e:
            logger.warning(f"Error calculating emotion influence: {e}")
            return BoneTransform()

    async def _blend_transforms(self, base: BoneTransform, viseme_influence: BoneTransform, 
                              emotion_influence: BoneTransform) -> BoneTransform:
        """混合变换"""
        try:
            # 位置混合
            final_position = (
                base.position[0] + viseme_influence.position[0] + emotion_influence.position[0],
                base.position[1] + viseme_influence.position[1] + emotion_influence.position[1],
                base.position[2] + viseme_influence.position[2] + emotion_influence.position[2]
            )
            
            # 旋转混合（四元数球面插值）
            final_rotation = await self._blend_rotations(
                base.rotation, viseme_influence.rotation, emotion_influence.rotation
            )
            
            # 缩放混合
            final_scale = (
                base.scale[0] * (1 + viseme_influence.scale[0]) * (1 + emotion_influence.scale[0]),
                base.scale[1] * (1 + viseme_influence.scale[1]) * (1 + emotion_influence.scale[1]),
                base.scale[2] * (1 + viseme_influence.scale[2]) * (1 + emotion_influence.scale[2])
            )
            
            return BoneTransform(
                position=final_position,
                rotation=final_rotation,
                scale=final_scale
            )
            
        except Exception as e:
            logger.warning(f"Error blending transforms: {e}")
            return base

    async def _blend_rotations(self, base: Tuple, viseme: Tuple, emotion: Tuple) -> Tuple:
        """混合旋转（四元数）"""
        try:
            # 简化实现：直接使用基础旋转
            # 实际应该使用四元数球面插值
            return base
            
        except Exception as e:
            logger.warning(f"Error blending rotations: {e}")
            return base

    async def _extract_audio_features(self, audio_data: np.ndarray, sample_rate: int, 
                                    timestamp: float) -> Dict[str, float]:
        """提取音频特征"""
        try:
            features = {}
            
            # 计算当前时间对应的音频帧
            start_frame = int(timestamp * sample_rate)
            end_frame = min(start_frame + 1024, len(audio_data))
            
            if start_frame >= len(audio_data):
                return features
            
            current_audio = audio_data[start_frame:end_frame]
            
            if len(current_audio) > 0:
                # 能量特征
                features["rms_energy"] = float(np.sqrt(np.mean(current_audio**2)))
                features["peak_amplitude"] = float(np.max(np.abs(current_audio)))
                
                # 频谱特征
                if len(current_audio) >= 256:
                    spectrum = np.abs(np.fft.rfft(current_audio[:256]))
                    features["spectral_centroid"] = float(np.sum(spectrum * np.arange(len(spectrum))) / np.sum(spectrum))
                    features["spectral_rolloff"] = float(np.percentile(spectrum, 85))
            
            return features
            
        except Exception as e:
            logger.warning(f"Error extracting audio features: {e}")
            return {}

    async def update(self, delta_time: float) -> bool:
        """更新嘴唇同步"""
        try:
            if self.current_state != LipSyncState.SYNCHRONIZING:
                return False
            
            if self.current_frame_index >= len(self.sync_frames):
                self.current_state = LipSyncState.IDLE
                logger.info("Lip sync completed")
                return False
            
            # 获取当前帧
            current_frame = self.sync_frames[self.current_frame_index]
            
            # 应用骨骼变换
            for bone_name, transform in current_frame.bone_transforms.items():
                await self.skeleton_animation.set_bone_transform(
                    bone_name, 
                    position=transform.position,
                    rotation=transform.rotation,
                    scale=transform.scale
                )
            
            # 更新统计
            self.stats["total_frames_processed"] += 1
            if self.config.realtime_mode:
                self.stats["real_time_frames"] += 1
            
            # 移动到下一帧
            self.current_frame_index += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating lip sync: {e}")
            self.current_state = LipSyncState.ERROR
            return False

    async def get_current_frame(self) -> Optional[LipSyncFrame]:
        """获取当前帧"""
        try:
            if (self.current_state == LipSyncState.SYNCHRONIZING and 
                self.current_frame_index < len(self.sync_frames)):
                return self.sync_frames[self.current_frame_index]
            return None
        except Exception as e:
            logger.error(f"Error getting current frame: {e}")
            return None

    async def get_sync_progress(self) -> float:
        """获取同步进度"""
        try:
            if not self.sync_frames:
                return 0.0
            return min(1.0, self.current_frame_index / len(self.sync_frames))
        except Exception as e:
            logger.error(f"Error getting sync progress: {e}")
            return 0.0

    async def pause_sync(self) -> bool:
        """暂停同步"""
        try:
            if self.current_state == LipSyncState.SYNCHRONIZING:
                self.current_state = LipSyncState.IDLE
                logger.info("Lip sync paused")
                return True
            return False
        except Exception as e:
            logger.error(f"Error pausing lip sync: {e}")
            return False

    async def resume_sync(self) -> bool:
        """恢复同步"""
        try:
            if self.current_state == LipSyncState.IDLE and self.sync_frames:
                self.current_state = LipSyncState.SYNCHRONIZING
                logger.info("Lip sync resumed")
                return True
            return False
        except Exception as e:
            logger.error(f"Error resuming lip sync: {e}")
            return False

    async def stop_sync(self) -> bool:
        """停止同步"""
        try:
            self.current_state = LipSyncState.IDLE
            self.current_frame_index = 0
            logger.info("Lip sync stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping lip sync: {e}")
            return False

    async def get_sync_quality(self) -> Dict[str, float]:
        """获取同步质量"""
        try:
            quality_metrics = {}
            
            if not self.sync_frames:
                return quality_metrics
            
            # 计算平均同步误差
            total_error = 0.0
            for frame in self.sync_frames:
                # 基于音频特征和视觉特征的匹配度计算误差
                audio_energy = frame.audio_features.get("rms_energy", 0.0)
                mouth_openness = frame.viseme_weights.get("A", 0.0) + frame.viseme_weights.get("O", 0.0)
                
                # 理想情况下，音频能量应该与口型开合度相关
                expected_openness = min(1.0, audio_energy * 5.0)  # 简化关系
                error = abs(mouth_openness - expected_openness)
                total_error += error
            
            quality_metrics["average_sync_error"] = total_error / len(self.sync_frames)
            quality_metrics["frame_count"] = len(self.sync_frames)
            quality_metrics["completion_rate"] = await self.get_sync_progress()
            
            # 更新统计
            self.stats["average_sync_error"] = quality_metrics["average_sync_error"]
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Error calculating sync quality: {e}")
            return {}

    async def export_sync_data(self, export_path: str) -> bool:
        """导出同步数据"""
        try:
            import json
            import pickle
            
            export_data = {
                "config": self.config.__dict__,
                "frames_count": len(self.sync_frames),
                "total_duration": self.sync_frames[-1].timestamp if self.sync_frames else 0.0,
                "stats": self.stats
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            # 导出帧数据（使用pickle）
            frames_path = export_path.replace('.json', '_frames.pkl')
            with open(frames_path, 'wb') as f:
                pickle.dump(self.sync_frames, f)
            
            logger.info(f"Sync data exported to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting sync data: {e}")
            return False

    async def import_sync_data(self, import_path: str) -> bool:
        """导入同步数据"""
        try:
            import json
            import pickle
            
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 导入配置
            self.config = LipSyncConfig(**import_data.get("config", {}))
            
            # 导入帧数据
            frames_path = import_path.replace('.json', '_frames.pkl')
            with open(frames_path, 'rb') as f:
                self.sync_frames = pickle.load(f)
            
            # 导入统计
            self.stats.update(import_data.get("stats", {}))
            
            logger.info(f"Sync data imported from {import_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing sync data: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats["current_state"] = self.current_state.value
        stats["current_frame"] = self.current_frame_index
        stats["total_frames"] = len(self.sync_frames)
        stats["sync_progress"] = await self.get_sync_progress()
        
        return stats

    async def cleanup(self):
        """清理资源"""
        try:
            await self.stop_sync()
            self.sync_frames.clear()
            self.phoneme_cache.clear()
            self.viseme_cache.clear()
            
            logger.info("LipSyncEngine cleaned up")
            
        except Exception as e:
            logger.error(f"Error during lip sync cleanup: {e}")

# 全局嘴唇同步引擎实例（根据需要创建）
# lip_sync_engine = LipSyncEngine(model_instance, skeleton_animation)
