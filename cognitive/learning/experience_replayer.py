# cognitive/learning/experience_replayer.py
import numpy as np
import random
import pickle
import os
from typing import Dict, List, Any, Optional, Tuple
from collections import deque, namedtuple
import logging
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor

# 经验数据结构
Experience = namedtuple('Experience', 
    ['state', 'action', 'reward', 'next_state', 'done', 'timestamp', 'metadata'])

class PrioritizedExperienceReplay:
    """优先经验回放缓冲区"""
    
    def __init__(self, capacity: int = 10000, alpha: float = 0.6, beta: float = 0.4):
        self.capacity = capacity
        self.alpha = alpha  # 优先级指数
        self.beta = beta    # 重要性采样指数
        self.beta_increment = 0.001
        
        # 经验存储
        self.experiences = []
        self.priorities = np.zeros((capacity,), dtype=np.float32)
        self.position = 0
        self.size = 0
        
        # 锁用于线程安全
        self.lock = threading.RLock()
        
    def add(self, experience: Experience, priority: Optional[float] = None):
        """添加经验到缓冲区"""
        with self.lock:
            if priority is None:
                # 新经验的初始优先级设为当前最大优先级或1.0
                if self.size > 0:
                    priority = np.max(self.priorities[:self.size])
                else:
                    priority = 1.0
            
            if self.size < self.capacity:
                self.experiences.append(experience)
                self.priorities[self.position] = priority
                self.size += 1
            else:
                self.experiences[self.position] = experience
                self.priorities[self.position] = priority
            
            self.position = (self.position + 1) % self.capacity
    
    def sample(self, batch_size: int) -> Tuple[List[Experience], np.ndarray, List[int]]:
        """从缓冲区中采样一批经验"""
        with self.lock:
            if self.size < batch_size:
                batch_size = self.size
            
            # 计算采样概率
            priorities = self.priorities[:self.size]
            probabilities = priorities ** self.alpha
            probabilities /= np.sum(probabilities)
            
            # 采样索引
            indices = np.random.choice(self.size, batch_size, p=probabilities)
            
            # 计算重要性采样权重
            weights = (self.size * probabilities[indices]) ** (-self.beta)
            weights /= np.max(weights)
            
            # 更新beta
            self.beta = min(1.0, self.beta + self.beta_increment)
            
            experiences = [self.experiences[i] for i in indices]
            return experiences, weights, indices.tolist()
    
    def update_priorities(self, indices: List[int], priorities: List[float]):
        """更新经验的优先级"""
        with self.lock:
            for idx, priority in zip(indices, priorities):
                self.priorities[idx] = priority
    
    def get_size(self) -> int:
        """获取当前缓冲区大小"""
        return self.size
    
    def get_capacity(self) -> int:
        """获取缓冲区容量"""
        return self.capacity

class ExperienceReplayer:
    """经验回放：重现经验以加强学习"""
    
    def __init__(self, replay_dir: str = "data/experience_replay", 
                 main_memory_size: int = 50000, 
                 episodic_memory_size: int = 10000):
        self.replay_dir = replay_dir
        self.logger = self._setup_logger()
        
        # 主经验回放缓冲区
        self.main_replay_buffer = PrioritizedExperienceReplay(main_memory_size)
        
        # 情景记忆缓冲区（用于长期重要经验）
        self.episodic_buffer = PrioritizedExperienceReplay(episodic_memory_size)
        
        # 短期记忆缓冲区（用于最近经验）
        self.short_term_buffer = deque(maxlen=1000)
        
        # 经验统计
        self.experience_stats = {
            'total_experiences': 0,
            'successful_experiences': 0,
            'failed_experiences': 0,
            'average_reward': 0.0,
            'last_update': None
        }
        
        # 线程池用于并行处理
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.processing_lock = threading.Lock()
        
        # 加载现有经验
        self._load_experiences()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('experience_replayer')
        if not logger.handlers:
            handler = logging.FileHandler('logs/experience_replay.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _load_experiences(self):
        """加载保存的经验数据"""
        main_buffer_file = os.path.join(self.replay_dir, "main_replay_buffer.pkl")
        episodic_buffer_file = os.path.join(self.replay_dir, "episodic_buffer.pkl")
        stats_file = os.path.join(self.replay_dir, "experience_stats.json")
        
        try:
            os.makedirs(self.replay_dir, exist_ok=True)
            
            if os.path.exists(main_buffer_file):
                with open(main_buffer_file, 'rb') as f:
                    loaded_data = pickle.load(f)
                    self.main_replay_buffer = loaded_data.get('buffer', self.main_replay_buffer)
            
            if os.path.exists(episodic_buffer_file):
                with open(episodic_buffer_file, 'rb') as f:
                    loaded_data = pickle.load(f)
                    self.episodic_buffer = loaded_data.get('buffer', self.episodic_buffer)
            
            self.logger.info("经验回放数据加载成功")
            
        except Exception as e:
            self.logger.error(f"加载经验回放数据失败: {e}")
    
    def save_experiences(self):
        """保存经验数据"""
        try:
            os.makedirs(self.replay_dir, exist_ok=True)
            
            # 保存主缓冲区
            main_buffer_file = os.path.join(self.replay_dir, "main_replay_buffer.pkl")
            with open(main_buffer_file, 'wb') as f:
                pickle.dump({
                    'buffer': self.main_replay_buffer,
                    'save_timestamp': datetime.now().isoformat()
                }, f)
            
            # 保存情景缓冲区
            episodic_buffer_file = os.path.join(self.replay_dir, "episodic_buffer.pkl")
            with open(episodic_buffer_file, 'wb') as f:
                pickle.dump({
                    'buffer': self.episodic_buffer,
                    'save_timestamp': datetime.now().isoformat()
                }, f)
            
            self.logger.info("经验回放数据保存成功")
            
        except Exception as e:
            self.logger.error(f"保存经验回放数据失败: {e}")
    
    def add_experience(self, state: Any, action: Any, reward: float, 
                      next_state: Any, done: bool, metadata: Dict[str, Any] = None):
        """
        添加新经验到回放缓冲区
        
        Args:
            state: 当前状态
            action: 执行的动作
            reward: 获得的奖励
            next_state: 下一个状态
            done: 是否结束
            metadata: 额外的元数据
        """
        if metadata is None:
            metadata = {}
        
        # 创建经验对象
        experience = Experience(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done,
            timestamp=datetime.now().isoformat(),
            metadata=metadata
        )
        
        # 计算优先级（基于奖励和重要性）
        priority = self._calculate_priority(experience)
        
        # 添加到各个缓冲区
        self.main_replay_buffer.add(experience, priority)
        self.short_term_buffer.append(experience)
        
        # 如果是重要经验，添加到情景缓冲区
        if self._is_important_experience(experience):
            self.episodic_buffer.add(experience, priority * 2.0)  # 重要经验优先级加倍
        
        # 更新统计信息
        self._update_stats(experience)
        
        # 异步处理经验分析
        self.thread_pool.submit(self._analyze_experience, experience)
    
    def _calculate_priority(self, experience: Experience) -> float:
        """计算经验的优先级"""
        base_priority = 1.0
        
        # 基于奖励的优先级
        reward = experience.reward
        if abs(reward) > 1.0:
            base_priority += abs(reward) * 0.5
        
        # 基于元数据的重要性
        metadata = experience.metadata
        if metadata.get('is_critical', False):
            base_priority += 2.0
        
        if metadata.get('contains_innovation', False):
            base_priority += 1.5
        
        # 基于时间的新鲜度（新经验稍高优先级）
        base_priority += 0.1
        
        return base_priority
    
    def _is_important_experience(self, experience: Experience) -> bool:
        """判断是否为重要经验"""
        metadata = experience.metadata
        
        # 高奖励或惩罚
        if abs(experience.reward) >= 2.0:
            return True
        
        # 关键决策点
        if metadata.get('is_critical', False):
            return True
        
        # 包含创新或发现
        if metadata.get('contains_innovation', False):
            return True
        
        # 任务完成或失败
        if experience.done and abs(experience.reward) > 0.5:
            return True
        
        return False
    
    def _update_stats(self, experience: Experience):
        """更新经验统计"""
        self.experience_stats['total_experiences'] += 1
        
        if experience.reward > 0:
            self.experience_stats['successful_experiences'] += 1
        elif experience.reward < 0:
            self.experience_stats['failed_experiences'] += 1
        
        # 更新平均奖励（移动平均）
        current_avg = self.experience_stats['average_reward']
        n = self.experience_stats['total_experiences']
        self.experience_stats['average_reward'] = (
            current_avg * (n - 1) + experience.reward
        ) / n
        
        self.experience_stats['last_update'] = datetime.now().isoformat()
    
    def _analyze_experience(self, experience: Experience):
        """分析经验（在后台线程中执行）"""
        try:
            # 这里可以添加更复杂的经验分析逻辑
            metadata = experience.metadata
            
            # 检测模式
            if experience.reward > 1.0 and not metadata.get('pattern_detected', False):
                self._detect_success_patterns(experience)
            
            # 学习洞察提取
            if abs(experience.reward) > 0.5:
                self._extract_learning_insights(experience)
                
        except Exception as e:
            self.logger.error(f"经验分析失败: {e}")
    
    def _detect_success_patterns(self, experience: Experience):
        """检测成功模式"""
        # 在实际实现中，这里会有更复杂的模式检测逻辑
        self.logger.info(f"检测到高奖励经验，奖励: {experience.reward}")
    
    def _extract_learning_insights(self, experience: Experience):
        """提取学习洞察"""
        # 在实际实现中，这里会分析经验中的学习点
        pass
    
    def sample_batch(self, batch_size: int = 32, 
                    buffer_type: str = 'main') -> Tuple[List[Experience], np.ndarray]:
        """
        从指定缓冲区采样一批经验
        
        Args:
            batch_size: 批次大小
            buffer_type: 缓冲区类型 ('main', 'episodic', 'mixed')
            
        Returns:
            经验批次和重要性采样权重
        """
        if buffer_type == 'main':
            experiences, weights, _ = self.main_replay_buffer.sample(batch_size)
        elif buffer_type == 'episodic':
            experiences, weights, _ = self.episodic_buffer.sample(batch_size)
        elif buffer_type == 'mixed':
            # 混合采样：一半来自主缓冲区，一半来自情景缓冲区
            main_experiences, main_weights, _ = self.main_replay_buffer.sample(batch_size // 2)
            episodic_experiences, episodic_weights, _ = self.episodic_buffer.sample(batch_size // 2)
            
            experiences = main_experiences + episodic_experiences
            weights = np.concatenate([main_weights, episodic_weights])
        else:
            raise ValueError(f"未知的缓冲区类型: {buffer_type}")
        
        return experiences, weights
    
    def replay_experiences(self, learning_system: Any, batch_size: int = 32, 
                          num_batches: int = 10, buffer_type: str = 'main'):
        """
        执行经验回放学习
        
        Args:
            learning_system: 学习系统实例
            batch_size: 批次大小
            num_batches: 批次数
            buffer_type: 缓冲区类型
        """
        total_loss = 0.0
        batches_processed = 0
        
        for i in range(num_batches):
            try:
                experiences, weights = self.sample_batch(batch_size, buffer_type)
                
                if not experiences:
                    self.logger.warning("没有可用的经验进行回放")
                    break
                
                # 在这里调用学习系统的更新方法
                # 实际实现中会根据具体的学习算法进行调整
                batch_loss = self._process_batch(learning_system, experiences, weights)
                total_loss += batch_loss
                batches_processed += 1
                
                self.logger.debug(f"经验回放批次 {i+1}/{num_batches}，损失: {batch_loss:.4f}")
                
            except Exception as e:
                self.logger.error(f"经验回放批次 {i+1} 处理失败: {e}")
                continue
        
        if batches_processed > 0:
            avg_loss = total_loss / batches_processed
            self.logger.info(f"经验回放完成，平均损失: {avg_loss:.4f}")
            return avg_loss
        else:
            return 0.0
    
    def _process_batch(self, learning_system: Any, experiences: List[Experience], 
                      weights: np.ndarray) -> float:
        """处理一个经验批次"""
        # 这里是经验回放的核心逻辑
        # 实际实现中会调用学习系统的更新方法
        
        # 模拟处理过程
        batch_loss = 0.0
        for exp, weight in zip(experiences, weights):
            # 这里应该是具体的机器学习更新步骤
            # 例如：Q-learning, policy gradient 等
            pass
        
        return batch_loss / len(experiences) if experiences else 0.0
    
    def get_recent_experiences(self, num_experiences: int = 100) -> List[Experience]:
        """获取最近的经验"""
        return list(self.short_term_buffer)[-num_experiences:]
    
    def get_high_reward_experiences(self, min_reward: float = 1.0, 
                                  max_experiences: int = 50) -> List[Experience]:
        """获取高奖励经验"""
        all_experiences = []
        
        # 从主缓冲区获取
        for exp in self.main_replay_buffer.experiences[:self.main_replay_buffer.size]:
            if exp.reward >= min_reward:
                all_experiences.append(exp)
        
        # 从情景缓冲区获取
        for exp in self.episodic_buffer.experiences[:self.episodic_buffer.size]:
            if exp.reward >= min_reward:
                all_experiences.append(exp)
        
        # 按奖励排序并返回前N个
        all_experiences.sort(key=lambda x: x.reward, reverse=True)
        return all_experiences[:max_experiences]
    
    def get_failed_experiences(self, max_experiences: int = 50) -> List[Experience]:
        """获取失败经验（负奖励）"""
        failed_experiences = []
        
        # 从主缓冲区获取
        for exp in self.main_replay_buffer.experiences[:self.main_replay_buffer.size]:
            if exp.reward < 0:
                failed_experiences.append(exp)
        
        # 按奖励排序（最差的在前）
        failed_experiences.sort(key=lambda x: x.reward)
        return failed_experiences[:max_experiences]
    
    def cleanup_old_experiences(self, max_age_days: int = 30):
        """清理旧经验"""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        cutoff_str = cutoff_date.isoformat()
        
        initial_size = self.main_replay_buffer.size
        
        # 清理主缓冲区
        new_experiences = []
        new_priorities = []
        
        for i in range(self.main_replay_buffer.size):
            exp = self.main_replay_buffer.experiences[i]
            if exp.timestamp > cutoff_str:
                new_experiences.append(exp)
                new_priorities.append(self.main_replay_buffer.priorities[i])
        
        # 更新缓冲区
        self.main_replay_buffer.experiences = new_experiences
        self.main_replay_buffer.priorities = np.array(new_priorities + 
            [0.0] * (self.main_replay_buffer.capacity - len(new_priorities)), 
            dtype=np.float32)
        self.main_replay_buffer.size = len(new_experiences)
        self.main_replay_buffer.position = self.main_replay_buffer.size % self.main_replay_buffer.capacity
        
        removed_count = initial_size - self.main_replay_buffer.size
        self.logger.info(f"清理了 {removed_count} 条旧经验")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取经验回放统计信息"""
        main_buffer_stats = {
            'size': self.main_replay_buffer.get_size(),
            'capacity': self.main_replay_buffer.get_capacity(),
            'utilization': self.main_replay_buffer.get_size() / self.main_replay_buffer.get_capacity()
        }
        
        episodic_buffer_stats = {
            'size': self.episodic_buffer.get_size(),
            'capacity': self.episodic_buffer.get_capacity(),
            'utilization': self.episodic_buffer.get_size() / self.episodic_buffer.get_capacity()
        }
        
        short_term_stats = {
            'size': len(self.short_term_buffer),
            'capacity': self.short_term_buffer.maxlen
        }
        
        return {
            'main_buffer': main_buffer_stats,
            'episodic_buffer': episodic_buffer_stats,
            'short_term_buffer': short_term_stats,
            'experience_stats': self.experience_stats,
            'total_unique_experiences': (main_buffer_stats['size'] + 
                                       episodic_buffer_stats['size'])
        }
    
    def find_similar_experiences(self, query_experience: Experience, 
                               max_results: int = 10) -> List[Tuple[Experience, float]]:
        """
        查找相似经验
        
        Args:
            query_experience: 查询经验
            max_results: 最大返回结果数
            
        Returns:
            相似经验列表（经验, 相似度）
        """
        # 这里实现相似度搜索逻辑
        # 实际实现中会使用向量相似度计算
        
        similar_experiences = []
        
        # 简化实现：基于奖励和状态的简单相似度
        for exp in self.main_replay_buffer.experiences[:self.main_replay_buffer.size]:
            similarity = self._calculate_experience_similarity(query_experience, exp)
            if similarity > 0.5:  # 相似度阈值
                similar_experiences.append((exp, similarity))
        
        # 按相似度排序
        similar_experiences.sort(key=lambda x: x[1], reverse=True)
        return similar_experiences[:max_results]
    
    def _calculate_experience_similarity(self, exp1: Experience, exp2: Experience) -> float:
        """计算两个经验的相似度"""
        similarity = 0.0
        
        # 奖励相似度
        reward_sim = 1.0 - min(abs(exp1.reward - exp2.reward) / 5.0, 1.0)
        similarity += reward_sim * 0.3
        
        # 动作相似度（如果动作可比较）
        if hasattr(exp1.action, '__len__') and hasattr(exp2.action, '__len__'):
            if len(exp1.action) == len(exp2.action):
                action_sim = np.dot(exp1.action, exp2.action) / (
                    np.linalg.norm(exp1.action) * np.linalg.norm(exp2.action) + 1e-8)
                similarity += max(action_sim, 0) * 0.4
        
        # 元数据相似度
        common_metadata = set(exp1.metadata.keys()) & set(exp2.metadata.keys())
        if common_metadata:
            metadata_sim = len(common_metadata) / max(len(exp1.metadata), len(exp2.metadata))
            similarity += metadata_sim * 0.3
        
        return similarity

# 全局经验回放器实例
_global_experience_replayer: Optional[ExperienceReplayer] = None

def get_experience_replayer() -> ExperienceReplayer:
    """获取全局经验回放器实例"""
    global _global_experience_replayer
    if _global_experience_replayer is None:
        _global_experience_replayer = ExperienceReplayer()
    return _global_experience_replayer

