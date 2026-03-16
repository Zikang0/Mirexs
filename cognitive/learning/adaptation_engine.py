# cognitive/learning/adaptation_engine.py
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import json
import os
from datetime import datetime
import logging
from collections import defaultdict, deque
import hashlib

class AdaptationNetwork(nn.Module):
    """适应网络"""
    
    def __init__(self, input_dim: int = 256, hidden_dim: int = 128, output_dim: int = 64):
        super(AdaptationNetwork, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        
        # 环境特征编码器
        self.env_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU()
        )
        
        # 策略适配器
        self.policy_adapter = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.ReLU(),
            nn.Linear(hidden_dim // 4, output_dim),
            nn.Tanh()
        )
        
        # 变化检测器
        self.change_detector = nn.Sequential(
            nn.Linear(input_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid()
        )
        
    def forward(self, current_state: torch.Tensor, previous_state: torch.Tensor = None):
        """前向传播"""
        env_features = self.env_encoder(current_state)
        adaptation_weights = self.policy_adapter(env_features)
        
        output = {
            'adaptation_weights': adaptation_weights,
            'environment_features': env_features
        }
        
        # 如果提供了先前状态，检测变化
        if previous_state is not None:
            state_pair = torch.cat([current_state, previous_state], dim=1)
            change_score = self.change_detector(state_pair)
            output['change_score'] = change_score
        
        return output

class AdaptationEngine:
    """适应引擎：动态适应环境变化"""
    
    def __init__(self, adaptation_dir: str = "data/adaptation_engine"):
        self.adaptation_dir = adaptation_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = self._setup_logger()
        
        # 适应网络
        self.adaptation_net = AdaptationNetwork().to(self.device)
        self.optimizer = torch.optim.Adam(self.adaptation_net.parameters(), lr=0.001)
        
        # 环境状态历史
        self.environment_history = deque(maxlen=100)
        self.adaptation_history: List[Dict] = []
        
        # 适应策略库
        self.adaptation_strategies: Dict[str, Dict] = {}
        
        # 适应配置
        self.adaptation_config = {
            'change_detection_threshold': 0.7,
            'adaptation_trigger_delay': 5,
            'learning_rate_adaptation': True,
            'strategy_switching': True,
            'performance_monitoring': True
        }
        
        # 当前状态
        self.current_environment_id = None
        self.last_adaptation_time = None
        self.adaptation_count = 0
        
        # 加载适应数据
        self._load_adaptation_data()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('adaptation_engine')
        if not logger.handlers:
            handler = logging.FileHandler('logs/adaptation_engine.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _load_adaptation_data(self):
        """加载适应数据"""
        strategies_file = os.path.join(self.adaptation_dir, "adaptation_strategies.json")
        history_file = os.path.join(self.adaptation_dir, "adaptation_history.json")
        config_file = os.path.join(self.adaptation_dir, "adaptation_config.json")
        
        try:
            os.makedirs(self.adaptation_dir, exist_ok=True)
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.adaptation_config.update(loaded_config)
            
            if os.path.exists(strategies_file):
                with open(strategies_file, 'r', encoding='utf-8') as f:
                    self.adaptation_strategies = json.load(f)
            
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.adaptation_history = json.load(f)
            
            self.logger.info("适应引擎数据加载成功")
            
        except Exception as e:
            self.logger.error(f"加载适应引擎数据失败: {e}")
    
    def save_adaptation_data(self):
        """保存适应数据"""
        try:
            os.makedirs(self.adaptation_dir, exist_ok=True)
            
            # 保存配置
            config_file = os.path.join(self.adaptation_dir, "adaptation_config.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.adaptation_config, f, ensure_ascii=False, indent=2)
            
            # 保存策略库
            strategies_file = os.path.join(self.adaptation_dir, "adaptation_strategies.json")
            with open(strategies_file, 'w', encoding='utf-8') as f:
                json.dump(self.adaptation_strategies, f, ensure_ascii=False, indent=2)
            
            # 保存历史
            history_file = os.path.join(self.adaptation_dir, "adaptation_history.json")
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.adaptation_history, f, ensure_ascii=False, indent=2)
            
            self.logger.info("适应引擎数据保存成功")
            
        except Exception as e:
            self.logger.error(f"保存适应引擎数据失败: {e}")
    
    def analyze_environment(self, environment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析环境
        
        Args:
            environment_data: 环境数据
            
        Returns:
            环境分析结果
        """
        try:
            # 提取环境特征
            environment_features = self._extract_environment_features(environment_data)
            features_tensor = torch.FloatTensor(environment_features).unsqueeze(0).to(self.device)
            
            # 生成环境ID
            environment_id = self._generate_environment_id(environment_features)
            
            # 检测环境变化
            change_detection = self._detect_environment_change(environment_features)
            
            # 分析环境特性
            environment_analysis = self._analyze_environment_characteristics(environment_data)
            
            # 记录环境状态
            environment_record = {
                'environment_id': environment_id,
                'timestamp': datetime.now().isoformat(),
                'features': environment_features,
                'analysis': environment_analysis,
                'change_detection': change_detection
            }
            
            self.environment_history.append(environment_record)
            
            analysis_result = {
                'environment_id': environment_id,
                'environment_type': environment_analysis['type'],
                'stability': environment_analysis['stability'],
                'complexity': environment_analysis['complexity'],
                'change_detected': change_detection['change_detected'],
                'change_magnitude': change_detection['change_magnitude'],
                'recommended_adaptation': change_detection['recommended_action'],
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"环境分析完成: {environment_id} "
                           f"(类型: {environment_analysis['type']})")
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"环境分析失败: {e}")
            return self._get_fallback_analysis()
    
    def _extract_environment_features(self, environment_data: Dict[str, Any]) -> List[float]:
        """提取环境特征"""
        features = []
        
        # 任务特征
        task_info = environment_data.get('task', {})
        features.append(task_info.get('complexity', 0.5))
        features.append(task_info.get('novelty', 0.5))
        features.append(task_info.get('urgency', 0.5))
        
        # 用户特征
        user_context = environment_data.get('user_context', {})
        features.append(user_context.get('skill_level', 0.5))
        features.append(user_context.get('engagement', 0.5))
        features.append(user_context.get('preferences', 0.5))
        
        # 系统特征
        system_state = environment_data.get('system_state', {})
        features.append(system_state.get('resource_availability', 0.5))
        features.append(system_state.get('performance_level', 0.5))
        features.append(system_state.get('stability', 0.5))
        
        # 外部环境特征
        external_env = environment_data.get('external_environment', {})
        features.append(external_env.get('noise_level', 0.5))
        features.append(external_env.get('distraction_level', 0.5))
        
        # 填充到固定维度
        while len(features) < 256:
            features.append(0.0)
        features = features[:256]
        
        return features
    
    def _generate_environment_id(self, environment_features: List[float]) -> str:
        """生成环境ID"""
        # 使用特征哈希生成唯一ID
        features_str = ','.join(f"{f:.3f}" for f in environment_features[:10])  # 使用前10个特征
        features_hash = hashlib.md5(features_str.encode()).hexdigest()[:8]
        
        return f"env_{features_hash}_{datetime.now().strftime('%H%M%S')}"
    
    def _detect_environment_change(self, current_features: List[float]) -> Dict[str, Any]:
        """检测环境变化"""
        if len(self.environment_history) < 2:
            return {
                'change_detected': False,
                'change_magnitude': 0.0,
                'recommended_action': 'continue_current_strategy'
            }
        
        # 获取最近的环境状态
        previous_record = self.environment_history[-1]
        previous_features = previous_record['features']
        
        # 计算特征变化
        current_array = np.array(current_features)
        previous_array = np.array(previous_features)
        
        change_magnitude = np.linalg.norm(current_array - previous_array)
        
        # 使用神经网络检测变化
        current_tensor = torch.FloatTensor(current_features).unsqueeze(0).to(self.device)
        previous_tensor = torch.FloatTensor(previous_features).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            output = self.adaptation_net(current_tensor, previous_tensor)
            neural_change_score = output.get('change_score', torch.tensor([0.5])).item()
        
        # 结合两种变化检测方法
        combined_score = (change_magnitude + neural_change_score) / 2
        
        change_detected = combined_score > self.adaptation_config['change_detection_threshold']
        
        # 推荐行动
        if change_detected:
            if combined_score > 0.8:
                recommended_action = 'major_strategy_change'
            elif combined_score > 0.6:
                recommended_action = 'moderate_adaptation'
            else:
                recommended_action = 'minor_adjustment'
        else:
            recommended_action = 'continue_current_strategy'
        
        return {
            'change_detected': change_detected,
            'change_magnitude': combined_score,
            'feature_change': change_magnitude,
            'neural_change_score': neural_change_score,
            'recommended_action': recommended_action
        }
    
    def _analyze_environment_characteristics(self, environment_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析环境特性"""
        # 环境类型分类
        task_complexity = environment_data.get('task', {}).get('complexity', 0.5)
        novelty = environment_data.get('task', {}).get('novelty', 0.5)
        urgency = environment_data.get('task', {}).get('urgency', 0.5)
        
        # 确定环境类型
        if novelty > 0.7:
            env_type = 'novel'
        elif task_complexity > 0.7:
            env_type = 'complex'
        elif urgency > 0.7:
            env_type = 'time_sensitive'
        else:
            env_type = 'standard'
        
        # 稳定性评估
        system_stability = environment_data.get('system_state', {}).get('stability', 0.5)
        resource_stability = environment_data.get('system_state', {}).get('resource_availability', 0.5)
        stability_score = (system_stability + resource_stability) / 2
        
        # 复杂度评估
        complexity_score = (task_complexity + novelty) / 2
        
        return {
            'type': env_type,
            'stability': stability_score,
            'complexity': complexity_score,
            'predictability': 1.0 - novelty,  # 新颖性越低，可预测性越高
            'resource_intensity': environment_data.get('system_state', {}).get('resource_availability', 0.5)
        }
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """获取回退分析结果"""
        return {
            'environment_id': 'unknown',
            'environment_type': 'standard',
            'stability': 0.5,
            'complexity': 0.5,
            'change_detected': False,
            'change_magnitude': 0.0,
            'recommended_adaptation': 'continue_current_strategy',
            'timestamp': datetime.now().isoformat(),
            'fallback': True
        }
    
    def generate_adaptation_strategy(self, environment_analysis: Dict[str, Any],
                                  current_performance: float) -> Dict[str, Any]:
        """
        生成适应策略
        
        Args:
            environment_analysis: 环境分析结果
            current_performance: 当前性能水平
            
        Returns:
            适应策略
        """
        try:
            # 生成策略ID
            strategy_id = self._generate_strategy_id(environment_analysis, current_performance)
            
            # 基于环境分析生成策略
            base_strategy = self._create_base_strategy(environment_analysis)
            
            # 根据性能调整策略
            adapted_strategy = self._adapt_strategy_to_performance(base_strategy, current_performance)
            
            # 添加环境特定调整
            final_strategy = self._add_environment_specific_adjustments(adapted_strategy, environment_analysis)
            
            # 记录策略
            strategy_record = {
                'strategy_id': strategy_id,
                'environment_id': environment_analysis['environment_id'],
                'strategy_details': final_strategy,
                'generation_reason': self._explain_strategy_generation(environment_analysis, current_performance),
                'timestamp': datetime.now().isoformat(),
                'performance_context': current_performance
            }
            
            self.adaptation_strategies[strategy_id] = strategy_record
            
            self.logger.info(f"适应策略生成完成: {strategy_id}")
            return final_strategy
            
        except Exception as e:
            self.logger.error(f"生成适应策略失败: {e}")
            return self._get_fallback_strategy()
    
    def _generate_strategy_id(self, environment_analysis: Dict[str, Any], 
                            performance: float) -> str:
        """生成策略ID"""
        env_type = environment_analysis['environment_type']
        performance_level = 'high' if performance > 0.7 else 'medium' if performance > 0.4 else 'low'
        timestamp = datetime.now().strftime('%H%M%S')
        
        return f"strategy_{env_type}_{performance_level}_{timestamp}"
    
    def _create_base_strategy(self, environment_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """创建基础策略"""
        env_type = environment_analysis['environment_type']
        
        base_strategies = {
            'novel': {
                'exploration_rate': 0.3,
                'learning_rate': 0.01,
                'memory_usage': 'high',
                'risk_tolerance': 'medium',
                'adaptation_speed': 'fast',
                'focus': 'discovery_and_learning'
            },
            'complex': {
                'exploration_rate': 0.1,
                'learning_rate': 0.001,
                'memory_usage': 'very_high',
                'risk_tolerance': 'low',
                'adaptation_speed': 'slow',
                'focus': 'precision_and_analysis'
            },
            'time_sensitive': {
                'exploration_rate': 0.05,
                'learning_rate': 0.1,
                'memory_usage': 'medium',
                'risk_tolerance': 'high',
                'adaptation_speed': 'very_fast',
                'focus': 'efficiency_and_speed'
            },
            'standard': {
                'exploration_rate': 0.2,
                'learning_rate': 0.001,
                'memory_usage': 'medium',
                'risk_tolerance': 'medium',
                'adaptation_speed': 'moderate',
                'focus': 'balance_and_stability'
            }
        }
        
        return base_strategies.get(env_type, base_strategies['standard'])
    
    def _adapt_strategy_to_performance(self, base_strategy: Dict[str, Any], 
                                     performance: float) -> Dict[str, Any]:
        """根据性能调整策略"""
        adapted_strategy = base_strategy.copy()
        
        if performance < 0.4:
            # 低性能：增加探索，降低风险容忍度
            adapted_strategy['exploration_rate'] = min(adapted_strategy['exploration_rate'] + 0.2, 0.5)
            adapted_strategy['risk_tolerance'] = 'very_low'
            adapted_strategy['adaptation_speed'] = 'very_slow'
        elif performance > 0.8:
            # 高性能：减少探索，增加风险容忍度
            adapted_strategy['exploration_rate'] = max(adapted_strategy['exploration_rate'] - 0.1, 0.05)
            adapted_strategy['risk_tolerance'] = 'high'
            adapted_strategy['adaptation_speed'] = 'fast'
        
        return adapted_strategy
    
    def _add_environment_specific_adjustments(self, strategy: Dict[str, Any],
                                           environment_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """添加环境特定调整"""
        adjusted_strategy = strategy.copy()
        
        # 根据稳定性调整
        stability = environment_analysis['stability']
        if stability < 0.3:
            adjusted_strategy['adaptation_speed'] = 'very_fast'
            adjusted_strategy['memory_usage'] = 'low'  # 在不稳定环境中减少内存使用
        elif stability > 0.8:
            adjusted_strategy['adaptation_speed'] = 'slow'
            adjusted_strategy['memory_usage'] = 'high'
        
        # 根据复杂度调整
        complexity = environment_analysis['complexity']
        if complexity > 0.7:
            adjusted_strategy['learning_rate'] = adjusted_strategy['learning_rate'] * 0.5
            adjusted_strategy['risk_tolerance'] = 'very_low'
        
        return adjusted_strategy
    
    def _explain_strategy_generation(self, environment_analysis: Dict[str, Any],
                                   performance: float) -> str:
        """解释策略生成原因"""
        env_type = environment_analysis['environment_type']
        performance_level = 'high' if performance > 0.7 else 'medium' if performance > 0.4 else 'low'
        
        explanations = {
            ('novel', 'low'): "在新颖环境中表现不佳，采用高探索策略以学习新知识",
            ('novel', 'medium'): "在新颖环境中表现中等，平衡探索和利用",
            ('novel', 'high'): "在新颖环境中表现出色，适度探索以发现新机会",
            ('complex', 'low'): "在复杂环境中表现不佳，采用谨慎的慢速学习策略",
            ('complex', 'medium'): "在复杂环境中表现中等，注重精确分析",
            ('complex', 'high'): "在复杂环境中表现出色，可以适度加快学习速度",
            ('time_sensitive', 'low'): "在时间敏感环境中表现不佳，需要快速调整策略",
            ('time_sensitive', 'medium'): "在时间敏感环境中表现中等，注重效率",
            ('time_sensitive', 'high'): "在时间敏感环境中表现出色，可以承担更高风险"
        }
        
        return explanations.get((env_type, performance_level), 
                              "基于当前环境和性能水平调整策略")
    
    def _get_fallback_strategy(self) -> Dict[str, Any]:
        """获取回退策略"""
        return {
            'exploration_rate': 0.2,
            'learning_rate': 0.001,
            'memory_usage': 'medium',
            'risk_tolerance': 'medium',
            'adaptation_speed': 'moderate',
            'focus': 'stability_and_reliability',
            'fallback': True
        }
    
    def execute_adaptation(self, strategy: Dict[str, Any], 
                         system_components: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行适应
        
        Args:
            strategy: 适应策略
            system_components: 系统组件配置
            
        Returns:
            适应执行结果
        """
        try:
            adaptation_id = f"adapt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 应用策略到系统组件
            adaptation_actions = self._apply_strategy_to_components(strategy, system_components)
            
            # 记录适应执行
            adaptation_record = {
                'adaptation_id': adaptation_id,
                'strategy_applied': strategy,
                'actions_taken': adaptation_actions,
                'timestamp': datetime.now().isoformat(),
                'status': 'completed'
            }
            
            self.adaptation_history.append(adaptation_record)
            self.adaptation_count += 1
            self.last_adaptation_time = datetime.now()
            
            self.logger.info(f"适应执行完成: {adaptation_id}")
            return adaptation_record
            
        except Exception as e:
            self.logger.error(f"执行适应失败: {e}")
            return {
                'adaptation_id': 'failed',
                'error': str(e),
                'status': 'failed',
                'timestamp': datetime.now().isoformat()
            }
    
    def _apply_strategy_to_components(self, strategy: Dict[str, Any],
                                   components: Dict[str, Any]) -> List[Dict[str, Any]]:
        """应用策略到系统组件"""
        actions = []
        
        # 应用到学习系统
        if 'learning_system' in components:
            learning_actions = self._adapt_learning_system(strategy, components['learning_system'])
            actions.extend(learning_actions)
        
        # 应用到推理系统
        if 'reasoning_system' in components:
            reasoning_actions = self._adapt_reasoning_system(strategy, components['reasoning_system'])
            actions.extend(reasoning_actions)
        
        # 应用到记忆系统
        if 'memory_system' in components:
            memory_actions = self._adapt_memory_system(strategy, components['memory_system'])
            actions.extend(memory_actions)
        
        return actions
    
    def _adapt_learning_system(self, strategy: Dict[str, Any], 
                             learning_system: Dict[str, Any]) -> List[Dict[str, Any]]:
        """适应学习系统"""
        actions = []
        
        # 调整学习率
        if 'learning_rate' in strategy:
            new_lr = strategy['learning_rate']
            actions.append({
                'component': 'learning_system',
                'action': 'adjust_learning_rate',
                'parameter': 'learning_rate',
                'old_value': learning_system.get('learning_rate', 0.001),
                'new_value': new_lr,
                'reason': f"策略要求的学习率: {new_lr}"
            })
        
        # 调整探索率
        if 'exploration_rate' in strategy:
            new_exploration = strategy['exploration_rate']
            actions.append({
                'component': 'learning_system',
                'action': 'adjust_exploration_rate',
                'parameter': 'exploration_rate',
                'old_value': learning_system.get('exploration_rate', 0.1),
                'new_value': new_exploration,
                'reason': f"策略要求的探索率: {new_exploration}"
            })
        
        return actions
    
    def _adapt_reasoning_system(self, strategy: Dict[str, Any],
                              reasoning_system: Dict[str, Any]) -> List[Dict[str, Any]]:
        """适应推理系统"""
        actions = []
        
        # 调整推理深度
        if strategy.get('focus') in ['precision_and_analysis', 'discovery_and_learning']:
            new_depth = 'deep'
        elif strategy.get('focus') in ['efficiency_and_speed']:
            new_depth = 'shallow'
        else:
            new_depth = 'balanced'
        
        actions.append({
            'component': 'reasoning_system',
            'action': 'adjust_reasoning_depth',
            'parameter': 'reasoning_depth',
            'old_value': reasoning_system.get('reasoning_depth', 'balanced'),
            'new_value': new_depth,
            'reason': f"策略焦点: {strategy.get('focus')}"
        })
        
        return actions
    
    def _adapt_memory_system(self, strategy: Dict[str, Any],
                           memory_system: Dict[str, Any]) -> List[Dict[str, Any]]:
        """适应记忆系统"""
        actions = []
        
        # 调整内存使用策略
        memory_usage = strategy.get('memory_usage', 'medium')
        if memory_usage == 'very_high':
            new_policy = 'aggressive_caching'
        elif memory_usage == 'high':
            new_policy = 'standard_caching'
        elif memory_usage == 'low':
            new_policy = 'minimal_caching'
        else:  # medium
            new_policy = 'balanced_caching'
        
        actions.append({
            'component': 'memory_system',
            'action': 'adjust_caching_policy',
            'parameter': 'caching_policy',
            'old_value': memory_system.get('caching_policy', 'balanced_caching'),
            'new_value': new_policy,
            'reason': f"策略要求的内存使用: {memory_usage}"
        })
        
        return actions
    
    def evaluate_adaptation_effectiveness(self, adaptation_id: str,
                                       performance_before: float,
                                       performance_after: float) -> Dict[str, Any]:
        """
        评估适应效果
        
        Args:
            adaptation_id: 适应ID
            performance_before: 适应前性能
            performance_after: 适应后性能
            
        Returns:
            效果评估结果
        """
        improvement = performance_after - performance_before
        improvement_percentage = (improvement / performance_before) * 100 if performance_before > 0 else 0
        
        effectiveness = 'high' if improvement > 0.1 else 'medium' if improvement > 0.05 else 'low'
        
        # 查找适应记录
        adaptation_record = None
        for record in self.adaptation_history:
            if record.get('adaptation_id') == adaptation_id:
                adaptation_record = record
                break
        
        evaluation_result = {
            'adaptation_id': adaptation_id,
            'performance_before': performance_before,
            'performance_after': performance_after,
            'improvement': improvement,
            'improvement_percentage': improvement_percentage,
            'effectiveness': effectiveness,
            'evaluation_timestamp': datetime.now().isoformat()
        }
        
        if adaptation_record:
            adaptation_record['effectiveness_evaluation'] = evaluation_result
        
        self.logger.info(f"适应效果评估: {adaptation_id} "
                       f"(改进: {improvement_percentage:+.1f}%)")
        
        return evaluation_result
    
    def get_adaptation_analytics(self) -> Dict[str, Any]:
        """获取适应分析"""
        total_adaptations = len(self.adaptation_history)
        
        if total_adaptations == 0:
            return {'message': '尚无适应记录'}
        
        # 计算适应效果统计
        effectiveness_scores = []
        improvements = []
        
        for record in self.adaptation_history:
            evaluation = record.get('effectiveness_evaluation')
            if evaluation:
                effectiveness_scores.append({
                    'high': 1.0,
                    'medium': 0.5,
                    'low': 0.0
                }[evaluation['effectiveness']])
                improvements.append(evaluation['improvement'])
        
        analytics = {
            'total_adaptations': total_adaptations,
            'successful_adaptations': len([r for r in self.adaptation_history 
                                         if r.get('status') == 'completed']),
            'average_effectiveness': np.mean(effectiveness_scores) if effectiveness_scores else 0.0,
            'average_improvement': np.mean(improvements) if improvements else 0.0,
            'most_effective_strategy_type': self._find_most_effective_strategy(),
            'adaptation_frequency': self._calculate_adaptation_frequency(),
            'recent_environment_changes': len([r for r in self.environment_history 
                                            if r.get('change_detection', {}).get('change_detected', False)])
        }
        
        return analytics
    
    def _find_most_effective_strategy(self) -> str:
        """找到最有效的策略类型"""
        if not self.adaptation_history:
            return 'unknown'
        
        strategy_effectiveness = defaultdict(list)
        
        for record in self.adaptation_history:
            evaluation = record.get('effectiveness_evaluation')
            strategy = record.get('strategy_applied', {})
            env_type = strategy.get('focus', 'unknown')
            
            if evaluation:
                effectiveness_score = {
                    'high': 1.0,
                    'medium': 0.5,
                    'low': 0.0
                }[evaluation['effectiveness']]
                strategy_effectiveness[env_type].append(effectiveness_score)
        
        # 计算平均效果
        avg_effectiveness = {}
        for env_type, scores in strategy_effectiveness.items():
            avg_effectiveness[env_type] = np.mean(scores)
        
        return max(avg_effectiveness.items(), key=lambda x: x[1])[0] if avg_effectiveness else 'unknown'
    
    def _calculate_adaptation_frequency(self) -> str:
        """计算适应频率"""
        if len(self.adaptation_history) < 2:
            return 'low'
        
        # 计算平均适应间隔
        timestamps = []
        for record in self.adaptation_history:
            if 'timestamp' in record:
                try:
                    ts = datetime.fromisoformat(record['timestamp'])
                    timestamps.append(ts.timestamp())
                except:
                    continue
        
        if len(timestamps) < 2:
            return 'low'
        
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        avg_interval_hours = np.mean(intervals) / 3600
        
        if avg_interval_hours < 1:
            return 'very_high'
        elif avg_interval_hours < 6:
            return 'high'
        elif avg_interval_hours < 24:
            return 'medium'
        else:
            return 'low'

# 全局适应引擎实例
_global_adaptation_engine: Optional[AdaptationEngine] = None

def get_adaptation_engine() -> AdaptationEngine:
    """获取全局适应引擎实例"""
    global _global_adaptation_engine
    if _global_adaptation_engine is None:
        _global_adaptation_engine = AdaptationEngine()
    return _global_adaptation_engine

