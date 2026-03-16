# cognitive/learning/skill_acquisition.py
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import json
import os
from datetime import datetime
import logging
from collections import defaultdict

class SkillRepresentation(nn.Module):
    """技能表示网络"""
    
    def __init__(self, input_dim: int = 768, skill_dim: int = 256):
        super(SkillRepresentation, self).__init__()
        self.input_dim = input_dim
        self.skill_dim = skill_dim
        
        # 技能编码器
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, 384),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(384, skill_dim),
            nn.Tanh()
        )
        
        # 技能解码器
        self.decoder = nn.Sequential(
            nn.Linear(skill_dim, 384),
            nn.ReLU(),
            nn.Linear(384, 512),
            nn.ReLU(),
            nn.Linear(512, input_dim)
        )
        
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        
        return {
            'encoded_skill': encoded,
            'reconstructed_input': decoded,
            'skill_norm': torch.norm(encoded, dim=-1)
        }

class SkillAcquisitionSystem:
    """技能获取系统：从交互中学习新技能"""
    
    def __init__(self, skills_dir: str = "data/skills"):
        self.skills_dir = skills_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = self._setup_logger()
        
        # 初始化技能模型
        self.skill_model = SkillRepresentation().to(self.device)
        self.optimizer = torch.optim.Adam(self.skill_model.parameters(), lr=0.0001)
        self.reconstruction_criterion = nn.MSELoss()
        
        # 技能库
        self.skill_library: Dict[str, Dict] = {}
        self.skill_embeddings: Dict[str, np.ndarray] = {}
        self.skill_usage_stats: Dict[str, Dict] = defaultdict(lambda: {
            'usage_count': 0,
            'success_rate': 0.0,
            'last_used': None,
            'performance_history': []
        })
        
        # 加载现有技能
        self._load_skills()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('skill_acquisition')
        if not logger.handlers:
            handler = logging.FileHandler('logs/skill_acquisition.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _load_skills(self):
        """加载已学习的技能"""
        skills_file = os.path.join(self.skills_dir, "skill_library.json")
        embeddings_file = os.path.join(self.skills_dir, "skill_embeddings.npy")
        stats_file = os.path.join(self.skills_dir, "skill_stats.json")
        
        try:
            if os.path.exists(skills_file):
                with open(skills_file, 'r', encoding='utf-8') as f:
                    self.skill_library = json.load(f)
            
            if os.path.exists(embeddings_file):
                self.skill_embeddings = np.load(embeddings_file, allow_pickle=True).item()
            
            if os.path.exists(stats_file):
                with open(stats_file, 'r', encoding='utf-8') as f:
                    loaded_stats = json.load(f)
                    self.skill_usage_stats.update(loaded_stats)
            
            self.logger.info(f"技能库加载成功，共{len(self.skill_library)}个技能")
            
        except Exception as e:
            self.logger.error(f"加载技能库失败: {e}")
    
    def save_skills(self):
        """保存技能库"""
        os.makedirs(self.skills_dir, exist_ok=True)
        
        try:
            # 保存技能库
            skills_file = os.path.join(self.skills_dir, "skill_library.json")
            with open(skills_file, 'w', encoding='utf-8') as f:
                json.dump(self.skill_library, f, ensure_ascii=False, indent=2)
            
            # 保存技能嵌入
            embeddings_file = os.path.join(self.skills_dir, "skill_embeddings.npy")
            np.save(embeddings_file, self.skill_embeddings)
            
            # 保存使用统计
            stats_file = os.path.join(self.skills_dir, "skill_stats.json")
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(dict(self.skill_usage_stats), f, ensure_ascii=False, indent=2)
            
            self.logger.info("技能库保存成功")
            
        except Exception as e:
            self.logger.error(f"保存技能库失败: {e}")
    
    def learn_new_skill(self, interaction_data: Dict[str, Any]) -> str:
        """
        从交互中学习新技能
        
        Args:
            interaction_data: 交互数据，包含动作序列、结果、上下文等信息
            
        Returns:
            新技能的ID
        """
        try:
            # 提取技能特征
            skill_features = self._extract_skill_features(interaction_data)
            skill_tensor = torch.FloatTensor(skill_features).unsqueeze(0).to(self.device)
            
            # 获取技能表示
            self.skill_model.eval()
            with torch.no_grad():
                skill_representation = self.skill_model(skill_tensor)
            
            # 生成技能ID和元数据
            skill_id = self._generate_skill_id(interaction_data)
            skill_metadata = self._create_skill_metadata(interaction_data, skill_representation)
            
            # 添加到技能库
            self.skill_library[skill_id] = skill_metadata
            self.skill_embeddings[skill_id] = skill_representation['encoded_skill'][0].cpu().numpy()
            
            # 初始化使用统计
            self.skill_usage_stats[skill_id] = {
                'usage_count': 0,
                'success_rate': 0.0,
                'last_used': None,
                'performance_history': []
            }
            
            # 微调技能模型
            self._fine_tune_model(skill_tensor)
            
            self.logger.info(f"新技能学习完成: {skill_id}")
            return skill_id
            
        except Exception as e:
            self.logger.error(f"学习新技能失败: {e}")
            return f"error_skill_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _extract_skill_features(self, interaction_data: Dict[str, Any]) -> List[float]:
        """从交互数据中提取技能特征"""
        features = []
        
        # 动作序列特征
        action_sequence = interaction_data.get('actions', [])
        features.append(len(action_sequence))  # 动作数量
        
        # 动作类型分布
        action_types = [action.get('type', 'unknown') for action in action_sequence]
        unique_types = set(action_types)
        features.append(len(unique_types))  # 动作类型多样性
        
        # 结果特征
        result = interaction_data.get('result', {})
        features.append(result.get('success', 0.0))
        features.append(result.get('efficiency', 0.0))
        features.append(result.get('quality', 0.0))
        
        # 上下文特征
        context = interaction_data.get('context', {})
        features.append(context.get('complexity', 0.5))
        features.append(context.get('novelty', 0.5))
        
        # 时间特征
        duration = interaction_data.get('duration', 0.0)
        features.append(min(duration, 3600) / 3600)  # 归一化到小时
        
        # 填充到固定维度
        while len(features) < 768:
            features.append(0.0)
        features = features[:768]
        
        return features
    
    def _generate_skill_id(self, interaction_data: Dict[str, Any]) -> str:
        """生成技能ID"""
        task_type = interaction_data.get('task_type', 'general')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        features_hash = hash(str(interaction_data.get('actions', []))[:100])
        
        return f"{task_type}_{timestamp}_{abs(features_hash) % 10000:04d}"
    
    def _create_skill_metadata(self, interaction_data: Dict[str, Any], 
                             skill_representation: Dict[str, torch.Tensor]) -> Dict[str, Any]:
        """创建技能元数据"""
        return {
            'task_type': interaction_data.get('task_type', 'general'),
            'description': self._generate_skill_description(interaction_data),
            'prerequisites': interaction_data.get('prerequisites', []),
            'action_sequence': interaction_data.get('actions', []),
            'expected_outcomes': interaction_data.get('expected_outcomes', []),
            'difficulty_level': interaction_data.get('difficulty', 0.5),
            'learning_timestamp': datetime.now().isoformat(),
            'skill_norm': float(skill_representation['skill_norm'][0]),
            'applicability_score': self._calculate_applicability(interaction_data)
        }
    
    def _generate_skill_description(self, interaction_data: Dict[str, Any]) -> str:
        """生成技能描述"""
        task_type = interaction_data.get('task_type', '任务')
        actions = interaction_data.get('actions', [])
        action_types = [action.get('type', '操作') for action in actions[:3]]
        
        if action_types:
            return f"{task_type}技能，包含{', '.join(action_types)}等操作"
        else:
            return f"{task_type}相关技能"
    
    def _calculate_applicability(self, interaction_data: Dict[str, Any]) -> float:
        """计算技能适用性评分"""
        score = 0.0
        
        # 基于任务复杂度
        complexity = interaction_data.get('context', {}).get('complexity', 0.5)
        score += complexity * 0.3
        
        # 基于结果质量
        result = interaction_data.get('result', {})
        score += result.get('quality', 0.0) * 0.4
        
        # 基于效率
        score += result.get('efficiency', 0.0) * 0.3
        
        return min(score, 1.0)
    
    def _fine_tune_model(self, skill_tensor: torch.Tensor):
        """微调技能模型"""
        try:
            self.skill_model.train()
            self.optimizer.zero_grad()
            
            outputs = self.skill_model(skill_tensor)
            loss = self.reconstruction_criterion(outputs['reconstructed_input'], skill_tensor)
            
            loss.backward()
            self.optimizer.step()
            
            self.logger.debug(f"技能模型微调完成，重建损失: {loss.item():.4f}")
            
        except Exception as e:
            self.logger.error(f"技能模型微调失败: {e}")
    
    def retrieve_relevant_skills(self, task_context: Dict[str, Any], 
                               top_k: int = 5) -> List[Tuple[str, float]]:
        """
        检索相关技能
        
        Args:
            task_context: 任务上下文
            top_k: 返回的技能数量
            
        Returns:
            相关技能列表（技能ID, 相似度评分）
        """
        try:
            if not self.skill_embeddings:
                return []
            
            # 提取任务特征
            task_features = self._extract_skill_features({
                'actions': task_context.get('required_actions', []),
                'result': {'success': 0.5, 'efficiency': 0.5, 'quality': 0.5},
                'context': task_context,
                'task_type': task_context.get('task_type', 'general')
            })
            
            task_embedding = torch.FloatTensor(task_features).to(self.device)
            
            # 计算相似度
            similarities = []
            for skill_id, skill_embedding in self.skill_embeddings.items():
                skill_tensor = torch.FloatTensor(skill_embedding).to(self.device)
                similarity = torch.cosine_similarity(task_embedding, skill_tensor, dim=0)
                
                # 考虑使用频率和成功率
                stats = self.skill_usage_stats[skill_id]
                usage_boost = min(stats['usage_count'] * 0.01, 0.2)  # 使用频率加成
                success_boost = stats['success_rate'] * 0.3  # 成功率加成
                
                adjusted_similarity = float(similarity) * (1.0 + usage_boost + success_boost)
                similarities.append((skill_id, adjusted_similarity))
            
            # 按相似度排序并返回前k个
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            self.logger.error(f"检索相关技能失败: {e}")
            return []
    
    def update_skill_usage(self, skill_id: str, success: bool, performance_metrics: Dict[str, float]):
        """
        更新技能使用统计
        
        Args:
            skill_id: 技能ID
            success: 是否成功
            performance_metrics: 性能指标
        """
        if skill_id not in self.skill_usage_stats:
            self.logger.warning(f"未知技能ID: {skill_id}")
            return
        
        stats = self.skill_usage_stats[skill_id]
        stats['usage_count'] += 1
        stats['last_used'] = datetime.now().isoformat()
        
        # 更新成功率
        current_success_rate = stats['success_rate']
        new_success = 1.0 if success else 0.0
        stats['success_rate'] = (current_success_rate * (stats['usage_count'] - 1) + new_success) / stats['usage_count']
        
        # 记录性能历史
        performance_score = performance_metrics.get('overall_score', 
                          (performance_metrics.get('efficiency', 0.0) + 
                           performance_metrics.get('quality', 0.0)) / 2)
        stats['performance_history'].append({
            'timestamp': datetime.now().isoformat(),
            'score': performance_score,
            'success': success,
            'metrics': performance_metrics
        })
        
        # 限制历史记录长度
        if len(stats['performance_history']) > 100:
            stats['performance_history'] = stats['performance_history'][-50:]
        
        self.logger.info(f"技能 {skill_id} 使用统计已更新，成功率: {stats['success_rate']:.3f}")
    
    def get_skill_proficiency(self, skill_id: str) -> Dict[str, Any]:
        """获取技能熟练度评估"""
        if skill_id not in self.skill_usage_stats:
            return {'proficiency': 0.0, 'confidence': 0.0, 'assessment': 'unknown'}
        
        stats = self.skill_usage_stats[skill_id]
        
        # 计算熟练度
        base_proficiency = stats['success_rate']
        usage_confidence = min(stats['usage_count'] / 10.0, 1.0)  # 使用次数带来的置信度
        
        # 考虑性能趋势
        performance_history = stats['performance_history']
        if len(performance_history) >= 3:
            recent_scores = [entry['score'] for entry in performance_history[-3:]]
            trend = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
            trend_boost = trend * 0.2  # 趋势对熟练度的影响
        else:
            trend_boost = 0.0
        
        proficiency = min(base_proficiency + trend_boost, 1.0)
        
        # 熟练度等级评估
        if proficiency >= 0.9:
            assessment = 'expert'
        elif proficiency >= 0.7:
            assessment = 'proficient'
        elif proficiency >= 0.5:
            assessment = 'competent'
        elif proficiency >= 0.3:
            assessment = 'beginner'
        else:
            assessment = 'novice'
        
        return {
            'proficiency': proficiency,
            'confidence': usage_confidence,
            'assessment': assessment,
            'usage_count': stats['usage_count'],
            'last_used': stats['last_used']
        }
    
    def transfer_skill_knowledge(self, source_skill_id: str, target_context: Dict[str, Any]) -> Optional[str]:
        """
        迁移技能知识到新上下文
        
        Args:
            source_skill_id: 源技能ID
            target_context: 目标上下文
            
        Returns:
            新技能ID(如果迁移成功)
        """
        try:
            if source_skill_id not in self.skill_library:
                self.logger.warning(f"源技能不存在: {source_skill_id}")
                return None
            
            source_skill = self.skill_library[source_skill_id]
            source_embedding = self.skill_embeddings[source_skill_id]
            
            # 创建迁移后的技能
            transferred_skill = source_skill.copy()
            transferred_skill['task_type'] = target_context.get('task_type', 'transferred')
            transferred_skill['description'] = f"从{source_skill['task_type']}迁移的技能"
            transferred_skill['is_transferred'] = True
            transferred_skill['source_skill'] = source_skill_id
            transferred_skill['transfer_timestamp'] = datetime.now().isoformat()
            
            # 调整技能嵌入
            target_features = self._extract_skill_features({
                'actions': target_context.get('required_actions', []),
                'context': target_context,
                'task_type': target_context.get('task_type', 'general')
            })
            
            # 混合源技能嵌入和目标特征
            transfer_ratio = 0.7  # 源技能的权重
            mixed_embedding = (source_embedding * transfer_ratio + 
                             np.array(target_features)[:256] * (1 - transfer_ratio))
            
            # 生成新技能ID
            new_skill_id = f"transferred_{source_skill_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 添加到技能库
            self.skill_library[new_skill_id] = transferred_skill
            self.skill_embeddings[new_skill_id] = mixed_embedding
            
            # 初始化使用统计
            self.skill_usage_stats[new_skill_id] = {
                'usage_count': 0,
                'success_rate': 0.0,
                'last_used': None,
                'performance_history': []
            }
            
            self.logger.info(f"技能知识迁移完成: {source_skill_id} -> {new_skill_id}")
            return new_skill_id
            
        except Exception as e:
            self.logger.error(f"技能知识迁移失败: {e}")
            return None
    
    def get_skill_library_overview(self) -> Dict[str, Any]:
        """获取技能库概览"""
        total_skills = len(self.skill_library)
        skill_types = defaultdict(int)
        proficiency_levels = defaultdict(int)
        
        for skill_id, skill_data in self.skill_library.items():
            skill_type = skill_data.get('task_type', 'unknown')
            skill_types[skill_type] += 1
            
            proficiency = self.get_skill_proficiency(skill_id)
            proficiency_levels[proficiency['assessment']] += 1
        
        return {
            'total_skills': total_skills,
            'skill_type_distribution': dict(skill_types),
            'proficiency_distribution': dict(proficiency_levels),
            'most_used_skills': self._get_most_used_skills(5),
            'recently_acquired_skills': self._get_recent_skills(5)
        }
    
    def _get_most_used_skills(self, top_n: int) -> List[Dict[str, Any]]:
        """获取最常使用的技能"""
        sorted_skills = sorted(self.skill_usage_stats.items(), 
                             key=lambda x: x[1]['usage_count'], reverse=True)
        
        result = []
        for skill_id, stats in sorted_skills[:top_n]:
            skill_info = self.skill_library.get(skill_id, {})
            result.append({
                'skill_id': skill_id,
                'description': skill_info.get('description', '未知技能'),
                'usage_count': stats['usage_count'],
                'success_rate': stats['success_rate']
            })
        
        return result
    
    def _get_recent_skills(self, top_n: int) -> List[Dict[str, Any]]:
        """获取最近学习的技能"""
        skills_with_timestamps = []
        for skill_id, skill_data in self.skill_library.items():
            timestamp = skill_data.get('learning_timestamp')
            if timestamp:
                skills_with_timestamps.append((skill_id, timestamp))
        
        # 按时间戳排序（最近的在前）
        skills_with_timestamps.sort(key=lambda x: x[1], reverse=True)
        
        result = []
        for skill_id, timestamp in skills_with_timestamps[:top_n]:
            skill_data = self.skill_library[skill_id]
            result.append({
                'skill_id': skill_id,
                'description': skill_data.get('description', '未知技能'),
                'task_type': skill_data.get('task_type', 'unknown'),
                'learned_at': timestamp
            })
        
        return result

# 全局技能获取系统实例
_global_skill_acquisition: Optional[SkillAcquisitionSystem] = None

def get_skill_acquisition_system() -> SkillAcquisitionSystem:
    """获取全局技能获取系统实例"""
    global _global_skill_acquisition
    if _global_skill_acquisition is None:
        _global_skill_acquisition = SkillAcquisitionSystem()
    return _global_skill_acquisition

