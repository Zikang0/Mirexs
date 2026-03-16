# cognitive/learning/reinforcement_learner.py
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import json
import os
from datetime import datetime
import logging
from collections import deque, namedtuple
import random

# 定义经验元组
Transition = namedtuple('Transition', 
                       ['state', 'action', 'reward', 'next_state', 'done'])

class DQNNetwork(nn.Module):
    """深度Q网络"""
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 128):
        super(DQNNetwork, self).__init__()
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        
        # 特征提取层
        self.feature_net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
        # 优势流 (Advantage stream)
        self.advantage_net = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, action_dim)
        )
        
        # 价值流 (Value stream) - Dueling DQN架构
        self.value_net = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1)
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.feature_net(x)
        advantage = self.advantage_net(features)
        value = self.value_net(features)
        
        # 结合价值和优势
        q_values = value + (advantage - advantage.mean(dim=1, keepdim=True))
        return q_values

class PolicyNetwork(nn.Module):
    """策略网络（用于策略梯度方法）"""
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 128):
        super(PolicyNetwork, self).__init__()
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        self.policy_net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
            nn.Softmax(dim=-1)
        )
        
        # 价值网络（用于Actor-Critic）
        self.value_net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        action_probs = self.policy_net(x)
        state_value = self.value_net(x)
        return action_probs, state_value

class ReplayBuffer:
    """经验回放缓冲区"""
    
    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
        self.position = 0
        
    def push(self, transition: Transition):
        """添加经验到缓冲区"""
        self.buffer.append(transition)
        
    def sample(self, batch_size: int) -> List[Transition]:
        """从缓冲区采样一批经验"""
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))
    
    def __len__(self) -> int:
        return len(self.buffer)

class ReinforcementLearner:
    """强化学习：基于奖励的学习"""
    
    def __init__(self, rl_dir: str = "data/reinforcement_learning"):
        self.rl_dir = rl_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = self._setup_logger()
        
        # 强化学习参数
        self.learning_config = {
            'gamma': 0.99,  # 折扣因子
            'lr': 0.001,    # 学习率
            'batch_size': 32,
            'epsilon_start': 1.0,
            'epsilon_end': 0.01,
            'epsilon_decay': 0.995,
            'target_update': 100,  # 目标网络更新频率
            'memory_size': 10000,
            'warmup_steps': 1000   # 预热步数
        }
        
        # 模型和优化器（在初始化环境后设置）
        self.policy_net: Optional[DQNNetwork] = None
        self.target_net: Optional[DQNNetwork] = None
        self.optimizer: Optional[torch.optim.Optimizer] = None
        
        # 经验回放
        self.memory = ReplayBuffer(self.learning_config['memory_size'])
        
        # 训练状态
        self.training_step = 0
        self.epsilon = self.learning_config['epsilon_start']
        self.episode_rewards = []
        self.episode_lengths = []
        
        # 学习历史
        self.learning_history = []
        
        # 加载已有模型
        self._load_models()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('reinforcement_learner')
        if not logger.handlers:
            handler = logging.FileHandler('logs/reinforcement_learning.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _load_models(self):
        """加载已有模型"""
        model_file = os.path.join(self.rl_dir, "rl_models.pth")
        config_file = os.path.join(self.rl_dir, "learning_config.json")
        history_file = os.path.join(self.rl_dir, "learning_history.json")
        
        try:
            os.makedirs(self.rl_dir, exist_ok=True)
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.learning_config.update(loaded_config)
            
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.learning_history = json.load(f)
            
            self.logger.info("强化学习配置加载成功")
            
        except Exception as e:
            self.logger.error(f"加载强化学习模型失败: {e}")
    
    def save_models(self):
        """保存模型和配置"""
        try:
            os.makedirs(self.rl_dir, exist_ok=True)
            
            # 保存配置
            config_file = os.path.join(self.rl_dir, "learning_config.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.learning_config, f, ensure_ascii=False, indent=2)
            
            # 保存历史
            history_file = os.path.join(self.rl_dir, "learning_history.json")
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.learning_history, f, ensure_ascii=False, indent=2)
            
            # 保存模型（如果存在）
            if self.policy_net is not None:
                model_file = os.path.join(self.rl_dir, "rl_models.pth")
                torch.save({
                    'policy_net_state_dict': self.policy_net.state_dict(),
                    'target_net_state_dict': self.target_net.state_dict() if self.target_net else None,
                    'optimizer_state_dict': self.optimizer.state_dict() if self.optimizer else None,
                    'training_step': self.training_step,
                    'epsilon': self.epsilon,
                    'episode_rewards': self.episode_rewards,
                    'episode_lengths': self.episode_lengths
                }, model_file)
            
            self.logger.info("强化学习模型保存成功")
            
        except Exception as e:
            self.logger.error(f"保存强化学习模型失败: {e}")
    
    def initialize_environment(self, state_dim: int, action_dim: int, 
                             algorithm: str = "dqn"):
        """
        初始化强化学习环境
        
        Args:
            state_dim: 状态维度
            action_dim: 动作维度
            algorithm: 算法类型 ('dqn', 'policy_gradient', 'actor_critic')
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.algorithm = algorithm
        
        # 根据算法选择网络架构
        if algorithm == "dqn":
            self.policy_net = DQNNetwork(state_dim, action_dim).to(self.device)
            self.target_net = DQNNetwork(state_dim, action_dim).to(self.device)
            self.target_net.load_state_dict(self.policy_net.state_dict())
            self.target_net.eval()
        elif algorithm in ["policy_gradient", "actor_critic"]:
            self.policy_net = PolicyNetwork(state_dim, action_dim).to(self.device)
            self.target_net = None
        
        # 优化器
        self.optimizer = torch.optim.Adam(self.policy_net.parameters(), 
                                         lr=self.learning_config['lr'])
        
        self.logger.info(f"强化学习环境初始化完成: {algorithm}")
    
    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """
        选择动作
        
        Args:
            state: 当前状态
            training: 是否在训练模式
            
        Returns:
            选择的动作
        """
        if self.policy_net is None:
            raise ValueError("请先初始化环境")
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        # ε-贪婪策略
        if training and random.random() < self.epsilon:
            # 随机探索
            return random.randint(0, self.action_dim - 1)
        else:
            # 利用学到的策略
            with torch.no_grad():
                if isinstance(self.policy_net, DQNNetwork):
                    q_values = self.policy_net(state_tensor)
                    return q_values.max(1)[1].item()
                else:  # PolicyNetwork
                    action_probs, _ = self.policy_net(state_tensor)
                    action_dist = torch.distributions.Categorical(action_probs)
                    return action_dist.sample().item()
    
    def store_experience(self, state: np.ndarray, action: int, reward: float, 
                        next_state: np.ndarray, done: bool):
        """
        存储经验
        
        Args:
            state: 当前状态
            action: 执行的动作
            reward: 获得的奖励
            next_state: 下一个状态
            done: 是否结束
        """
        transition = Transition(state, action, reward, next_state, done)
        self.memory.push(transition)
    
    def update_model(self) -> Optional[float]:
        """
        更新模型
        
        Returns:
            损失值（如果进行了更新）
        """
        if len(self.memory) < self.learning_config['batch_size']:
            return None
        
        # 采样一批经验
        transitions = self.memory.sample(self.learning_config['batch_size'])
        batch = Transition(*zip(*transitions))
        
        # 转换为张量
        state_batch = torch.FloatTensor(np.array(batch.state)).to(self.device)
        action_batch = torch.LongTensor(batch.action).unsqueeze(1).to(self.device)
        reward_batch = torch.FloatTensor(batch.reward).to(self.device)
        next_state_batch = torch.FloatTensor(np.array(batch.next_state)).to(self.device)
        done_batch = torch.BoolTensor(batch.done).to(self.device)
        
        # 根据算法类型更新
        if self.algorithm == "dqn":
            loss = self._update_dqn(state_batch, action_batch, reward_batch, 
                                  next_state_batch, done_batch)
        elif self.algorithm == "policy_gradient":
            loss = self._update_policy_gradient(state_batch, action_batch, reward_batch)
        elif self.algorithm == "actor_critic":
            loss = self._update_actor_critic(state_batch, action_batch, reward_batch, 
                                           next_state_batch, done_batch)
        else:
            raise ValueError(f"未知的算法: {self.algorithm}")
        
        # 更新训练步数
        self.training_step += 1
        
        # 更新ε（探索率）
        if self.epsilon > self.learning_config['epsilon_end']:
            self.epsilon *= self.learning_config['epsilon_decay']
        
        # 更新目标网络
        if (self.algorithm == "dqn" and 
            self.training_step % self.learning_config['target_update'] == 0):
            self.target_net.load_state_dict(self.policy_net.state_dict())
        
        return loss
    
    def _update_dqn(self, state_batch: torch.Tensor, action_batch: torch.Tensor,
                   reward_batch: torch.Tensor, next_state_batch: torch.Tensor,
                   done_batch: torch.Tensor) -> float:
        """更新DQN模型"""
        # 计算当前Q值
        current_q_values = self.policy_net(state_batch).gather(1, action_batch)
        
        # 计算目标Q值
        with torch.no_grad():
            next_q_values = self.target_net(next_state_batch).max(1)[0]
            target_q_values = reward_batch + (
                self.learning_config['gamma'] * next_q_values * ~done_batch)
        
        # 计算损失
        loss = F.smooth_l1_loss(current_q_values.squeeze(), target_q_values)
        
        # 反向传播
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_value_(self.policy_net.parameters(), 100)
        self.optimizer.step()
        
        return loss.item()
    
    def _update_policy_gradient(self, state_batch: torch.Tensor, 
                               action_batch: torch.Tensor, 
                               reward_batch: torch.Tensor) -> float:
        """更新策略梯度模型"""
        # 计算动作概率
        action_probs, _ = self.policy_net(state_batch)
        action_dist = torch.distributions.Categorical(action_probs)
        
        # 计算对数概率
        log_probs = action_dist.log_prob(action_batch.squeeze())
        
        # 计算损失（负的期望奖励）
        loss = -torch.mean(log_probs * reward_batch)
        
        # 反向传播
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
    
    def _update_actor_critic(self, state_batch: torch.Tensor, 
                            action_batch: torch.Tensor, 
                            reward_batch: torch.Tensor,
                            next_state_batch: torch.Tensor,
                            done_batch: torch.Tensor) -> float:
        """更新Actor-Critic模型"""
        # 计算当前状态价值和下一状态价值
        _, current_values = self.policy_net(state_batch)
        with torch.no_grad():
            _, next_values = self.policy_net(next_state_batch)
        
        # 计算优势函数
        target_values = reward_batch.unsqueeze(1) + (
            self.learning_config['gamma'] * next_values * ~done_batch.unsqueeze(1))
        advantages = target_values - current_values
        
        # 计算动作概率
        action_probs, _ = self.policy_net(state_batch)
        action_dist = torch.distributions.Categorical(action_probs)
        log_probs = action_dist.log_prob(action_batch.squeeze())
        
        # 计算Actor和Critic损失
        actor_loss = -torch.mean(log_probs.unsqueeze(1) * advantages.detach())
        critic_loss = F.mse_loss(current_values, target_values)
        
        # 总损失
        loss = actor_loss + 0.5 * critic_loss
        
        # 反向传播
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
    
    def train_episode(self, env, max_steps: int = 1000) -> Dict[str, Any]:
        """
        训练一个回合
        
        Args:
            env: 环境对象（需要有reset和step方法）
            max_steps: 最大步数
            
        Returns:
            回合训练结果
        """
        state = env.reset()
        total_reward = 0
        steps = 0
        
        for step in range(max_steps):
            # 选择动作
            action = self.select_action(state, training=True)
            
            # 执行动作
            next_state, reward, done, info = env.step(action)
            
            # 存储经验
            self.store_experience(state, action, reward, next_state, done)
            
            # 更新模型
            loss = self.update_model()
            
            state = next_state
            total_reward += reward
            steps += 1
            
            if done:
                break
        
        # 记录回合结果
        episode_result = {
            'episode': len(self.episode_rewards) + 1,
            'total_reward': total_reward,
            'steps': steps,
            'epsilon': self.epsilon,
            'training_step': self.training_step,
            'timestamp': datetime.now().isoformat()
        }
        
        self.episode_rewards.append(total_reward)
        self.episode_lengths.append(steps)
        self.learning_history.append(episode_result)
        
        self.logger.info(f"回合 {episode_result['episode']} 完成: "
                        f"奖励={total_reward}, 步数={steps}, ε={self.epsilon:.3f}")
        
        return episode_result
    
    def evaluate_policy(self, env, num_episodes: int = 10) -> Dict[str, Any]:
        """
        评估策略
        
        Args:
            env: 环境对象
            num_episodes: 评估回合数
            
        Returns:
            评估结果
        """
        if self.policy_net is None:
            raise ValueError("请先初始化环境")
        
        episode_rewards = []
        episode_lengths = []
        
        for episode in range(num_episodes):
            state = env.reset()
            total_reward = 0
            steps = 0
            done = False
            
            while not done and steps < 1000:
                action = self.select_action(state, training=False)
                next_state, reward, done, _ = env.step(action)
                
                state = next_state
                total_reward += reward
                steps += 1
            
            episode_rewards.append(total_reward)
            episode_lengths.append(steps)
        
        evaluation_result = {
            'timestamp': datetime.now().isoformat(),
            'num_episodes': num_episodes,
            'mean_reward': np.mean(episode_rewards),
            'std_reward': np.std(episode_rewards),
            'mean_length': np.mean(episode_lengths),
            'best_reward': np.max(episode_rewards),
            'worst_reward': np.min(episode_rewards)
        }
        
        self.logger.info(f"策略评估完成: 平均奖励={evaluation_result['mean_reward']:.2f}")
        return evaluation_result
    
    def get_learning_curves(self) -> Dict[str, Any]:
        """获取学习曲线数据"""
        if not self.episode_rewards:
            return {'message': '尚无训练数据'}
        
        # 计算移动平均
        window = min(10, len(self.episode_rewards))
        moving_avg = np.convolve(self.episode_rewards, 
                                np.ones(window)/window, mode='valid')
        
        return {
            'episode_rewards': self.episode_rewards,
            'episode_lengths': self.episode_lengths,
            'moving_average_rewards': moving_avg.tolist(),
            'epsilon_history': [self.learning_config['epsilon_start'] * 
                              (self.learning_config['epsilon_decay'] ** i) 
                              for i in range(len(self.episode_rewards))],
            'training_steps': self.training_step
        }
    
    def get_policy_analysis(self, state: np.ndarray) -> Dict[str, Any]:
        """
        分析策略在给定状态下的行为
        
        Args:
            state: 要分析的状态
            
        Returns:
            策略分析结果
        """
        if self.policy_net is None:
            raise ValueError("请先初始化环境")
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            if isinstance(self.policy_net, DQNNetwork):
                q_values = self.policy_net(state_tensor).squeeze().cpu().numpy()
                best_action = np.argmax(q_values)
                action_probs = F.softmax(torch.FloatTensor(q_values), dim=0).numpy()
            else:  # PolicyNetwork
                action_probs, state_value = self.policy_net(state_tensor)
                action_probs = action_probs.squeeze().cpu().numpy()
                state_value = state_value.squeeze().cpu().item()
                best_action = np.argmax(action_probs)
                q_values = action_probs  # 对于策略网络，用概率近似Q值
        
        analysis = {
            'state': state.tolist(),
            'q_values': q_values.tolist() if isinstance(q_values, np.ndarray) else q_values,
            'action_probs': action_probs.tolist(),
            'best_action': int(best_action),
            'confidence': float(action_probs[best_action]),
            'entropy': float(-np.sum(action_probs * np.log(action_probs + 1e-8))),
            'timestamp': datetime.now().isoformat()
        }
        
        if isinstance(self.policy_net, PolicyNetwork):
            analysis['state_value'] = state_value
        
        return analysis
    
    def update_learning_config(self, new_config: Dict[str, Any]):
        """更新学习配置"""
        self.learning_config.update(new_config)
        self.save_models()
        self.logger.info("强化学习配置已更新")
    
    def get_training_status(self) -> Dict[str, Any]:
        """获取训练状态"""
        return {
            'training_step': self.training_step,
            'epsilon': self.epsilon,
            'memory_size': len(self.memory),
            'episodes_completed': len(self.episode_rewards),
            'mean_reward': np.mean(self.episode_rewards[-10:]) if self.episode_rewards else 0,
            'algorithm': self.algorithm,
            'state_dim': self.state_dim if hasattr(self, 'state_dim') else None,
            'action_dim': self.action_dim if hasattr(self, 'action_dim') else None
        }

# 全局强化学习实例
_global_reinforcement_learner: Optional[ReinforcementLearner] = None

def get_reinforcement_learner() -> ReinforcementLearner:
    """获取全局强化学习实例"""
    global _global_reinforcement_learner
    if _global_reinforcement_learner is None:
        _global_reinforcement_learner = ReinforcementLearner()
    return _global_reinforcement_learner

