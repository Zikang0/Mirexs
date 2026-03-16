# cognitive/learning/transfer_learning.py
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import json
import os
from datetime import datetime
import logging
from collections import defaultdict
import hashlib

class TransferLearningModel(nn.Module):
    """迁移学习模型"""
    
    def __init__(self, base_model: nn.Module, num_source_tasks: int = 10, 
                 feature_dim: int = 512, hidden_dim: int = 256):
        super(TransferLearningModel, self).__init__()
        self.base_model = base_model
        self.num_source_tasks = num_source_tasks
        self.feature_dim = feature_dim
        self.hidden_dim = hidden_dim
        
        # 冻结基础模型的部分层
        self._freeze_base_layers()
        
        # 任务特定适配器
        self.task_adapters = nn.ModuleDict()
        
        # 迁移学习层
        self.transfer_layers = nn.Sequential(
            nn.Linear(feature_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        # 知识融合层
        self.knowledge_fusion = nn.Sequential(
            nn.Linear(hidden_dim // 2 + feature_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, feature_dim),
            nn.Tanh()
        )
        
        # 迁移权重预测器
        self.transfer_weight_predictor = nn.Sequential(
            nn.Linear(feature_dim * 2, 128),
            nn.ReLU(),
            nn.Linear(128, num_source_tasks),
            nn.Softmax(dim=-1)
        )
    
    def _freeze_base_layers(self):
        """冻结基础模型层"""
        # 冻结前几层，保持深层可训练
        for name, param in self.base_model.named_parameters():
            if 'layer' in name and int(name.split('.')[1]) < 3:  # 假设是ResNet风格
                param.requires_grad = False
    
    def forward(self, x: torch.Tensor, source_task_ids: Optional[List[int]] = None):
        """前向传播"""
        # 基础特征提取
        base_features = self.base_model(x)
        
        # 迁移学习特征转换
        transfer_features = self.transfer_layers(base_features)
        
        # 知识融合
        if source_task_ids is not None:
            # 如果有源任务，进行知识融合
            source_knowledge = self._get_source_knowledge(source_task_ids, base_features)
            fused_features = torch.cat([transfer_features, source_knowledge], dim=1)
            final_features = self.knowledge_fusion(fused_features)
        else:
            final_features = transfer_features
        
        return {
            'base_features': base_features,
            'transfer_features': transfer_features,
            'final_features': final_features
        }
    
    def _get_source_knowledge(self, source_task_ids: List[int], 
                            current_features: torch.Tensor) -> torch.Tensor:
        """获取源任务知识"""
        # 简化实现：在实际系统中会有更复杂的知识检索逻辑
        batch_size = current_features.size(0)
        source_knowledge = torch.zeros(batch_size, self.feature_dim).to(current_features.device)
        
        for task_id in source_task_ids:
            # 这里应该从知识库中获取对应任务的知识
            # 简化实现：使用随机矩阵模拟
            task_knowledge = torch.randn(batch_size, self.feature_dim).to(current_features.device)
            source_knowledge += task_knowledge * (1.0 / len(source_task_ids))
        
        return source_knowledge
    
    def add_task_adapter(self, task_id: str, input_dim: int, output_dim: int):
        """添加任务特定适配器"""
        adapter = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, output_dim)
        )
        self.task_adapters[task_id] = adapter

class TransferLearningSystem:
    """迁移学习：跨任务知识迁移"""
    
    def __init__(self, transfer_dir: str = "data/transfer_learning"):
        self.transfer_dir = transfer_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = self._setup_logger()
        
        # 迁移知识库
        self.knowledge_base: Dict[str, Dict] = {}
        self.task_similarity_matrix: np.ndarray = np.eye(10)  # 初始化为单位矩阵
        
        # 迁移历史
        self.transfer_history: List[Dict] = []
        
        # 模型实例（在实际使用中需要传入基础模型）
        self.model: Optional[TransferLearningModel] = None
        
        # 加载迁移学习数据
        self._load_transfer_data()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('transfer_learning')
        if not logger.handlers:
            handler = logging.FileHandler('logs/transfer_learning.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _load_transfer_data(self):
        """加载迁移学习数据"""
        knowledge_file = os.path.join(self.transfer_dir, "knowledge_base.json")
        similarity_file = os.path.join(self.transfer_dir, "task_similarity.npy")
        history_file = os.path.join(self.transfer_dir, "transfer_history.json")
        
        try:
            os.makedirs(self.transfer_dir, exist_ok=True)
            
            if os.path.exists(knowledge_file):
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    self.knowledge_base = json.load(f)
            
            if os.path.exists(similarity_file):
                self.task_similarity_matrix = np.load(similarity_file)
            
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.transfer_history = json.load(f)
            
            self.logger.info(f"迁移学习数据加载成功，共{len(self.knowledge_base)}个任务知识")
            
        except Exception as e:
            self.logger.error(f"加载迁移学习数据失败: {e}")
    
    def save_transfer_data(self):
        """保存迁移学习数据"""
        try:
            os.makedirs(self.transfer_dir, exist_ok=True)
            
            # 保存知识库
            knowledge_file = os.path.join(self.transfer_dir, "knowledge_base.json")
            with open(knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_base, f, ensure_ascii=False, indent=2)
            
            # 保存相似度矩阵
            similarity_file = os.path.join(self.transfer_dir, "task_similarity.npy")
            np.save(similarity_file, self.task_similarity_matrix)
            
            # 保存迁移历史
            history_file = os.path.join(self.transfer_dir, "transfer_history.json")
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.transfer_history, f, ensure_ascii=False, indent=2)
            
            self.logger.info("迁移学习数据保存成功")
            
        except Exception as e:
            self.logger.error(f"保存迁移学习数据失败: {e}")
    
    def extract_task_knowledge(self, task_id: str, model: nn.Module, 
                             task_data: Dict[str, Any]) -> str:
        """
        提取任务知识
        
        Args:
            task_id: 任务ID
            model: 训练好的模型
            task_data: 任务数据
            
        Returns:
            知识ID
        """
        try:
            # 生成知识ID
            knowledge_id = self._generate_knowledge_id(task_id, task_data)
            
            # 提取模型知识
            model_knowledge = self._extract_model_knowledge(model)
            
            # 提取任务特征
            task_features = self._extract_task_features(task_data)
            
            # 创建知识条目
            knowledge_entry = {
                'task_id': task_id,
                'knowledge_id': knowledge_id,
                'model_knowledge': model_knowledge,
                'task_features': task_features,
                'performance_metrics': task_data.get('performance_metrics', {}),
                'extraction_timestamp': datetime.now().isoformat(),
                'task_type': task_data.get('task_type', 'unknown'),
                'difficulty': task_data.get('difficulty', 0.5),
                'domain': task_data.get('domain', 'general')
            }
            
            # 保存到知识库
            self.knowledge_base[knowledge_id] = knowledge_entry
            
            # 更新任务相似度矩阵
            self._update_similarity_matrix(task_id, task_features)
            
            self.logger.info(f"任务知识提取成功: {knowledge_id}")
            return knowledge_id
            
        except Exception as e:
            self.logger.error(f"任务知识提取失败: {e}")
            return f"error_knowledge_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _generate_knowledge_id(self, task_id: str, task_data: Dict[str, Any]) -> str:
        """生成知识ID"""
        task_type = task_data.get('task_type', 'unknown')
        domain = task_data.get('domain', 'general')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        content_hash = hashlib.md5(str(task_data).encode()).hexdigest()[:8]
        
        return f"{domain}_{task_type}_{task_id}_{timestamp}_{content_hash}"
    
    def _extract_model_knowledge(self, model: nn.Module) -> Dict[str, Any]:
        """提取模型知识"""
        knowledge = {}
        
        # 提取权重和偏置
        for name, param in model.named_parameters():
            if param.requires_grad:
                # 只保存统计信息而不是完整权重以节省空间
                knowledge[name] = {
                    'shape': list(param.shape),
                    'mean': float(param.data.mean()),
                    'std': float(param.data.std()),
                    'norm': float(param.data.norm())
                }
        
        # 提取架构信息
        knowledge['architecture'] = str(model)
        
        return knowledge
    
    def _extract_task_features(self, task_data: Dict[str, Any]) -> List[float]:
        """提取任务特征"""
        features = []
        
        # 任务类型特征
        task_type = task_data.get('task_type', 'unknown')
        type_encoding = self._encode_task_type(task_type)
        features.extend(type_encoding)
        
        # 难度特征
        difficulty = task_data.get('difficulty', 0.5)
        features.append(difficulty)
        
        # 数据特征
        data_info = task_data.get('data_info', {})
        features.append(data_info.get('sample_count', 0) / 10000.0)  # 归一化
        features.append(data_info.get('feature_dim', 0) / 1000.0)    # 归一化
        
        # 性能特征
        performance = task_data.get('performance_metrics', {})
        features.append(performance.get('accuracy', 0.5))
        features.append(performance.get('loss', 1.0))
        
        # 领域特征
        domain = task_data.get('domain', 'general')
        domain_encoding = self._encode_domain(domain)
        features.extend(domain_encoding)
        
        # 填充到固定维度
        while len(features) < 64:
            features.append(0.0)
        features = features[:64]
        
        return features
    
    def _encode_task_type(self, task_type: str) -> List[float]:
        """编码任务类型"""
        task_types = ['classification', 'regression', 'reinforcement', 
                     'generation', 'clustering', 'anomaly_detection', 'unknown']
        encoding = [0.0] * len(task_types)
        
        if task_type in task_types:
            encoding[task_types.index(task_type)] = 1.0
        else:
            encoding[-1] = 1.0  # unknown
        
        return encoding
    
    def _encode_domain(self, domain: str) -> List[float]:
        """编码领域"""
        domains = ['vision', 'nlp', 'audio', 'robotics', 'healthcare', 'finance', 'general']
        encoding = [0.0] * len(domains)
        
        if domain in domains:
            encoding[domains.index(domain)] = 1.0
        else:
            encoding[-1] = 1.0  # general
        
        return encoding
    
    def _update_similarity_matrix(self, task_id: str, task_features: List[float]):
        """更新相似度矩阵"""
        # 简化实现：在实际系统中会有更复杂的相似度计算
        feature_vector = np.array(task_features)
        
        # 如果矩阵太小，扩展它
        current_size = self.task_similarity_matrix.shape[0]
        if current_size <= len(self.knowledge_base):
            new_size = current_size * 2
            new_matrix = np.eye(new_size)
            new_matrix[:current_size, :current_size] = self.task_similarity_matrix
            self.task_similarity_matrix = new_matrix
        
        # 计算与新任务的相似度并更新矩阵
        for i, (existing_id, existing_knowledge) in enumerate(list(self.knowledge_base.items())[:-1]):
            existing_features = np.array(existing_knowledge['task_features'])
            similarity = self._calculate_feature_similarity(feature_vector, existing_features)
            self.task_similarity_matrix[i, len(self.knowledge_base)-1] = similarity
            self.task_similarity_matrix[len(self.knowledge_base)-1, i] = similarity
    
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
    
    def find_similar_tasks(self, target_task: Dict[str, Any], top_k: int = 3) -> List[Tuple[str, float]]:
        """
        查找相似任务
        
        Args:
            target_task: 目标任务数据
            top_k: 返回的相似任务数量
            
        Returns:
            相似任务列表（任务ID, 相似度）
        """
        try:
            # 提取目标任务特征
            target_features = self._extract_task_features(target_task)
            target_vector = np.array(target_features)
            
            similarities = []
            
            for knowledge_id, knowledge_data in self.knowledge_base.items():
                source_features = np.array(knowledge_data['task_features'])
                similarity = self._calculate_feature_similarity(target_vector, source_features)
                
                # 考虑任务性能
                performance = knowledge_data.get('performance_metrics', {})
                performance_boost = performance.get('accuracy', 0.5) * 0.2  # 高性能任务更相关
                
                adjusted_similarity = similarity * (1.0 + performance_boost)
                similarities.append((knowledge_id, adjusted_similarity))
            
            # 按相似度排序
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            self.logger.error(f"查找相似任务失败: {e}")
            return []
    
    def transfer_knowledge(self, source_knowledge_id: str, target_task: Dict[str, Any], 
                          transfer_method: str = 'feature_adaptation') -> Dict[str, Any]:
        """
        迁移知识到目标任务
        
        Args:
            source_knowledge_id: 源知识ID
            target_task: 目标任务数据
            transfer_method: 迁移方法
            
        Returns:
            迁移结果
        """
        try:
            if source_knowledge_id not in self.knowledge_base:
                return {'success': False, 'error': '源知识不存在'}
            
            source_knowledge = self.knowledge_base[source_knowledge_id]
            
            # 执行知识迁移
            transfer_result = self._perform_knowledge_transfer(
                source_knowledge, target_task, transfer_method)
            
            # 记录迁移历史
            transfer_record = {
                'transfer_id': f"transfer_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'source_knowledge_id': source_knowledge_id,
                'target_task': target_task.get('task_type', 'unknown'),
                'transfer_method': transfer_method,
                'result': transfer_result,
                'timestamp': datetime.now().isoformat()
            }
            
            self.transfer_history.append(transfer_record)
            
            self.logger.info(f"知识迁移完成: {source_knowledge_id} -> {target_task.get('task_type', 'unknown')}")
            return transfer_result
            
        except Exception as e:
            self.logger.error(f"知识迁移失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _perform_knowledge_transfer(self, source_knowledge: Dict[str, Any], 
                                  target_task: Dict[str, Any], 
                                  transfer_method: str) -> Dict[str, Any]:
        """执行知识迁移"""
        if transfer_method == 'feature_adaptation':
            return self._feature_adaptation_transfer(source_knowledge, target_task)
        elif transfer_method == 'model_finetuning':
            return self._model_finetuning_transfer(source_knowledge, target_task)
        elif transfer_method == 'knowledge_distillation':
            return self._knowledge_distillation_transfer(source_knowledge, target_task)
        else:
            return {'success': False, 'error': f'未知的迁移方法: {transfer_method}'}
    
    def _feature_adaptation_transfer(self, source_knowledge: Dict[str, Any], 
                                   target_task: Dict[str, Any]) -> Dict[str, Any]:
        """特征适应迁移"""
        try:
            # 提取源任务特征
            source_features = np.array(source_knowledge['task_features'])
            target_features = np.array(self._extract_task_features(target_task))
            
            # 计算特征变换矩阵
            feature_similarity = self._calculate_feature_similarity(source_features, target_features)
            
            # 生成迁移建议
            adaptation_advice = self._generate_adaptation_advice(source_knowledge, target_task)
            
            return {
                'success': True,
                'transfer_method': 'feature_adaptation',
                'feature_similarity': float(feature_similarity),
                'adaptation_advice': adaptation_advice,
                'expected_improvement': f'{min(feature_similarity * 100, 50):.1f}%',
                'confidence': min(feature_similarity, 0.8)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'transfer_method': 'feature_adaptation'
            }
    
    def _model_finetuning_transfer(self, source_knowledge: Dict[str, Any], 
                                 target_task: Dict[str, Any]) -> Dict[str, Any]:
        """模型微调迁移"""
        try:
            # 分析模型兼容性
            compatibility = self._analyze_model_compatibility(source_knowledge, target_task)
            
            # 生成微调策略
            finetuning_strategy = self._generate_finetuning_strategy(source_knowledge, target_task)
            
            return {
                'success': True,
                'transfer_method': 'model_finetuning',
                'compatibility_score': compatibility,
                'finetuning_strategy': finetuning_strategy,
                'expected_training_time_reduction': f'{compatibility * 70:.1f}%',
                'recommended_learning_rate': 0.001 * compatibility
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'transfer_method': 'model_finetuning'
            }
    
    def _knowledge_distillation_transfer(self, source_knowledge: Dict[str, Any], 
                                       target_task: Dict[str, Any]) -> Dict[str, Any]:
        """知识蒸馏迁移"""
        try:
            # 分析蒸馏可行性
            distillation_feasibility = self._analyze_distillation_feasibility(source_knowledge, target_task)
            
            # 生成蒸馏策略
            distillation_strategy = self._generate_distillation_strategy(source_knowledge, target_task)
            
            return {
                'success': True,
                'transfer_method': 'knowledge_distillation',
                'feasibility_score': distillation_feasibility,
                'distillation_strategy': distillation_strategy,
                'expected_model_size_reduction': f'{(1 - distillation_feasibility) * 50:.1f}%',
                'recommended_temperature': 3.0
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'transfer_method': 'knowledge_distillation'
            }
    
    def _generate_adaptation_advice(self, source_knowledge: Dict[str, Any], 
                                  target_task: Dict[str, Any]) -> List[str]:
        """生成适应建议"""
        advice = []
        
        source_domain = source_knowledge.get('domain', 'general')
        target_domain = target_task.get('domain', 'general')
        
        if source_domain != target_domain:
            advice.append(f"需要从{source_domain}领域适配到{target_domain}领域")
        
        source_difficulty = source_knowledge.get('difficulty', 0.5)
        target_difficulty = target_task.get('difficulty', 0.5)
        
        if target_difficulty > source_difficulty:
            advice.append("目标任务更难，建议渐进式迁移")
        else:
            advice.append("目标任务相对简单，可以直接迁移")
        
        return advice
    
    def _analyze_model_compatibility(self, source_knowledge: Dict[str, Any], 
                                   target_task: Dict[str, Any]) -> float:
        """分析模型兼容性"""
        compatibility = 0.5  # 基础兼容性
        
        # 任务类型兼容性
        source_type = source_knowledge.get('task_type')
        target_type = target_task.get('task_type')
        if source_type == target_type:
            compatibility += 0.3
        
        # 领域兼容性
        source_domain = source_knowledge.get('domain')
        target_domain = target_task.get('domain')
        if source_domain == target_domain:
            compatibility += 0.2
        
        return min(compatibility, 1.0)
    
    def _generate_finetuning_strategy(self, source_knowledge: Dict[str, Any], 
                                    target_task: Dict[str, Any]) -> Dict[str, Any]:
        """生成微调策略"""
        return {
            'frozen_layers': ['base_layers'],
            'trainable_layers': ['classification_head', 'adaptation_layers'],
            'recommended_epochs': 10,
            'learning_rate_schedule': 'cosine_annealing',
            'early_stopping_patience': 5
        }
    
    def _analyze_distillation_feasibility(self, source_knowledge: Dict[str, Any], 
                                        target_task: Dict[str, Any]) -> float:
        """分析蒸馏可行性"""
        feasibility = 0.6  # 基础可行性
        
        # 基于任务复杂度调整
        source_difficulty = source_knowledge.get('difficulty', 0.5)
        target_difficulty = target_task.get('difficulty', 0.5)
        
        if target_difficulty < source_difficulty:
            feasibility += 0.2  # 简单任务更容易蒸馏
        elif target_difficulty > source_difficulty:
            feasibility -= 0.1  # 复杂任务蒸馏难度大
        
        return max(0.1, min(feasibility, 1.0))
    
    def _generate_distillation_strategy(self, source_knowledge: Dict[str, Any], 
                                      target_task: Dict[str, Any]) -> Dict[str, Any]:
        """生成蒸馏策略"""
        return {
            'distillation_type': 'response_based',
            'temperature': 3.0,
            'alpha': 0.7,
            'loss_weights': {
                'hard_target': 0.3,
                'soft_target': 0.7
            },
            'recommended_student_architecture': 'simplified_version'
        }
    
    def get_transfer_effectiveness_report(self) -> Dict[str, Any]:
        """获取迁移效果报告"""
        successful_transfers = [
            record for record in self.transfer_history 
            if record.get('result', {}).get('success', False)
        ]
        
        if not successful_transfers:
            return {'message': '尚无成功的迁移记录'}
        
        # 分析迁移效果
        effectiveness_metrics = []
        for transfer in successful_transfers:
            result = transfer['result']
            effectiveness_metrics.append({
                'transfer_method': transfer['transfer_method'],
                'similarity': result.get('feature_similarity', 0.5),
                'confidence': result.get('confidence', 0.5),
                'expected_improvement': result.get('expected_improvement', '0%')
            })
        
        # 计算各方法的平均效果
        method_stats = {}
        for metric in effectiveness_metrics:
            method = metric['transfer_method']
            if method not in method_stats:
                method_stats[method] = {
                    'count': 0,
                    'total_similarity': 0.0,
                    'total_confidence': 0.0
                }
            
            stats = method_stats[method]
            stats['count'] += 1
            stats['total_similarity'] += metric['similarity']
            stats['total_confidence'] += metric['confidence']
        
        # 计算平均值
        for method, stats in method_stats.items():
            stats['avg_similarity'] = stats['total_similarity'] / stats['count']
            stats['avg_confidence'] = stats['total_confidence'] / stats['count']
        
        return {
            'total_transfers': len(self.transfer_history),
            'successful_transfers': len(successful_transfers),
            'success_rate': len(successful_transfers) / len(self.transfer_history) 
                            if self.transfer_history else 0.0,
            'method_effectiveness': method_stats,
            'knowledge_base_size': len(self.knowledge_base),
            'most_effective_method': max(method_stats.items(), 
                                       key=lambda x: x[1]['avg_confidence'])[0] 
                                   if method_stats else 'unknown'
        }
    
    def recommend_transfer_strategy(self, target_task: Dict[str, Any]) -> Dict[str, Any]:
        """
        推荐迁移策略
        
        Args:
            target_task: 目标任务数据
            
        Returns:
            迁移策略推荐
        """
        similar_tasks = self.find_similar_tasks(target_task, top_k=3)
        
        if not similar_tasks:
            return {
                'recommendation': 'no_similar_tasks',
                'suggestion': '从零开始训练或寻找外部知识源',
                'confidence': 0.0
            }
        
        # 分析最佳迁移方法
        best_method = 'feature_adaptation'
        best_confidence = 0.0
        
        for knowledge_id, similarity in similar_tasks:
            if similarity > best_confidence:
                best_confidence = similarity
        
        # 基于相似度选择方法
        if best_confidence > 0.8:
            best_method = 'model_finetuning'
        elif best_confidence > 0.6:
            best_method = 'feature_adaptation'
        else:
            best_method = 'knowledge_distillation'
        
        return {
            'recommended_method': best_method,
            'similar_tasks_found': len(similar_tasks),
            'best_similarity': best_confidence,
            'source_tasks': [task_id for task_id, _ in similar_tasks],
            'confidence': best_confidence * 0.8,  # 调整置信度
            'implementation_guidance': self._get_implementation_guidance(best_method)
        }
    
    def _get_implementation_guidance(self, method: str) -> List[str]:
        """获取实施指导"""
        guidance = {
            'feature_adaptation': [
                "提取源任务的特征表示",
                "设计特征适配层",
                "在目标任务数据上微适配层",
                "验证特征迁移效果"
            ],
            'model_finetuning': [
                "加载预训练源模型",
                "冻结基础层，解冻顶层",
                "使用较小的学习率",
                "在目标任务数据上微调",
                "使用早停法防止过拟合"
            ],
            'knowledge_distillation': [
                "保持源模型作为教师模型",
                "设计更小的学生模型",
                "使用软标签进行训练",
                "平衡硬标签和软标签损失",
                "逐步降低蒸馏温度"
            ]
        }
        
        return guidance.get(method, ["请参考迁移学习最佳实践"])

# 全局迁移学习系统实例
_global_transfer_learning: Optional[TransferLearningSystem] = None

def get_transfer_learning_system() -> TransferLearningSystem:
    """获取全局迁移学习系统实例"""
    global _global_transfer_learning
    if _global_transfer_learning is None:
        _global_transfer_learning = TransferLearningSystem()
    return _global_transfer_learning

