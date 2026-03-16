# cognitive/learning/meta_learner.py
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Any, Optional
import pickle
import os
from datetime import datetime
import logging

class MetaLearningNetwork(nn.Module):
    """元学习神经网络模型"""
    
    def __init__(self, input_dim: int = 512, hidden_dim: int = 1024, output_dim: int = 256):
        super(MetaLearningNetwork, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        
        # 特征提取层
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        # 元学习层
        self.meta_learner = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.ReLU(),
            nn.Linear(hidden_dim // 4, output_dim),
            nn.Tanh()
        )
        
        # 学习策略输出层
        self.strategy_predictor = nn.Sequential(
            nn.Linear(output_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.Softmax(dim=-1)
        )
        
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        features = self.feature_extractor(x)
        meta_features = self.meta_learner(features)
        learning_strategy = self.strategy_predictor(meta_features)
        
        return {
            'meta_features': meta_features,
            'learning_strategy': learning_strategy
        }

class MetaLearner:
    """元学习器：学习如何学习"""
    
    def __init__(self, model_dir: str = "data/models/meta_learning"):
        self.model_dir = model_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = self._setup_logger()
        
        # 初始化模型
        self.model = MetaLearningNetwork().to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()
        
        # 学习历史
        self.learning_history: List[Dict] = []
        self.task_performance: Dict[str, List[float]] = {}
        
        # 加载现有模型
        self._load_model()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('meta_learner')
        if not logger.handlers:
            handler = logging.FileHandler('logs/meta_learning.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _load_model(self):
        """加载已训练的模型"""
        model_path = os.path.join(self.model_dir, "meta_learner_model.pth")
        if os.path.exists(model_path):
            try:
                checkpoint = torch.load(model_path, map_location=self.device)
                self.model.load_state_dict(checkpoint['model_state_dict'])
                self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
                self.learning_history = checkpoint.get('learning_history', [])
                self.task_performance = checkpoint.get('task_performance', {})
                self.logger.info("元学习模型加载成功")
            except Exception as e:
                self.logger.error(f"加载元学习模型失败: {e}")
    
    def save_model(self):
        """保存模型"""
        os.makedirs(self.model_dir, exist_ok=True)
        model_path = os.path.join(self.model_dir, "meta_learner_model.pth")
        
        checkpoint = {
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'learning_history': self.learning_history,
            'task_performance': self.task_performance
        }
        
        torch.save(checkpoint, model_path)
        self.logger.info("元学习模型保存成功")
    
    def analyze_learning_patterns(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析学习模式
        
        Args:
            task_data: 任务数据，包含任务类型、历史性能等信息
            
        Returns:
            学习策略建议
        """
        try:
            # 准备输入数据
            input_features = self._prepare_features(task_data)
            input_tensor = torch.FloatTensor(input_features).unsqueeze(0).to(self.device)
            
            # 模型推理
            self.model.eval()
            with torch.no_grad():
                outputs = self.model(input_tensor)
            
            # 解析输出
            learning_strategy = self._interpret_strategy(outputs['learning_strategy'][0])
            meta_features = outputs['meta_features'][0].cpu().numpy()
            
            analysis_result = {
                'optimal_strategy': learning_strategy,
                'meta_features': meta_features.tolist(),
                'confidence': float(torch.max(outputs['learning_strategy'][0])),
                'recommended_approach': self._generate_recommendation(learning_strategy, task_data),
                'timestamp': datetime.now().isoformat()
            }
            
            # 记录分析结果
            self.learning_history.append({
                'task_data': task_data,
                'analysis_result': analysis_result,
                'timestamp': datetime.now().isoformat()
            })
            
            self.logger.info(f"学习模式分析完成: {learning_strategy}")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"学习模式分析失败: {e}")
            return self._get_fallback_strategy()
    
    def _prepare_features(self, task_data: Dict[str, Any]) -> List[float]:
        """准备输入特征"""
        features = []
        
        # 任务类型特征
        task_type = task_data.get('task_type', 'unknown')
        task_type_encoding = self._encode_task_type(task_type)
        features.extend(task_type_encoding)
        
        # 历史性能特征
        performance_data = task_data.get('performance_history', [])
        if performance_data:
            features.append(np.mean(performance_data))
            features.append(np.std(performance_data))
            features.append(len(performance_data))
        else:
            features.extend([0.5, 0.1, 1])  # 默认值
        
        # 学习风格特征
        learning_style = task_data.get('learning_style', {})
        features.append(learning_style.get('pace', 0.5))
        features.append(learning_style.get('depth', 0.5))
        features.append(learning_style.get('variety', 0.5))
        
        # 确保特征维度一致
        while len(features) < 512:
            features.append(0.0)
        features = features[:512]
        
        return features
    
    def _encode_task_type(self, task_type: str) -> List[float]:
        """编码任务类型"""
        task_types = ['classification', 'regression', 'reinforcement', 'generation', 'optimization', 'unknown']
        encoding = [0.0] * len(task_types)
        
        if task_type in task_types:
            encoding[task_types.index(task_type)] = 1.0
        else:
            encoding[-1] = 1.0  # unknown
        
        return encoding
    
    def _interpret_strategy(self, strategy_tensor: torch.Tensor) -> str:
        """解释学习策略输出"""
        strategy_idx = torch.argmax(strategy_tensor).item()
        strategies = [
            'supervised_learning',
            'reinforcement_learning', 
            'transfer_learning',
            'self_supervised_learning',
            'meta_learning',
            'curriculum_learning',
            'multi_task_learning'
        ]
        
        return strategies[strategy_idx % len(strategies)]
    
    def _generate_recommendation(self, strategy: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成学习策略推荐"""
        base_recommendation = {
            'learning_rate': 0.001,
            'batch_size': 32,
            'optimizer': 'adam',
            'regularization': 0.01
        }
        
        strategy_specific = {
            'supervised_learning': {
                'recommendation': '使用交叉验证和早停法',
                'parameters': {'validation_split': 0.2, 'patience': 5}
            },
            'reinforcement_learning': {
                'recommendation': '使用经验回放和目标网络',
                'parameters': {'gamma': 0.99, 'epsilon_decay': 0.995}
            },
            'transfer_learning': {
                'recommendation': '冻结基础层，微调顶层',
                'parameters': {'freeze_layers': 0.7, 'fine_tune_lr': 0.0001}
            },
            'meta_learning': {
                'recommendation': '使用MAML或Reptile算法',
                'parameters': {'inner_lr': 0.01, 'meta_lr': 0.001}
            }
        }
        
        recommendation = base_recommendation.copy()
        if strategy in strategy_specific:
            recommendation.update(strategy_specific[strategy]['parameters'])
            recommendation['description'] = strategy_specific[strategy]['recommendation']
        else:
            recommendation['description'] = f'使用{strategy}策略'
        
        return recommendation
    
    def _get_fallback_strategy(self) -> Dict[str, Any]:
        """获取回退策略"""
        return {
            'optimal_strategy': 'supervised_learning',
            'meta_features': [0.0] * 256,
            'confidence': 0.5,
            'recommended_approach': {
                'learning_rate': 0.001,
                'batch_size': 32,
                'optimizer': 'adam',
                'description': '使用默认监督学习策略'
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def update_from_experience(self, experience_data: Dict[str, Any]):
        """
        从经验中更新元学习模型
        
        Args:
            experience_data: 包含任务执行结果的经验数据
        """
        try:
            # 准备训练数据
            input_features = self._prepare_features(experience_data['task_data'])
            target_strategy = self._encode_strategy(experience_data['actual_strategy'])
            
            input_tensor = torch.FloatTensor(input_features).unsqueeze(0).to(self.device)
            target_tensor = torch.FloatTensor(target_strategy).unsqueeze(0).to(self.device)
            
            # 训练模型
            self.model.train()
            self.optimizer.zero_grad()
            
            outputs = self.model(input_tensor)
            loss = self.criterion(outputs['learning_strategy'], target_tensor)
            
            loss.backward()
            self.optimizer.step()
            
            # 记录性能
            task_type = experience_data['task_data'].get('task_type', 'unknown')
            if task_type not in self.task_performance:
                self.task_performance[task_type] = []
            self.task_performance[task_type].append(experience_data['performance_score'])
            
            self.logger.info(f"元学习模型更新完成，损失: {loss.item():.4f}")
            
        except Exception as e:
            self.logger.error(f"元学习模型更新失败: {e}")
    
    def _encode_strategy(self, strategy: str) -> List[float]:
        """编码学习策略"""
        strategies = [
            'supervised_learning',
            'reinforcement_learning', 
            'transfer_learning',
            'self_supervised_learning',
            'meta_learning',
            'curriculum_learning',
            'multi_task_learning'
        ]
        
        encoding = [0.0] * len(strategies)
        if strategy in strategies:
            encoding[strategies.index(strategy)] = 1.0
        else:
            encoding[0] = 1.0  # 默认使用监督学习
        
        return encoding
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """获取学习洞察"""
        insights = {
            'total_learning_episodes': len(self.learning_history),
            'task_type_distribution': {},
            'strategy_effectiveness': {},
            'recent_performance_trends': self._calculate_performance_trends(),
            'learning_efficiency_metrics': self._calculate_efficiency_metrics()
        }
        
        # 分析任务类型分布
        for episode in self.learning_history:
            task_type = episode['task_data'].get('task_type', 'unknown')
            insights['task_type_distribution'][task_type] = \
                insights['task_type_distribution'].get(task_type, 0) + 1
        
        # 分析策略效果
        for task_type, performances in self.task_performance.items():
            if performances:
                insights['strategy_effectiveness'][task_type] = {
                    'average_performance': np.mean(performances),
                    'performance_std': np.std(performances),
                    'sample_size': len(performances)
                }
        
        return insights
    
    def _calculate_performance_trends(self) -> Dict[str, float]:
        """计算性能趋势"""
        if len(self.learning_history) < 2:
            return {'trend': 'insufficient_data'}
        
        recent_performances = []
        for episode in self.learning_history[-10:]:  # 最近10次
            # 这里需要根据实际数据结构调整
            performance = episode.get('analysis_result', {}).get('confidence', 0.5)
            recent_performances.append(performance)
        
        if len(recent_performances) >= 2:
            trend = np.polyfit(range(len(recent_performances)), recent_performances, 1)[0]
            return {
                'trend_slope': trend,
                'trend_direction': 'improving' if trend > 0 else 'declining',
                'current_level': recent_performances[-1]
            }
        else:
            return {'trend': 'insufficient_data'}
    
    def _calculate_efficiency_metrics(self) -> Dict[str, float]:
        """计算学习效率指标"""
        if not self.learning_history:
            return {'efficiency': 0.5, 'consistency': 0.5}
        
        confidences = [episode['analysis_result'].get('confidence', 0.5) 
                      for episode in self.learning_history]
        
        return {
            'average_confidence': np.mean(confidences),
            'consistency': 1.0 - np.std(confidences),  # 标准差越小，一致性越高
            'learning_speed': self._estimate_learning_speed()
        }
    
    def _estimate_learning_speed(self) -> float:
        """估计学习速度"""
        if len(self.learning_history) < 5:
            return 0.5
        
        # 使用最近几次学习的性能变化来估计学习速度
        recent_confidences = [episode['analysis_result'].get('confidence', 0.5) 
                             for episode in self.learning_history[-5:]]
        
        if len(recent_confidences) >= 2:
            improvements = [recent_confidences[i+1] - recent_confidences[i] 
                          for i in range(len(recent_confidences)-1)]
            return np.mean(improvements) if improvements else 0.0
        else:
            return 0.0

# 全局元学习器实例
_global_meta_learner: Optional[MetaLearner] = None

def get_meta_learner() -> MetaLearner:
    """获取全局元学习器实例"""
    global _global_meta_learner
    if _global_meta_learner is None:
        _global_meta_learner = MetaLearner()
    return _global_meta_learner

