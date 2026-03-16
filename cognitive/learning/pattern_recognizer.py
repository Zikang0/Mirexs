# cognitive/learning/pattern_recognizer.py
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
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

class PatternRecognitionNetwork(nn.Module):
    """模式识别神经网络"""
    
    def __init__(self, input_dim: int = 512, hidden_dims: List[int] = [1024, 512, 256]):
        super(PatternRecognitionNetwork, self).__init__()
        self.input_dim = input_dim
        
        # 编码器层
        encoder_layers = []
        prev_dim = input_dim
        for hidden_dim in hidden_dims:
            encoder_layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.2)
            ])
            prev_dim = hidden_dim
        
        self.encoder = nn.Sequential(*encoder_layers)
        
        # 模式提取层
        self.pattern_extractor = nn.Sequential(
            nn.Linear(hidden_dims[-1], 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.Tanh()
        )
        
        # 模式分类器
        self.pattern_classifier = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16),  # 16种基础模式类型
            nn.Softmax(dim=-1)
        )
        
        # 异常检测层
        self.anomaly_detector = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        encoded = self.encoder(x)
        pattern_features = self.pattern_extractor(encoded)
        pattern_type = self.pattern_classifier(pattern_features)
        anomaly_score = self.anomaly_detector(pattern_features)
        
        return {
            'pattern_features': pattern_features,
            'pattern_type': pattern_type,
            'anomaly_score': anomaly_score,
            'encoded_features': encoded
        }

class PatternRecognizer:
    """模式识别：识别用户行为模式"""
    
    def __init__(self, patterns_dir: str = "data/patterns"):
        self.patterns_dir = patterns_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = self._setup_logger()
        
        # 初始化模式识别模型
        self.model = PatternRecognitionNetwork().to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.0001)
        
        # 模式库
        self.pattern_library: Dict[str, Dict] = {}
        self.pattern_clusters: Dict[str, Any] = {}
        self.behavior_sequences: deque = deque(maxlen=1000)
        
        # 模式统计
        self.pattern_stats = defaultdict(lambda: {
            'detection_count': 0,
            'last_detected': None,
            'confidence_history': [],
            'contexts': set()
        })
        
        # 聚类分析器
        self.cluster_analyzer = DBSCAN(eps=0.5, min_samples=3)
        self.feature_scaler = StandardScaler()
        
        # 加载现有模式
        self._load_patterns()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('pattern_recognizer')
        if not logger.handlers:
            handler = logging.FileHandler('logs/pattern_recognition.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _load_patterns(self):
        """加载已识别的模式"""
        patterns_file = os.path.join(self.patterns_dir, "pattern_library.json")
        clusters_file = os.path.join(self.patterns_dir, "pattern_clusters.npy")
        stats_file = os.path.join(self.patterns_dir, "pattern_stats.json")
        
        try:
            if os.path.exists(patterns_file):
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    self.pattern_library = json.load(f)
            
            if os.path.exists(clusters_file):
                loaded_data = np.load(clusters_file, allow_pickle=True).item()
                self.pattern_clusters = loaded_data.get('clusters', {})
                if 'scaler_params' in loaded_data:
                    self.feature_scaler.mean_ = loaded_data['scaler_params']['mean']
                    self.feature_scaler.scale_ = loaded_data['scaler_params']['scale']
                    self.feature_scaler.var_ = loaded_data['scaler_params']['var']
                    self.feature_scaler.n_features_in_ = loaded_data['scaler_params']['n_features_in']
            
            if os.path.exists(stats_file):
                with open(stats_file, 'r', encoding='utf-8') as f:
                    loaded_stats = json.load(f)
                    # 转换回 defaultdict
                    for key, value in loaded_stats.items():
                        self.pattern_stats[key] = value
            
            self.logger.info(f"模式库加载成功，共{len(self.pattern_library)}个模式")
            
        except Exception as e:
            self.logger.error(f"加载模式库失败: {e}")
    
    def save_patterns(self):
        """保存模式库"""
        os.makedirs(self.patterns_dir, exist_ok=True)
        
        try:
            # 保存模式库
            patterns_file = os.path.join(self.patterns_dir, "pattern_library.json")
            with open(patterns_file, 'w', encoding='utf-8') as f:
                json.dump(self.pattern_library, f, ensure_ascii=False, indent=2)
            
            # 保存聚类数据
            clusters_file = os.path.join(self.patterns_dir, "pattern_clusters.npy")
            scaler_params = {
                'mean': self.feature_scaler.mean_ if hasattr(self.feature_scaler, 'mean_') else None,
                'scale': self.feature_scaler.scale_ if hasattr(self.feature_scaler, 'scale_') else None,
                'var': self.feature_scaler.var_ if hasattr(self.feature_scaler, 'var_') else None,
                'n_features_in': self.feature_scaler.n_features_in_ if hasattr(self.feature_scaler, 'n_features_in_') else None
            }
            np.save(clusters_file, {
                'clusters': self.pattern_clusters,
                'scaler_params': scaler_params
            })
            
            # 保存统计信息
            stats_file = os.path.join(self.patterns_dir, "pattern_stats.json")
            with open(stats_file, 'w', encoding='utf-8') as f:
                # 转换set为list以便JSON序列化
                serializable_stats = {}
                for key, value in self.pattern_stats.items():
                    serializable_value = value.copy()
                    serializable_value['contexts'] = list(value['contexts'])
                    serializable_stats[key] = serializable_value
                json.dump(serializable_stats, f, ensure_ascii=False, indent=2)
            
            self.logger.info("模式库保存成功")
            
        except Exception as e:
            self.logger.error(f"保存模式库失败: {e}")
    
    def analyze_behavior_sequence(self, behavior_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析行为序列，识别模式
        
        Args:
            behavior_data: 行为数据，包含动作序列、时间戳、上下文等信息
            
        Returns:
            模式识别结果
        """
        try:
            # 提取行为特征
            behavior_features = self._extract_behavior_features(behavior_data)
            feature_tensor = torch.FloatTensor(behavior_features).unsqueeze(0).to(self.device)
            
            # 模型推理
            self.model.eval()
            with torch.no_grad():
                outputs = self.model(feature_tensor)
            
            # 解析结果
            pattern_type_idx = torch.argmax(outputs['pattern_type'][0]).item()
            pattern_type = self._get_pattern_type_name(pattern_type_idx)
            anomaly_score = float(outputs['anomaly_score'][0])
            confidence = float(torch.max(outputs['pattern_type'][0]))
            
            # 检查是否为已知模式
            known_pattern = self._match_known_patterns(behavior_features, outputs['pattern_features'][0])
            
            # 构建结果
            analysis_result = {
                'pattern_type': pattern_type,
                'pattern_type_idx': pattern_type_idx,
                'anomaly_score': anomaly_score,
                'confidence': confidence,
                'is_known_pattern': known_pattern is not None,
                'known_pattern_id': known_pattern,
                'pattern_features': outputs['pattern_features'][0].cpu().numpy().tolist(),
                'timestamp': datetime.now().isoformat()
            }
            
            # 如果是新模式或高置信度模式，进行记录
            if confidence > 0.7 or anomaly_score > 0.8:
                self._record_pattern(behavior_data, analysis_result)
            
            # 更新行为序列
            self.behavior_sequences.append({
                'behavior_data': behavior_data,
                'analysis_result': analysis_result,
                'timestamp': datetime.now().isoformat()
            })
            
            # 定期进行聚类分析
            if len(self.behavior_sequences) % 50 == 0:
                self._perform_clustering_analysis()
            
            self.logger.info(f"行为模式分析完成: {pattern_type} (置信度: {confidence:.3f})")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"行为模式分析失败: {e}")
            return self._get_fallback_analysis()
    
    def _extract_behavior_features(self, behavior_data: Dict[str, Any]) -> List[float]:
        """从行为数据中提取特征"""
        features = []
        
        # 动作序列特征
        actions = behavior_data.get('actions', [])
        features.append(len(actions))  # 序列长度
        
        # 动作类型分布
        action_types = [action.get('type', 'unknown') for action in actions]
        unique_types = set(action_types)
        features.append(len(unique_types))  # 动作多样性
        
        # 时间特征
        timestamps = behavior_data.get('timestamps', [])
        if len(timestamps) >= 2:
            time_intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
            features.append(np.mean(time_intervals) if time_intervals else 0.0)
            features.append(np.std(time_intervals) if time_intervals else 0.0)
        else:
            features.extend([0.0, 0.0])
        
        # 上下文特征
        context = behavior_data.get('context', {})
        features.append(context.get('complexity', 0.5))
        features.append(context.get('urgency', 0.5))
        features.append(context.get('familiarity', 0.5))
        
        # 结果特征
        result = behavior_data.get('result', {})
        features.append(result.get('success', 0.0))
        features.append(result.get('efficiency', 0.0))
        
        # 填充到固定维度
        while len(features) < 512:
            features.append(0.0)
        features = features[:512]
        
        return features
    
    def _get_pattern_type_name(self, type_idx: int) -> str:
        """获取模式类型名称"""
        pattern_types = [
            'sequential_linear',      # 顺序线性模式
            'exploratory_random',     # 探索随机模式
            'focused_repetitive',     # 专注重复模式
            'multitasking_parallel',  # 多任务并行模式
            'adaptive_flexible',      # 自适应灵活模式
            'conservative_cautious',  # 保守谨慎模式
            'innovative_creative',    # 创新创造模式
            'systematic_methodical',  # 系统方法模式
            'emotional_reactive',     # 情绪反应模式
            'strategic_planned',      # 战略计划模式
            'quick_decisive',         # 快速决策模式
            'detailed_analytical',    # 详细分析模式
            'social_interactive',     # 社交互动模式
            'independent_autonomous', # 独立自主模式
            'learning_adaptive',      # 学习适应模式
            'habitual_automatic'      # 习惯自动模式
        ]
        
        return pattern_types[type_idx % len(pattern_types)]
    
    def _match_known_patterns(self, behavior_features: List[float], 
                            pattern_features: torch.Tensor) -> Optional[str]:
        """匹配已知模式"""
        if not self.pattern_library:
            return None
        
        best_match_id = None
        best_similarity = 0.0
        similarity_threshold = 0.8
        
        pattern_features_np = pattern_features.cpu().numpy()
        
        for pattern_id, pattern_data in self.pattern_library.items():
            stored_features = np.array(pattern_data.get('pattern_features', []))
            
            if len(stored_features) == len(pattern_features_np):
                similarity = self._calculate_feature_similarity(pattern_features_np, stored_features)
                
                if similarity > best_similarity and similarity > similarity_threshold:
                    best_similarity = similarity
                    best_match_id = pattern_id
        
        return best_match_id
    
    def _calculate_feature_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """计算特征相似度"""
        if len(features1) != len(features2):
            return 0.0
        
        # 余弦相似度
        dot_product = np.dot(features1, features2)
        norm1 = np.linalg.norm(features1)
        norm2 = np.linalg.norm(features2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _record_pattern(self, behavior_data: Dict[str, Any], analysis_result: Dict[str, Any]):
        """记录识别到的模式"""
        pattern_id = self._generate_pattern_id(behavior_data, analysis_result)
        
        pattern_data = {
            'pattern_type': analysis_result['pattern_type'],
            'pattern_features': analysis_result['pattern_features'],
            'behavior_characteristics': self._extract_behavior_characteristics(behavior_data),
            'context': behavior_data.get('context', {}),
            'first_detected': datetime.now().isoformat(),
            'last_detected': datetime.now().isoformat(),
            'detection_count': 1,
            'average_confidence': analysis_result['confidence'],
            'anomaly_score': analysis_result['anomaly_score']
        }
        
        # 如果模式已存在，更新统计信息
        if pattern_id in self.pattern_library:
            existing_data = self.pattern_library[pattern_id]
            existing_data['last_detected'] = pattern_data['last_detected']
            existing_data['detection_count'] += 1
            # 更新平均置信度
            current_avg = existing_data['average_confidence']
            new_count = existing_data['detection_count']
            existing_data['average_confidence'] = (
                current_avg * (new_count - 1) + analysis_result['confidence']
            ) / new_count
        else:
            self.pattern_library[pattern_id] = pattern_data
        
        # 更新模式统计
        self.pattern_stats[pattern_id]['detection_count'] += 1
        self.pattern_stats[pattern_id]['last_detected'] = datetime.now().isoformat()
        self.pattern_stats[pattern_id]['confidence_history'].append(analysis_result['confidence'])
        self.pattern_stats[pattern_id]['contexts'].add(behavior_data.get('context', {}).get('type', 'unknown'))
        
        self.logger.info(f"模式记录完成: {pattern_id}")
    
    def _generate_pattern_id(self, behavior_data: Dict[str, Any], 
                           analysis_result: Dict[str, Any]) -> str:
        """生成模式ID"""
        pattern_type = analysis_result['pattern_type']
        context_type = behavior_data.get('context', {}).get('type', 'general')
        timestamp = datetime.now().strftime('%Y%m%d')
        features_hash = hash(str(analysis_result['pattern_features'][:10]))
        
        return f"{pattern_type}_{context_type}_{timestamp}_{abs(features_hash) % 10000:04d}"
    
    def _extract_behavior_characteristics(self, behavior_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取行为特征"""
        actions = behavior_data.get('actions', [])
        
        return {
            'action_count': len(actions),
            'action_types': list(set(action.get('type', 'unknown') for action in actions)),
            'average_duration': behavior_data.get('duration', 0) / max(len(actions), 1),
            'success_rate': behavior_data.get('result', {}).get('success', 0.0),
            'efficiency': behavior_data.get('result', {}).get('efficiency', 0.0),
            'complexity': behavior_data.get('context', {}).get('complexity', 0.5)
        }
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """获取回退分析结果"""
        return {
            'pattern_type': 'unknown',
            'pattern_type_idx': -1,
            'anomaly_score': 0.5,
            'confidence': 0.0,
            'is_known_pattern': False,
            'known_pattern_id': None,
            'pattern_features': [0.0] * 64,
            'timestamp': datetime.now().isoformat()
        }
    
    def _perform_clustering_analysis(self):
        """执行聚类分析"""
        try:
            if len(self.behavior_sequences) < 10:
                return
            
            # 提取所有模式特征
            all_features = []
            valid_sequences = []
            
            for seq in self.behavior_sequences:
                features = seq['analysis_result']['pattern_features']
                if len(features) == 64:  # 确保特征维度正确
                    all_features.append(features)
                    valid_sequences.append(seq)
            
            if len(all_features) < 10:
                return
            
            # 标准化特征
            features_array = np.array(all_features)
            if hasattr(self.feature_scaler, 'n_features_in_'):
                scaled_features = self.feature_scaler.transform(features_array)
            else:
                scaled_features = self.feature_scaler.fit_transform(features_array)
            
            # 执行聚类
            clusters = self.cluster_analyzer.fit_predict(scaled_features)
            
            # 分析聚类结果
            unique_clusters = set(clusters)
            cluster_info = {}
            
            for cluster_id in unique_clusters:
                if cluster_id == -1:
                    continue  # 跳过噪声点
                
                cluster_indices = np.where(clusters == cluster_id)[0]
                cluster_sequences = [valid_sequences[i] for i in cluster_indices]
                
                # 分析聚类特征
                cluster_features = features_array[cluster_indices]
                centroid = np.mean(cluster_features, axis=0)
                
                cluster_info[cluster_id] = {
                    'size': len(cluster_indices),
                    'centroid': centroid.tolist(),
                    'patterns': [seq['analysis_result']['pattern_type'] for seq in cluster_sequences],
                    'average_confidence': np.mean([seq['analysis_result']['confidence'] for seq in cluster_sequences]),
                    'representative_sequences': cluster_sequences[:5]  # 前5个代表序列
                }
            
            self.pattern_clusters = cluster_info
            self.logger.info(f"聚类分析完成，发现 {len(cluster_info)} 个聚类")
            
        except Exception as e:
            self.logger.error(f"聚类分析失败: {e}")
    
    def predict_behavior(self, current_context: Dict[str, Any], 
                        history_length: int = 5) -> Dict[str, Any]:
        """
        预测未来行为
        
        Args:
            current_context: 当前上下文
            history_length: 使用的历史长度
            
        Returns:
            行为预测结果
        """
        try:
            # 获取最近的行为历史
            recent_sequences = list(self.behavior_sequences)[-history_length:]
            
            if not recent_sequences:
                return {'prediction': 'insufficient_data', 'confidence': 0.0}
            
            # 分析历史模式
            historical_patterns = [seq['analysis_result']['pattern_type'] for seq in recent_sequences]
            pattern_transitions = self._analyze_pattern_transitions(historical_patterns)
            
            # 预测下一个模式
            next_pattern = self._predict_next_pattern(historical_patterns, pattern_transitions)
            
            # 基于当前上下文和预测模式生成具体预测
            behavior_prediction = self._generate_behavior_prediction(next_pattern, current_context)
            
            prediction_result = {
                'predicted_pattern': next_pattern['pattern'],
                'confidence': next_pattern['confidence'],
                'expected_actions': behavior_prediction['actions'],
                'likely_outcomes': behavior_prediction['outcomes'],
                'recommended_responses': behavior_prediction['responses'],
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"行为预测完成: {next_pattern['pattern']} (置信度: {next_pattern['confidence']:.3f})")
            return prediction_result
            
        except Exception as e:
            self.logger.error(f"行为预测失败: {e}")
            return {'prediction': 'error', 'confidence': 0.0}
    
    def _analyze_pattern_transitions(self, historical_patterns: List[str]) -> Dict[str, Dict[str, float]]:
        """分析模式转移概率"""
        transitions = defaultdict(lambda: defaultdict(int))
        
        # 统计模式转移
        for i in range(len(historical_patterns) - 1):
            current = historical_patterns[i]
            next_pattern = historical_patterns[i + 1]
            transitions[current][next_pattern] += 1
        
        # 计算概率
        transition_probs = {}
        for current, next_patterns in transitions.items():
            total = sum(next_patterns.values())
            transition_probs[current] = {
                next_p: count / total for next_p, count in next_patterns.items()
            }
        
        return transition_probs
    
    def _predict_next_pattern(self, historical_patterns: List[str], 
                            transition_probs: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """预测下一个模式"""
        if not historical_patterns:
            return {'pattern': 'exploratory_random', 'confidence': 0.5}
        
        current_pattern = historical_patterns[-1]
        
        if current_pattern in transition_probs and transition_probs[current_pattern]:
            # 找到最可能的下一模式
            next_patterns = transition_probs[current_pattern]
            most_likely = max(next_patterns.items(), key=lambda x: x[1])
            
            return {
                'pattern': most_likely[0],
                'confidence': most_likely[1],
                'alternative_patterns': dict(sorted(next_patterns.items(), key=lambda x: x[1], reverse=True)[:3])
            }
        else:
            # 没有历史转移数据，返回默认预测
            return {
                'pattern': 'adaptive_flexible',
                'confidence': 0.3,
                'alternative_patterns': {'exploratory_random': 0.3, 'sequential_linear': 0.2}
            }
    
    def _generate_behavior_prediction(self, pattern_prediction: Dict[str, Any], 
                                    context: Dict[str, Any]) -> Dict[str, Any]:
        """生成具体的行为预测"""
        pattern_type = pattern_prediction['pattern']
        confidence = pattern_prediction['confidence']
        
        # 基于模式类型生成预测
        prediction_templates = {
            'sequential_linear': {
                'actions': ['计划下一步', '按顺序执行', '检查进度'],
                'outcomes': ['任务完成', '进度稳定', '可预测结果'],
                'responses': ['提供清晰指引', '确认当前步骤', '鼓励持续进行']
            },
            'exploratory_random': {
                'actions': ['尝试新方法', '测试不同选项', '收集信息'],
                'outcomes': ['可能发现新方案', '学习新知识', '结果不确定'],
                'responses': ['提供探索空间', '鼓励创新', '帮助分析结果']
            },
            'focused_repetitive': {
                'actions': ['重复优化', '深入分析', '精炼细节'],
                'outcomes': ['质量提高', '效率提升', '可能遇到瓶颈'],
                'responses': ['提供反馈', '建议休息', '介绍新视角']
            },
            'adaptive_flexible': {
                'actions': ['调整策略', '整合信息', '多任务处理'],
                'outcomes': ['适应变化', '平衡多个目标', '灵活应对'],
                'responses': ['支持调整', '提供资源', '帮助优先级排序']
            }
        }
        
        # 获取模板或使用默认
        template = prediction_templates.get(pattern_type, {
            'actions': ['评估情况', '做出决策', '执行行动'],
            'outcomes': ['任务进展', '学习发生', '体验积累'],
            'responses': ['观察支持', '提供帮助', '鼓励反思']
        })
        
        # 根据置信度调整预测
        if confidence < 0.5:
            template['actions'].insert(0, '谨慎评估')
            template['outcomes'].append('结果不确定')
        
        return template
    
    def get_pattern_insights(self) -> Dict[str, Any]:
        """获取模式识别洞察"""
        total_patterns = len(self.pattern_library)
        pattern_type_distribution = defaultdict(int)
        confidence_stats = defaultdict(list)
        
        for pattern_id, pattern_data in self.pattern_library.items():
            pattern_type = pattern_data['pattern_type']
            pattern_type_distribution[pattern_type] += 1
            confidence_stats[pattern_type].append(pattern_data['average_confidence'])
        
        # 计算平均置信度
        avg_confidence_by_type = {}
        for pattern_type, confidences in confidence_stats.items():
            avg_confidence_by_type[pattern_type] = np.mean(confidences)
        
        insights = {
            'total_identified_patterns': total_patterns,
            'pattern_type_distribution': dict(pattern_type_distribution),
            'average_confidence_by_type': avg_confidence_by_type,
            'most_common_patterns': self._get_most_common_patterns(5),
            'recent_pattern_trends': self._analyze_recent_trends(),
            'cluster_analysis': {
                'total_clusters': len(self.pattern_clusters),
                'cluster_sizes': [info['size'] for info in self.pattern_clusters.values()]
            }
        }
        
        return insights
    
    def _get_most_common_patterns(self, top_n: int) -> List[Dict[str, Any]]:
        """获取最常见的模式"""
        patterns_with_counts = []
        
        for pattern_id, pattern_data in self.pattern_library.items():
            patterns_with_counts.append({
                'pattern_id': pattern_id,
                'pattern_type': pattern_data['pattern_type'],
                'detection_count': pattern_data['detection_count'],
                'average_confidence': pattern_data['average_confidence'],
                'last_detected': pattern_data['last_detected']
            })
        
        # 按检测次数排序
        patterns_with_counts.sort(key=lambda x: x['detection_count'], reverse=True)
        return patterns_with_counts[:top_n]
    
    def _analyze_recent_trends(self) -> Dict[str, Any]:
        """分析近期模式趋势"""
        if len(self.behavior_sequences) < 10:
            return {'trend': 'insufficient_data'}
        
        recent_sequences = list(self.behavior_sequences)[-20:]  # 最近20个序列
        recent_patterns = [seq['analysis_result']['pattern_type'] for seq in recent_sequences]
        
        # 分析模式变化
        pattern_changes = []
        for i in range(1, len(recent_patterns)):
            if recent_patterns[i] != recent_patterns[i-1]:
                pattern_changes.append((recent_patterns[i-1], recent_patterns[i]))
        
        trend_analysis = {
            'total_recent_sequences': len(recent_sequences),
            'pattern_stability': 1.0 - (len(pattern_changes) / len(recent_sequences)),
            'recent_patterns': recent_patterns[-5:],  # 最近5个模式
            'pattern_transitions': pattern_changes[-5:] if pattern_changes else []
        }
        
        return trend_analysis
    
    def detect_anomalous_behavior(self, behavior_data: Dict[str, Any], 
                                threshold: float = 0.8) -> Dict[str, Any]:
        """
        检测异常行为
        
        Args:
            behavior_data: 行为数据
            threshold: 异常阈值
            
        Returns:
            异常检测结果
        """
        analysis_result = self.analyze_behavior_sequence(behavior_data)
        anomaly_score = analysis_result['anomaly_score']
        
        is_anomalous = anomaly_score > threshold
        anomaly_type = self._classify_anomaly_type(behavior_data, analysis_result)
        
        detection_result = {
            'is_anomalous': is_anomalous,
            'anomaly_score': anomaly_score,
            'anomaly_type': anomaly_type,
            'confidence': analysis_result['confidence'],
            'explanation': self._generate_anomaly_explanation(anomaly_type, behavior_data),
            'recommended_action': self._suggest_anomaly_response(anomaly_type),
            'timestamp': datetime.now().isoformat()
        }
        
        if is_anomalous:
            self.logger.warning(f"检测到异常行为: {anomaly_type} (分数: {anomaly_score:.3f})")
        
        return detection_result
    
    def _classify_anomaly_type(self, behavior_data: Dict[str, Any], 
                             analysis_result: Dict[str, Any]) -> str:
        """分类异常类型"""
        anomaly_score = analysis_result['anomaly_score']
        pattern_type = analysis_result['pattern_type']
        
        if anomaly_score > 0.9:
            return 'severe_anomaly'
        elif anomaly_score > 0.7:
            return 'moderate_anomaly'
        else:
            return 'minor_deviation'
    
    def _generate_anomaly_explanation(self, anomaly_type: str, 
                                    behavior_data: Dict[str, Any]) -> str:
        """生成异常解释"""
        explanations = {
            'severe_anomaly': '检测到严重偏离正常行为模式，可能与系统故障或异常情况相关',
            'moderate_anomaly': '行为模式出现显著变化，可能与学习阶段转换或环境变化相关',
            'minor_deviation': '检测到轻微的行为变化，属于正常的学习和适应过程'
        }
        
        return explanations.get(anomaly_type, '检测到行为模式变化')

    def _suggest_anomaly_response(self, anomaly_type: str) -> str:
        """建议异常响应"""
        responses = {
            'severe_anomaly': '立即进行系统检查，确认用户状态，准备回退方案',
            'moderate_anomaly': '密切观察行为变化，提供适当的引导和支持',
            'minor_deviation': '继续正常交互，记录变化用于模式更新'
        }
        
        return responses.get(anomaly_type, '继续观察')

# 全局模式识别器实例
_global_pattern_recognizer: Optional[PatternRecognizer] = None

def get_pattern_recognizer() -> PatternRecognizer:
    """获取全局模式识别器实例"""
    global _global_pattern_recognizer
    if _global_pattern_recognizer is None:
        _global_pattern_recognizer = PatternRecognizer()
    return _global_pattern_recognizer

