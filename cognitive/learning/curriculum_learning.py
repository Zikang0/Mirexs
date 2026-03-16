# cognitive/learning/curriculum_learning.py
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import json
import os
from datetime import datetime
import logging
from collections import defaultdict, deque
import heapq

class CurriculumItem:
    """课程项目"""
    
    def __init__(self, item_id: str, difficulty: float, content: Dict[str, Any],
                 prerequisites: List[str] = None, learning_objectives: List[str] = None):
        self.item_id = item_id
        self.difficulty = difficulty
        self.content = content
        self.prerequisites = prerequisites or []
        self.learning_objectives = learning_objectives or []
        
        # 学习统计
        self.attempts = 0
        self.successes = 0
        self.avg_performance = 0.0
        self.last_attempted = None
        self.completion_time = None
        
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.attempts == 0:
            return 0.0
        return self.successes / self.attempts
    
    @property
    def mastery_level(self) -> float:
        """计算掌握程度"""
        success_weight = self.success_rate * 0.6
        performance_weight = self.avg_performance * 0.4
        return success_weight + performance_weight
    
    def record_attempt(self, success: bool, performance: float, completion_time: float):
        """记录学习尝试"""
        self.attempts += 1
        if success:
            self.successes += 1
        
        # 更新平均性能（移动平均）
        self.avg_performance = (self.avg_performance * (self.attempts - 1) + performance) / self.attempts
        self.last_attempted = datetime.now()
        self.completion_time = completion_time

class CurriculumGraph:
    """课程图"""
    
    def __init__(self):
        self.items: Dict[str, CurriculumItem] = {}
        self.prerequisites: Dict[str, List[str]] = defaultdict(list)
        self.dependencies: Dict[str, List[str]] = defaultdict(list)
        
    def add_item(self, item: CurriculumItem):
        """添加课程项目"""
        self.items[item.item_id] = item
        
        # 建立先修关系
        for prereq in item.prerequisites:
            self.prerequisites[item.item_id].append(prereq)
            self.dependencies[prereq].append(item.item_id)
    
    def get_available_items(self, completed_items: List[str]) -> List[CurriculumItem]:
        """获取可用的课程项目（已完成先修课程的）"""
        available = []
        
        for item_id, item in self.items.items():
            # 检查是否已完成所有先修课程
            prerequisites_met = all(prereq in completed_items 
                                  for prereq in self.prerequisites[item_id])
            
            # 检查是否已经完成该项目
            not_completed = item_id not in completed_items
            
            if prerequisites_met and not_completed:
                available.append(item)
        
        return available
    
    def get_item_sequence(self, target_item: str) -> List[str]:
        """获取到达目标项目的学习序列"""
        if target_item not in self.prerequisites:
            return []
        
        sequence = []
        visited = set()
        
        def dfs(item_id: str):
            if item_id in visited:
                return
            visited.add(item_id)
            
            for prereq in self.prerequisites[item_id]:
                dfs(prereq)
            
            sequence.append(item_id)
        
        dfs(target_item)
        return sequence
    
    def validate_curriculum(self) -> List[str]:
        """验证课程结构的有效性"""
        issues = []
        
        # 检查循环依赖
        for item_id in self.items:
            if self._has_cycle(item_id):
                issues.append(f"检测到循环依赖: {item_id}")
        
        # 检查孤立的项目
        for item_id in self.items:
            if (not self.prerequisites[item_id] and 
                not self.dependencies[item_id] and
                len(self.items) > 1):
                issues.append(f"孤立项目: {item_id}")
        
        return issues
    
    def _has_cycle(self, start_item: str) -> bool:
        """检查是否存在循环依赖"""
        visited = set()
        stack = set()
        
        def dfs(item_id: str) -> bool:
            if item_id in stack:
                return True
            if item_id in visited:
                return False
            
            visited.add(item_id)
            stack.add(item_id)
            
            for dependent in self.dependencies[item_id]:
                if dfs(dependent):
                    return True
            
            stack.remove(item_id)
            return False
        
        return dfs(start_item)

class DifficultyPredictor(nn.Module):
    """难度预测器"""
    
    def __init__(self, input_dim: int = 64, hidden_dim: int = 128):
        super(DifficultyPredictor, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        self.predictor = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.predictor(x)

class CurriculumLearning:
    """课程学习：渐进式学习"""
    
    def __init__(self, curriculum_dir: str = "data/curriculum_learning"):
        self.curriculum_dir = curriculum_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = self._setup_logger()
        
        # 课程图
        self.curriculum = CurriculumGraph()
        
        # 难度预测器
        self.difficulty_predictor = DifficultyPredictor().to(self.device)
        self.difficulty_optimizer = torch.optim.Adam(self.difficulty_predictor.parameters(), lr=0.001)
        
        # 学习状态
        self.completed_items: List[str] = []
        self.current_progress: Dict[str, float] = {}  # 项目ID到进度（0-1）
        self.learning_history: List[Dict] = []
        
        # 课程配置
        self.curriculum_config = {
            'difficulty_threshold': 0.7,  # 掌握程度阈值
            'max_difficulty_jump': 0.3,   # 最大难度跳跃
            'adaptive_pacing': True,      # 自适应节奏
            'review_frequency': 0.2,      # 复习频率
            'mastery_threshold': 0.8      # 掌握阈值
        }
        
        # 加载课程数据
        self._load_curriculum()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('curriculum_learning')
        if not logger.handlers:
            handler = logging.FileHandler('logs/curriculum_learning.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _load_curriculum(self):
        """加载课程数据"""
        curriculum_file = os.path.join(self.curriculum_dir, "curriculum_graph.json")
        progress_file = os.path.join(self.curriculum_dir, "learning_progress.json")
        config_file = os.path.join(self.curriculum_dir, "curriculum_config.json")
        
        try:
            os.makedirs(self.curriculum_dir, exist_ok=True)
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.curriculum_config.update(loaded_config)
            
            if os.path.exists(curriculum_file):
                with open(curriculum_file, 'r', encoding='utf-8') as f:
                    curriculum_data = json.load(f)
                    self._load_curriculum_from_data(curriculum_data)
            
            if os.path.exists(progress_file):
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                    self.completed_items = progress_data.get('completed_items', [])
                    self.current_progress = progress_data.get('current_progress', {})
                    self.learning_history = progress_data.get('learning_history', [])
            
            self.logger.info(f"课程数据加载成功，共{len(self.curriculum.items)}个项目")
            
        except Exception as e:
            self.logger.error(f"加载课程数据失败: {e}")
    
    def _load_curriculum_from_data(self, curriculum_data: Dict[str, Any]):
        """从数据加载课程图"""
        for item_data in curriculum_data.get('items', []):
            item = CurriculumItem(
                item_id=item_data['item_id'],
                difficulty=item_data['difficulty'],
                content=item_data['content'],
                prerequisites=item_data.get('prerequisites', []),
                learning_objectives=item_data.get('learning_objectives', [])
            )
            
            # 加载学习统计
            if 'learning_stats' in item_data:
                item.attempts = item_data['learning_stats'].get('attempts', 0)
                item.successes = item_data['learning_stats'].get('successes', 0)
                item.avg_performance = item_data['learning_stats'].get('avg_performance', 0.0)
            
            self.curriculum.add_item(item)
    
    def save_curriculum(self):
        """保存课程数据"""
        try:
            os.makedirs(self.curriculum_dir, exist_ok=True)
            
            # 保存配置
            config_file = os.path.join(self.curriculum_dir, "curriculum_config.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.curriculum_config, f, ensure_ascii=False, indent=2)
            
            # 保存课程图
            curriculum_file = os.path.join(self.curriculum_dir, "curriculum_graph.json")
            curriculum_data = {
                'items': [],
                'timestamp': datetime.now().isoformat()
            }
            
            for item_id, item in self.curriculum.items.items():
                item_data = {
                    'item_id': item.item_id,
                    'difficulty': item.difficulty,
                    'content': item.content,
                    'prerequisites': item.prerequisites,
                    'learning_objectives': item.learning_objectives,
                    'learning_stats': {
                        'attempts': item.attempts,
                        'successes': item.successes,
                        'avg_performance': item.avg_performance
                    }
                }
                curriculum_data['items'].append(item_data)
            
            with open(curriculum_file, 'w', encoding='utf-8') as f:
                json.dump(curriculum_data, f, ensure_ascii=False, indent=2)
            
            # 保存学习进度
            progress_file = os.path.join(self.curriculum_dir, "learning_progress.json")
            progress_data = {
                'completed_items': self.completed_items,
                'current_progress': self.current_progress,
                'learning_history': self.learning_history,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info("课程数据保存成功")
            
        except Exception as e:
            self.logger.error(f"保存课程数据失败: {e}")
    
    def add_curriculum_item(self, item_id: str, difficulty: float, content: Dict[str, Any],
                          prerequisites: List[str] = None, learning_objectives: List[str] = None):
        """添加课程项目"""
        item = CurriculumItem(item_id, difficulty, content, prerequisites, learning_objectives)
        self.curriculum.add_item(item)
        self.save_curriculum()
        self.logger.info(f"课程项目添加成功: {item_id}")
    
    def get_recommended_item(self, user_skill_level: float = 0.5) -> Optional[CurriculumItem]:
        """
        获取推荐的学习项目
        
        Args:
            user_skill_level: 用户技能水平（0-1）
            
        Returns:
            推荐的课程项目
        """
        available_items = self.curriculum.get_available_items(self.completed_items)
        
        if not available_items:
            self.logger.info("没有可用的课程项目")
            return None
        
        # 计算每个项目的适宜性分数
        scored_items = []
        for item in available_items:
            score = self._calculate_item_suitability(item, user_skill_level)
            scored_items.append((item, score))
        
        # 按适宜性排序
        scored_items.sort(key=lambda x: x[1], reverse=True)
        
        # 选择最高分的项目
        recommended_item, score = scored_items[0]
        
        self.logger.info(f"推荐学习项目: {recommended_item.item_id} (适宜性: {score:.3f})")
        return recommended_item
    
    def _calculate_item_suitability(self, item: CurriculumItem, user_skill_level: float) -> float:
        """计算项目适宜性分数"""
        base_score = 0.0
        
        # 难度匹配度（用户技能与项目难度的匹配）
        difficulty_match = 1.0 - abs(user_skill_level - item.difficulty)
        base_score += difficulty_match * 0.4
        
        # 学习进度考虑
        if item.item_id in self.current_progress:
            progress = self.current_progress[item.item_id]
            base_score += progress * 0.2  # 有进展的项目优先
        
        # 复习需求
        if (item.success_rate > self.curriculum_config['mastery_threshold'] and
            random.random() < self.curriculum_config['review_frequency']):
            base_score += 0.3  # 复习已掌握内容
        
        # 多样性考虑（避免重复学习相同类型内容）
        recent_items = [h['item_id'] for h in self.learning_history[-5:]]
        if item.item_id not in recent_items:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def record_learning_attempt(self, item_id: str, success: bool, 
                              performance: float, completion_time: float):
        """
        记录学习尝试
        
        Args:
            item_id: 项目ID
            success: 是否成功
            performance: 性能评分（0-1）
            completion_time: 完成时间（秒）
        """
        if item_id not in self.curriculum.items:
            self.logger.warning(f"未知的课程项目: {item_id}")
            return
        
        item = self.curriculum.items[item_id]
        item.record_attempt(success, performance, completion_time)
        
        # 更新学习进度
        if success and performance >= self.curriculum_config['mastery_threshold']:
            if item_id not in self.completed_items:
                self.completed_items.append(item_id)
            self.current_progress[item_id] = 1.0  # 标记为完成
        else:
            # 更新进度（基于性能）
            current_progress = self.current_progress.get(item_id, 0.0)
            new_progress = max(current_progress, performance)
            self.current_progress[item_id] = new_progress
        
        # 记录学习历史
        learning_record = {
            'item_id': item_id,
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'performance': performance,
            'completion_time': completion_time,
            'mastery_level': item.mastery_level,
            'difficulty': item.difficulty
        }
        
        self.learning_history.append(learning_record)
        
        # 更新难度预测器
        self._update_difficulty_predictor(item, performance)
        
        self.logger.info(f"学习记录已保存: {item_id} (性能: {performance:.3f})")
    
    def _update_difficulty_predictor(self, item: CurriculumItem, actual_performance: float):
        """更新难度预测器"""
        try:
            # 准备特征
            features = self._extract_difficulty_features(item)
            features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)
            
            # 预测难度
            predicted_difficulty = self.difficulty_predictor(features_tensor)
            
            # 计算损失（预测难度与实际性能的差异）
            # 实际性能越高，说明难度越低
            target_difficulty = 1.0 - actual_performance
            loss = F.mse_loss(predicted_difficulty, 
                             torch.tensor([target_difficulty]).to(self.device))
            
            # 反向传播
            self.difficulty_optimizer.zero_grad()
            loss.backward()
            self.difficulty_optimizer.step()
            
        except Exception as e:
            self.logger.error(f"更新难度预测器失败: {e}")
    
    def _extract_difficulty_features(self, item: CurriculumItem) -> List[float]:
        """提取难度特征"""
        features = []
        
        # 项目元数据特征
        features.append(item.difficulty)
        features.append(len(item.prerequisites))
        features.append(len(item.learning_objectives))
        
        # 内容复杂度特征
        content = item.content
        features.append(content.get('complexity', 0.5))
        features.append(content.get('concept_density', 0.5))
        
        # 学习历史特征
        features.append(item.attempts / 10.0)  # 归一化
        features.append(item.success_rate)
        features.append(item.avg_performance)
        
        # 填充到固定维度
        while len(features) < 64:
            features.append(0.0)
        features = features[:64]
        
        return features
    
    def predict_item_difficulty(self, content: Dict[str, Any]) -> float:
        """
        预测新内容的难度
        
        Args:
            content: 内容数据
            
        Returns:
            预测的难度（0-1）
        """
        try:
            # 创建临时项目用于特征提取
            temp_item = CurriculumItem("temp", 0.5, content)
            features = self._extract_difficulty_features(temp_item)
            features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                predicted_difficulty = self.difficulty_predictor(features_tensor)
            
            return predicted_difficulty.item()
            
        except Exception as e:
            self.logger.error(f"预测难度失败: {e}")
            return 0.5  # 默认难度
    
    def generate_learning_path(self, target_item: str, user_skill_level: float) -> Dict[str, Any]:
        """
        生成学习路径
        
        Args:
            target_item: 目标项目
            user_skill_level: 用户技能水平
            
        Returns:
            学习路径规划
        """
        if target_item not in self.curriculum.items:
            return {'error': f'目标项目不存在: {target_item}'}
        
        # 获取学习序列
        learning_sequence = self.curriculum.get_item_sequence(target_item)
        
        if not learning_sequence:
            return {'error': '无法生成学习路径'}
        
        # 分析路径难度
        path_difficulty = self._analyze_path_difficulty(learning_sequence)
        
        # 估算学习时间
        estimated_time = self._estimate_learning_time(learning_sequence, user_skill_level)
        
        # 检查已完成的项目
        completed_in_path = [item for item in learning_sequence if item in self.completed_items]
        remaining_items = [item for item in learning_sequence if item not in self.completed_items]
        
        learning_path = {
            'target_item': target_item,
            'full_sequence': learning_sequence,
            'completed_items': completed_in_path,
            'remaining_items': remaining_items,
            'path_difficulty': path_difficulty,
            'estimated_learning_time_hours': estimated_time,
            'progress_percentage': len(completed_in_path) / len(learning_sequence) * 100,
            'generated_at': datetime.now().isoformat()
        }
        
        self.logger.info(f"学习路径生成完成: {target_item} "
                        f"(进度: {learning_path['progress_percentage']:.1f}%)")
        
        return learning_path
    
    def _analyze_path_difficulty(self, learning_sequence: List[str]) -> Dict[str, Any]:
        """分析路径难度"""
        difficulties = []
        for item_id in learning_sequence:
            if item_id in self.curriculum.items:
                difficulties.append(self.curriculum.items[item_id].difficulty)
        
        if not difficulties:
            return {'average': 0.5, 'max': 0.5, 'min': 0.5}
        
        return {
            'average': np.mean(difficulties),
            'max': np.max(difficulties),
            'min': np.min(difficulties),
            'progression_smoothness': self._calculate_progression_smoothness(difficulties)
        }
    
    def _calculate_progression_smoothness(self, difficulties: List[float]) -> float:
        """计算进度平滑度"""
        if len(difficulties) < 2:
            return 1.0
        
        # 计算难度变化的平滑度（变化越小越平滑）
        changes = [abs(difficulties[i+1] - difficulties[i]) for i in range(len(difficulties)-1)]
        avg_change = np.mean(changes)
        
        # 转换为平滑度分数（0-1，1表示最平滑）
        smoothness = 1.0 - min(avg_change / 0.5, 1.0)  # 假设最大可接受变化为0.5
        return max(smoothness, 0.0)
    
    def _estimate_learning_time(self, learning_sequence: List[str], 
                              user_skill_level: float) -> float:
        """估算学习时间（小时）"""
        total_time = 0.0
        
        for item_id in learning_sequence:
            if item_id in self.completed_items:
                continue  # 已完成的项目不计算时间
            
            if item_id in self.curriculum.items:
                item = self.curriculum.items[item_id]
                
                # 基于难度和用户技能水平估算时间
                base_time = 1.0  # 基础学习时间（小时）
                difficulty_factor = item.difficulty
                skill_factor = 1.0 - user_skill_level
                
                estimated_time = base_time * difficulty_factor * skill_factor
                total_time += estimated_time
        
        return total_time
    
    def get_learning_analytics(self) -> Dict[str, Any]:
        """获取学习分析"""
        total_items = len(self.curriculum.items)
        completed_count = len(self.completed_items)
        
        # 计算总体掌握程度
        mastery_scores = []
        for item_id, item in self.curriculum.items.items():
            mastery_scores.append(item.mastery_level)
        
        overall_mastery = np.mean(mastery_scores) if mastery_scores else 0.0
        
        # 学习进度分析
        recent_history = self.learning_history[-20:]  # 最近20次学习记录
        recent_performance = [record['performance'] for record in recent_history]
        
        performance_trend = 'stable'
        if len(recent_performance) >= 5:
            # 简单趋势分析
            recent_avg = np.mean(recent_performance[-5:])
            previous_avg = np.mean(recent_performance[-10:-5]) if len(recent_performance) >= 10 else recent_avg
            performance_trend = 'improving' if recent_avg > previous_avg else 'declining'
        
        analytics = {
            'total_items': total_items,
            'completed_items': completed_count,
            'completion_rate': completed_count / total_items if total_items > 0 else 0.0,
            'overall_mastery': overall_mastery,
            'average_performance': np.mean(recent_performance) if recent_performance else 0.0,
            'performance_trend': performance_trend,
            'recent_activity': {
                'last_7_days': self._get_recent_activity(7),
                'last_30_days': self._get_recent_activity(30)
            },
            'difficulty_distribution': self._get_difficulty_distribution(),
            'learning_velocity': self._calculate_learning_velocity()
        }
        
        return analytics
    
    def _get_recent_activity(self, days: int) -> Dict[str, int]:
        """获取近期学习活动"""
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        recent_records = [
            record for record in self.learning_history
            if datetime.fromisoformat(record['timestamp']).timestamp() > cutoff_date
        ]
        
        return {
            'learning_sessions': len(recent_records),
            'successful_attempts': sum(1 for r in recent_records if r['success']),
            'average_performance': np.mean([r['performance'] for r in recent_records]) 
                                if recent_records else 0.0
        }
    
    def _get_difficulty_distribution(self) -> Dict[str, int]:
        """获取难度分布"""
        distribution = {
            'beginner': 0,    # 0.0 - 0.33
            'intermediate': 0, # 0.34 - 0.66
            'advanced': 0      # 0.67 - 1.0
        }
        
        for item in self.curriculum.items.values():
            if item.difficulty <= 0.33:
                distribution['beginner'] += 1
            elif item.difficulty <= 0.66:
                distribution['intermediate'] += 1
            else:
                distribution['advanced'] += 1
        
        return distribution
    
    def _calculate_learning_velocity(self) -> float:
        """计算学习速度"""
        if len(self.learning_history) < 10:
            return 0.5  # 默认速度
        
        # 分析最近的学习效率
        recent_history = self.learning_history[-10:]
        total_learning_time = sum(record.get('completion_time', 0) for record in recent_history)
        total_performance = sum(record['performance'] for record in recent_history)
        
        if total_learning_time == 0:
            return 0.5
        
        # 学习速度 = 总性能 / 总时间（归一化）
        learning_velocity = total_performance / (total_learning_time / 3600)  # 转换为小时
        normalized_velocity = min(learning_velocity / 10.0, 1.0)  # 假设10为最大速度
        
        return normalized_velocity
    
    def adapt_curriculum_difficulty(self, user_performance: float):
        """根据用户表现调整课程难度"""
        if not self.curriculum_config['adaptive_pacing']:
            return
        
        # 如果用户表现很好，可以适当增加难度
        if user_performance > 0.8:
            adjustment = 0.05  # 轻微增加难度
        # 如果用户表现很差，适当降低难度
        elif user_performance < 0.4:
            adjustment = -0.05  # 轻微降低难度
        else:
            adjustment = 0.0
        
        # 应用调整到未学习的项目
        for item_id, item in self.curriculum.items.items():
            if item_id not in self.completed_items:
                new_difficulty = max(0.1, min(0.9, item.difficulty + adjustment))
                item.difficulty = new_difficulty
        
        if adjustment != 0.0:
            self.logger.info(f"课程难度已调整: {adjustment:+.3f}")

# 全局课程学习实例
_global_curriculum_learning: Optional[CurriculumLearning] = None

def get_curriculum_learning() -> CurriculumLearning:
    """获取全局课程学习实例"""
    global _global_curriculum_learning
    if _global_curriculum_learning is None:
        _global_curriculum_learning = CurriculumLearning()
    return _global_curriculum_learning

