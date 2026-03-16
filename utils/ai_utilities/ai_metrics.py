"""
AI指标模块

提供AI模型和系统相关的指标计算工具，包括分类、回归、聚类、排序、公平性、漂移等指标。
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Union, Tuple, Callable
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, average_precision_score,
    mean_squared_error, mean_absolute_error, r2_score,
    silhouette_score, calinski_harabasz_score, davies_bouldin_score,
    adjusted_rand_score, normalized_mutual_info_score,
    homogeneity_score, completeness_score, v_measure_score
)
from scipy import stats
import warnings


class ClassificationMetrics:
    """分类指标类"""
    
    def __init__(self, y_true: np.ndarray, y_pred: np.ndarray,
                 y_prob: Optional[np.ndarray] = None):
        """初始化分类指标
        
        Args:
            y_true: 真实标签
            y_pred: 预测标签
            y_prob: 预测概率
        """
        self.y_true = np.array(y_true)
        self.y_pred = np.array(y_pred)
        self.y_prob = np.array(y_prob) if y_prob is not None else None
        self.n_classes = len(np.unique(y_true))
    
    def accuracy(self) -> float:
        """准确率"""
        return accuracy_score(self.y_true, self.y_pred)
    
    def precision(self, average: str = 'weighted') -> float:
        """精确率"""
        return precision_score(self.y_true, self.y_pred, average=average, zero_division=0)
    
    def recall(self, average: str = 'weighted') -> float:
        """召回率"""
        return recall_score(self.y_true, self.y_pred, average=average, zero_division=0)
    
    def f1(self, average: str = 'weighted') -> float:
        """F1分数"""
        return f1_score(self.y_true, self.y_pred, average=average, zero_division=0)
    
    def roc_auc(self, average: str = 'macro') -> float:
        """ROC-AUC分数"""
        if self.y_prob is None:
            return 0.0
        
        if self.n_classes == 2:
            return roc_auc_score(self.y_true, self.y_prob[:, 1] if self.y_prob.ndim > 1 else self.y_prob)
        else:
            return roc_auc_score(self.y_true, self.y_prob, multi_class='ovr', average=average)
    
    def pr_auc(self, average: str = 'macro') -> float:
        """PR-AUC分数"""
        if self.y_prob is None:
            return 0.0
        
        if self.n_classes == 2:
            return average_precision_score(self.y_true, self.y_prob[:, 1] if self.y_prob.ndim > 1 else self.y_prob)
        else:
            scores = []
            for i in range(self.n_classes):
                y_true_bin = (self.y_true == i).astype(int)
                scores.append(average_precision_score(y_true_bin, self.y_prob[:, i]))
            return np.mean(scores)
    
    def log_loss(self) -> float:
        """对数损失"""
        if self.y_prob is None:
            return 0.0
        
        from sklearn.metrics import log_loss
        return log_loss(self.y_true, self.y_prob)
    
    def matthews_corrcoef(self) -> float:
        """马修斯相关系数"""
        from sklearn.metrics import matthews_corrcoef
        return matthews_corrcoef(self.y_true, self.y_pred)
    
    def cohen_kappa(self) -> float:
        """Cohen's Kappa"""
        from sklearn.metrics import cohen_kappa_score
        return cohen_kappa_score(self.y_true, self.y_pred)
    
    def balanced_accuracy(self) -> float:
        """平衡准确率"""
        from sklearn.metrics import balanced_accuracy_score
        return balanced_accuracy_score(self.y_true, self.y_pred)
    
    def hamming_loss(self) -> float:
        """汉明损失"""
        from sklearn.metrics import hamming_loss
        return hamming_loss(self.y_true, self.y_pred)
    
    def zero_one_loss(self) -> float:
        """0-1损失"""
        from sklearn.metrics import zero_one_loss
        return zero_one_loss(self.y_true, self.y_pred)
    
    def get_all(self) -> Dict[str, float]:
        """获取所有指标"""
        metrics = {
            'accuracy': self.accuracy(),
            'precision': self.precision(),
            'recall': self.recall(),
            'f1_score': self.f1(),
            'balanced_accuracy': self.balanced_accuracy(),
            'matthews_corrcoef': self.matthews_corrcoef(),
            'cohen_kappa': self.cohen_kappa(),
            'hamming_loss': self.hamming_loss(),
            'zero_one_loss': self.zero_one_loss()
        }
        
        if self.y_prob is not None:
            metrics.update({
                'roc_auc': self.roc_auc(),
                'pr_auc': self.pr_auc(),
                'log_loss': self.log_loss()
            })
        
        return metrics


class RegressionMetrics:
    """回归指标类"""
    
    def __init__(self, y_true: np.ndarray, y_pred: np.ndarray):
        """初始化回归指标
        
        Args:
            y_true: 真实值
            y_pred: 预测值
        """
        self.y_true = np.array(y_true)
        self.y_pred = np.array(y_pred)
    
    def mse(self) -> float:
        """均方误差"""
        return mean_squared_error(self.y_true, self.y_pred)
    
    def rmse(self) -> float:
        """均方根误差"""
        return np.sqrt(self.mse())
    
    def mae(self) -> float:
        """平均绝对误差"""
        return mean_absolute_error(self.y_true, self.y_pred)
    
    def r2(self) -> float:
        """R²分数"""
        return r2_score(self.y_true, self.y_pred)
    
    def explained_variance(self) -> float:
        """解释方差"""
        from sklearn.metrics import explained_variance_score
        return explained_variance_score(self.y_true, self.y_pred)
    
    def max_error(self) -> float:
        """最大误差"""
        from sklearn.metrics import max_error
        return max_error(self.y_true, self.y_pred)
    
    def median_absolute_error(self) -> float:
        """中位数绝对误差"""
        from sklearn.metrics import median_absolute_error
        return median_absolute_error(self.y_true, self.y_pred)
    
    def mean_absolute_percentage_error(self) -> float:
        """平均绝对百分比误差"""
        mask = self.y_true != 0
        if np.any(mask):
            return np.mean(np.abs((self.y_true[mask] - self.y_pred[mask]) / self.y_true[mask])) * 100
        return 0.0
    
    def mean_squared_log_error(self) -> float:
        """均方对数误差"""
        from sklearn.metrics import mean_squared_log_error
        return mean_squared_log_error(self.y_true, self.y_pred)
    
    def get_all(self) -> Dict[str, float]:
        """获取所有指标"""
        return {
            'mse': self.mse(),
            'rmse': self.rmse(),
            'mae': self.mae(),
            'r2': self.r2(),
            'explained_variance': self.explained_variance(),
            'max_error': self.max_error(),
            'median_ae': self.median_absolute_error(),
            'mape': self.mean_absolute_percentage_error(),
            'msle': self.mean_squared_log_error()
        }


class ClusteringMetrics:
    """聚类指标类"""
    
    def __init__(self, X: np.ndarray, labels: np.ndarray,
                 true_labels: Optional[np.ndarray] = None):
        """初始化聚类指标
        
        Args:
            X: 特征矩阵
            labels: 聚类标签
            true_labels: 真实标签（可选）
        """
        self.X = np.array(X)
        self.labels = np.array(labels)
        self.true_labels = np.array(true_labels) if true_labels is not None else None
    
    def silhouette(self) -> float:
        """轮廓系数"""
        if len(np.unique(self.labels)) < 2:
            return 0.0
        return silhouette_score(self.X, self.labels)
    
    def calinski_harabasz(self) -> float:
        """Calinski-Harabasz指数"""
        if len(np.unique(self.labels)) < 2:
            return 0.0
        return calinski_harabasz_score(self.X, self.labels)
    
    def davies_bouldin(self) -> float:
        """Davies-Bouldin指数"""
        if len(np.unique(self.labels)) < 2:
            return 0.0
        return davies_bouldin_score(self.X, self.labels)
    
    def inertia(self) -> float:
        """惯性（簇内平方和）"""
        from sklearn.metrics import pairwise_distances
        inertia = 0
        for i in range(len(np.unique(self.labels))):
            cluster_points = self.X[self.labels == i]
            if len(cluster_points) > 0:
                center = np.mean(cluster_points, axis=0)
                inertia += np.sum(pairwise_distances([center], cluster_points) ** 2)
        return inertia
    
    def adjusted_rand(self) -> float:
        """调整兰德指数"""
        if self.true_labels is None:
            return 0.0
        return adjusted_rand_score(self.true_labels, self.labels)
    
    def normalized_mutual_info(self) -> float:
        """归一化互信息"""
        if self.true_labels is None:
            return 0.0
        return normalized_mutual_info_score(self.true_labels, self.labels)
    
    def homogeneity(self) -> float:
        """同质性"""
        if self.true_labels is None:
            return 0.0
        return homogeneity_score(self.true_labels, self.labels)
    
    def completeness(self) -> float:
        """完整性"""
        if self.true_labels is None:
            return 0.0
        return completeness_score(self.true_labels, self.labels)
    
    def v_measure(self) -> float:
        """V-measure"""
        if self.true_labels is None:
            return 0.0
        return v_measure_score(self.true_labels, self.labels)
    
    def fowlkes_mallows(self) -> float:
        """Fowlkes-Mallows指数"""
        if self.true_labels is None:
            return 0.0
        from sklearn.metrics import fowlkes_mallows_score
        return fowlkes_mallows_score(self.true_labels, self.labels)
    
    def get_all(self) -> Dict[str, float]:
        """获取所有指标"""
        metrics = {
            'silhouette_score': self.silhouette(),
            'calinski_harabasz_score': self.calinski_harabasz(),
            'davies_bouldin_score': self.davies_bouldin(),
            'inertia': self.inertia(),
            'n_clusters': len(np.unique(self.labels))
        }
        
        if self.true_labels is not None:
            metrics.update({
                'adjusted_rand_score': self.adjusted_rand(),
                'normalized_mutual_info_score': self.normalized_mutual_info(),
                'homogeneity_score': self.homogeneity(),
                'completeness_score': self.completeness(),
                'v_measure_score': self.v_measure(),
                'fowlkes_mallows_score': self.fowlkes_mallows()
            })
        
        return metrics


class RankingMetrics:
    """排序指标类"""
    
    def __init__(self, y_true: np.ndarray, y_score: np.ndarray):
        """初始化排序指标
        
        Args:
            y_true: 真实标签（1表示相关，0表示不相关）
            y_score: 预测分数
        """
        self.y_true = np.array(y_true)
        self.y_score = np.array(y_score)
    
    def average_precision(self) -> float:
        """平均精度（AP）"""
        return average_precision_score(self.y_true, self.y_score)
    
    def ndcg(self, k: int = None) -> float:
        """NDCG@K"""
        if k is None:
            k = len(self.y_true)
        
        def dcg(scores, k):
            scores = np.array(scores)[:k]
            return np.sum((2**scores - 1) / np.log2(np.arange(2, len(scores) + 2)))
        
        # 按分数排序
        sorted_indices = np.argsort(self.y_score)[::-1]
        sorted_true = self.y_true[sorted_indices]
        
        dcg_k = dcg(sorted_true, k)
        
        # 理想DCG
        ideal_true = np.sort(self.y_true)[::-1]
        idcg_k = dcg(ideal_true, k)
        
        return dcg_k / idcg_k if idcg_k > 0 else 0
    
    def precision_at_k(self, k: int) -> float:
        """Precision@K"""
        indices = np.argsort(self.y_score)[::-1][:k]
        return np.mean(self.y_true[indices])
    
    def recall_at_k(self, k: int) -> float:
        """Recall@K"""
        indices = np.argsort(self.y_score)[::-1][:k]
        total_relevant = np.sum(self.y_true)
        if total_relevant == 0:
            return 0.0
        return np.sum(self.y_true[indices]) / total_relevant
    
    def mean_reciprocal_rank(self) -> float:
        """平均倒数排名（MRR）"""
        sorted_indices = np.argsort(self.y_score)[::-1]
        for rank, idx in enumerate(sorted_indices, 1):
            if self.y_true[idx] == 1:
                return 1.0 / rank
        return 0.0
    
    def get_all(self, k: int = 10) -> Dict[str, float]:
        """获取所有指标"""
        return {
            'map': self.average_precision(),
            f'precision@{k}': self.precision_at_k(k),
            f'recall@{k}': self.recall_at_k(k),
            f'ndcg@{k}': self.ndcg(k),
            'mrr': self.mean_reciprocal_rank()
        }


class FairnessMetrics:
    """公平性指标类"""
    
    def __init__(self, y_true: np.ndarray, y_pred: np.ndarray,
                 sensitive_features: np.ndarray):
        """初始化公平性指标
        
        Args:
            y_true: 真实标签
            y_pred: 预测标签
            sensitive_features: 敏感特征
        """
        self.y_true = np.array(y_true)
        self.y_pred = np.array(y_pred)
        self.sensitive = np.array(sensitive_features)
        self.groups = np.unique(self.sensitive)
    
    def demographic_parity_difference(self) -> float:
        """人口统计平等方面差异"""
        rates = []
        for group in self.groups:
            mask = self.sensitive == group
            rates.append(np.mean(self.y_pred[mask]))
        return max(rates) - min(rates)
    
    def equal_opportunity_difference(self) -> float:
        """平等机会差异"""
        tprs = []
        for group in self.groups:
            mask = (self.sensitive == group) & (self.y_true == 1)
            if np.sum(mask) > 0:
                tpr = np.mean(self.y_pred[mask])
                tprs.append(tpr)
        
        if len(tprs) < 2:
            return 0.0
        return max(tprs) - min(tprs)
    
    def predictive_parity_difference(self) -> float:
        """预测平等方面差异"""
        pprs = []
        for group in self.groups:
            mask = (self.sensitive == group) & (self.y_pred == 1)
            if np.sum(mask) > 0:
                ppr = np.mean(self.y_true[mask])
                pprs.append(ppr)
        
        if len(pprs) < 2:
            return 0.0
        return max(pprs) - min(pprs)
    
    def statistical_parity_ratio(self) -> float:
        """统计平等比率"""
        rates = []
        for group in self.groups:
            mask = self.sensitive == group
            rates.append(np.mean(self.y_pred[mask]))
        
        if min(rates) == 0:
            return 0.0
        return min(rates) / max(rates)
    
    def get_all(self) -> Dict[str, float]:
        """获取所有指标"""
        return {
            'demographic_parity_diff': self.demographic_parity_difference(),
            'equal_opportunity_diff': self.equal_opportunity_difference(),
            'predictive_parity_diff': self.predictive_parity_difference(),
            'statistical_parity_ratio': self.statistical_parity_ratio()
        }


class BiasMetrics:
    """偏差指标类"""
    
    def __init__(self, y_true: np.ndarray, y_pred: np.ndarray,
                 protected_attr: np.ndarray):
        """初始化偏差指标
        
        Args:
            y_true: 真实标签
            y_pred: 预测标签
            protected_attr: 受保护属性
        """
        self.y_true = np.array(y_true)
        self.y_pred = np.array(y_pred)
        self.protected = np.array(protected_attr)
        self.groups = np.unique(self.protected)
    
    def disparate_impact(self) -> float:
        """不同影响"""
        # 计算优势组的正面预测率
        majority_group = self.groups[0]  # 假设第一个是优势组
        minority_group = self.groups[1] if len(self.groups) > 1 else majority_group
        
        majority_mask = self.protected == majority_group
        minority_mask = self.protected == minority_group
        
        majority_pos = np.mean(self.y_pred[majority_mask])
        minority_pos = np.mean(self.y_pred[minority_mask])
        
        if majority_pos == 0:
            return 0.0
        
        return minority_pos / majority_pos
    
    def treatment_equality(self) -> float:
        """处理平等"""
        fnr_ratios = []
        fpr_ratios = []
        
        for group in self.groups:
            mask = self.protected == group
            
            # 假阴性率
            fn = np.sum((self.y_pred[mask] == 0) & (self.y_true[mask] == 1))
            tp = np.sum((self.y_pred[mask] == 1) & (self.y_true[mask] == 1))
            fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
            
            # 假阳性率
            fp = np.sum((self.y_pred[mask] == 1) & (self.y_true[mask] == 0))
            tn = np.sum((self.y_pred[mask] == 0) & (self.y_true[mask] == 0))
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
            
            fnr_ratios.append(fnr)
            fpr_ratios.append(fpr)
        
        return {
            'fnr_ratio': max(fnr_ratios) / min(fnr_ratios) if min(fnr_ratios) > 0 else 0,
            'fpr_ratio': max(fpr_ratios) / min(fpr_ratios) if min(fpr_ratios) > 0 else 0
        }
    
    def equalized_odds_difference(self) -> float:
        """均衡赔率差异"""
        tprs = []
        fprs = []
        
        for group in self.groups:
            mask = self.protected == group
            
            # TPR
            tp = np.sum((self.y_pred[mask] == 1) & (self.y_true[mask] == 1))
            fn = np.sum((self.y_pred[mask] == 0) & (self.y_true[mask] == 1))
            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
            
            # FPR
            fp = np.sum((self.y_pred[mask] == 1) & (self.y_true[mask] == 0))
            tn = np.sum((self.y_pred[mask] == 0) & (self.y_true[mask] == 0))
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
            
            tprs.append(tpr)
            fprs.append(fpr)
        
        return max(max(tprs) - min(tprs), max(fprs) - min(fprs))
    
    def get_all(self) -> Dict[str, float]:
        """获取所有指标"""
        treatment_eq = self.treatment_equality()
        
        return {
            'disparate_impact': self.disparate_impact(),
            'equalized_odds_diff': self.equalized_odds_difference(),
            'fnr_ratio': treatment_eq['fnr_ratio'],
            'fpr_ratio': treatment_eq['fpr_ratio']
        }


class AIMetrics:
    """AI综合指标类"""
    
    def __init__(self):
        self.metrics = {}
    
    def add_classification(self, name: str, y_true: np.ndarray,
                          y_pred: np.ndarray, y_prob: Optional[np.ndarray] = None):
        """添加分类指标"""
        metrics = ClassificationMetrics(y_true, y_pred, y_prob)
        self.metrics[f'{name}_classification'] = metrics.get_all()
        return self.metrics[f'{name}_classification']
    
    def add_regression(self, name: str, y_true: np.ndarray, y_pred: np.ndarray):
        """添加回归指标"""
        metrics = RegressionMetrics(y_true, y_pred)
        self.metrics[f'{name}_regression'] = metrics.get_all()
        return self.metrics[f'{name}_regression']
    
    def add_clustering(self, name: str, X: np.ndarray, labels: np.ndarray,
                       true_labels: Optional[np.ndarray] = None):
        """添加聚类指标"""
        metrics = ClusteringMetrics(X, labels, true_labels)
        self.metrics[f'{name}_clustering'] = metrics.get_all()
        return self.metrics[f'{name}_clustering']
    
    def add_ranking(self, name: str, y_true: np.ndarray, y_score: np.ndarray, k: int = 10):
        """添加排序指标"""
        metrics = RankingMetrics(y_true, y_score)
        self.metrics[f'{name}_ranking'] = metrics.get_all(k)
        return self.metrics[f'{name}_ranking']
    
    def add_fairness(self, name: str, y_true: np.ndarray, y_pred: np.ndarray,
                     sensitive_features: np.ndarray):
        """添加公平性指标"""
        metrics = FairnessMetrics(y_true, y_pred, sensitive_features)
        self.metrics[f'{name}_fairness'] = metrics.get_all()
        return self.metrics[f'{name}_fairness']
    
    def add_bias(self, name: str, y_true: np.ndarray, y_pred: np.ndarray,
                 protected_attr: np.ndarray):
        """添加偏差指标"""
        metrics = BiasMetrics(y_true, y_pred, protected_attr)
        self.metrics[f'{name}_bias'] = metrics.get_all()
        return self.metrics[f'{name}_bias']
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有指标"""
        return self.metrics
    
    def to_dataframe(self) -> pd.DataFrame:
        """转换为DataFrame"""
        rows = []
        for metric_name, values in self.metrics.items():
            row = {'metric': metric_name}
            row.update(values)
            rows.append(row)
        return pd.DataFrame(rows)


class ModelPerformanceMetrics:
    """模型性能指标类"""
    
    def __init__(self):
        self.metrics = {}
    
    def calculate_inference_time(self, inference_times: List[float]) -> Dict[str, float]:
        """计算推理时间指标"""
        if not inference_times:
            return {}
        
        times = np.array(inference_times)
        
        return {
            'mean_inference_time': float(np.mean(times)),
            'median_inference_time': float(np.median(times)),
            'min_inference_time': float(np.min(times)),
            'max_inference_time': float(np.max(times)),
            'std_inference_time': float(np.std(times)),
            'p95_inference_time': float(np.percentile(times, 95)),
            'p99_inference_time': float(np.percentile(times, 99))
        }
    
    def calculate_throughput(self, num_requests: int, total_time: float) -> float:
        """计算吞吐量（请求/秒）"""
        if total_time <= 0:
            return 0.0
        return num_requests / total_time
    
    def calculate_latency_percentiles(self, latencies: List[float],
                                      percentiles: List[int] = None) -> Dict[str, float]:
        """计算延迟百分位数"""
        if percentiles is None:
            percentiles = [50, 90, 95, 99, 99.9]
        
        latencies = np.array(latencies)
        results = {}
        
        for p in percentiles:
            results[f'p{p}_latency'] = float(np.percentile(latencies, p))
        
        return results
    
    def calculate_error_rate(self, errors: int, total: int) -> float:
        """计算错误率"""
        if total == 0:
            return 0.0
        return errors / total
    
    def calculate_availability(self, uptime: float, total_time: float) -> float:
        """计算可用性"""
        if total_time == 0:
            return 0.0
        return uptime / total_time


class DataQualityMetrics:
    """数据质量指标类"""
    
    def __init__(self, data: np.ndarray):
        """初始化数据质量指标
        
        Args:
            data: 数据矩阵
        """
        self.data = np.array(data)
    
    def completeness(self) -> float:
        """完整性（非缺失值比例）"""
        total_elements = self.data.size
        missing = np.sum(np.isnan(self.data)) if np.isnan(self.data).any() else 0
        return 1.0 - (missing / total_elements) if total_elements > 0 else 0.0
    
    def uniqueness(self) -> float:
        """唯一性（唯一行比例）"""
        if len(self.data) == 0:
            return 0.0
        
        # 将每行转换为元组以便哈希
        rows_as_tuples = [tuple(row) for row in self.data]
        unique_rows = len(set(rows_as_tuples))
        
        return unique_rows / len(self.data)
    
    def consistency(self) -> float:
        """一致性（数据类型一致性）"""
        # 简化实现：检查每列的数据类型是否一致
        n_cols = self.data.shape[1] if self.data.ndim > 1 else 1
        consistent_cols = 0
        
        for col in range(n_cols):
            col_data = self.data[:, col] if n_cols > 1 else self.data
            # 检查是否有混合类型
            types = set(type(x) for x in col_data if not pd.isna(x))
            if len(types) <= 1:
                consistent_cols += 1
        
        return consistent_cols / n_cols
    
    def validity(self, validation_func: Optional[Callable] = None) -> float:
        """有效性（符合规则的比例）"""
        if validation_func is None:
            return 1.0
        
        valid_count = 0
        for row in self.data:
            if validation_func(row):
                valid_count += 1
        
        return valid_count / len(self.data) if len(self.data) > 0 else 0.0
    
    def accuracy(self, ground_truth: np.ndarray) -> float:
        """准确性（与真实值对比）"""
        if ground_truth.shape != self.data.shape:
            return 0.0
        
        if np.issubdtype(self.data.dtype, np.number):
            # 数值数据使用容差
            return np.mean(np.isclose(self.data, ground_truth))
        else:
            # 非数值数据使用精确匹配
            return np.mean(self.data == ground_truth)
    
    def get_all(self, ground_truth: Optional[np.ndarray] = None) -> Dict[str, float]:
        """获取所有指标"""
        metrics = {
            'completeness': self.completeness(),
            'uniqueness': self.uniqueness(),
            'consistency': self.consistency()
        }
        
        if ground_truth is not None:
            metrics['accuracy'] = self.accuracy(ground_truth)
        
        return metrics


def calculate_model_drift(y_true_old: np.ndarray, y_pred_old: np.ndarray,
                         y_true_new: np.ndarray, y_pred_new: np.ndarray,
                         metric: str = 'accuracy') -> Dict[str, float]:
    """计算模型漂移
    
    Args:
        y_true_old: 旧数据真实标签
        y_pred_old: 旧数据预测标签
        y_true_new: 新数据真实标签
        y_pred_new: 新数据预测标签
        metric: 用于比较的指标
        
    Returns:
        漂移指标
    """
    if metric == 'accuracy':
        old_score = accuracy_score(y_true_old, y_pred_old)
        new_score = accuracy_score(y_true_new, y_pred_new)
    elif metric == 'f1':
        old_score = f1_score(y_true_old, y_pred_old, average='weighted', zero_division=0)
        new_score = f1_score(y_true_new, y_pred_new, average='weighted', zero_division=0)
    elif metric == 'auc':
        # 需要概率预测
        old_score = 0.0
        new_score = 0.0
    else:
        old_score = 0.0
        new_score = 0.0
    
    drift = new_score - old_score
    relative_drift = drift / old_score if old_score != 0 else 0
    
    return {
        'old_score': old_score,
        'new_score': new_score,
        'absolute_drift': drift,
        'relative_drift': relative_drift,
        'drift_percentage': relative_drift * 100
    }


def calculate_data_drift(X_old: np.ndarray, X_new: np.ndarray,
                        threshold: float = 0.05) -> Dict[str, Any]:
    """计算数据漂移
    
    Args:
        X_old: 旧数据
        X_new: 新数据
        threshold: 显著性阈值
        
    Returns:
        漂移指标
    """
    from scipy import stats
    
    n_features = X_old.shape[1]
    drifted_features = []
    p_values = []
    
    for i in range(n_features):
        # 使用KS检验
        statistic, p_value = stats.ks_2samp(X_old[:, i], X_new[:, i])
        p_values.append(p_value)
        
        if p_value < threshold:
            drifted_features.append(i)
    
    return {
        'n_drifted_features': len(drifted_features),
        'drifted_features': drifted_features,
        'p_values': p_values,
        'mean_p_value': np.mean(p_values),
        'max_p_value': np.max(p_values),
        'min_p_value': np.min(p_values),
        'has_drift': len(drifted_features) > 0
    }


def calculate_concept_drift(y_true: np.ndarray, y_pred: np.ndarray,
                           window_size: int = 100) -> Dict[str, Any]:
    """计算概念漂移
    
    Args:
        y_true: 真实标签
        y_pred: 预测标签
        window_size: 滑动窗口大小
        
    Returns:
        漂移指标
    """
    n = len(y_true)
    if n < window_size * 2:
        return {'has_drift': False, 'message': 'Insufficient data'}
    
    accuracies = []
    for i in range(0, n - window_size + 1, window_size // 2):
        window_true = y_true[i:i + window_size]
        window_pred = y_pred[i:i + window_size]
        acc = accuracy_score(window_true, window_pred)
        accuracies.append(acc)
    
    # 检测准确率变化
    if len(accuracies) < 2:
        return {'has_drift': False}
    
    # 计算滑动窗口准确率的方差
    acc_std = np.std(accuracies)
    acc_mean = np.mean(accuracies)
    acc_changes = np.diff(accuracies)
    
    # 检测突然下降
    sudden_drops = np.where(acc_changes < -0.1)[0]  # 准确率下降超过10%
    
    return {
        'has_drift': len(sudden_drops) > 0 or acc_std > 0.1,
        'accuracy_mean': acc_mean,
        'accuracy_std': acc_std,
        'accuracy_changes': acc_changes.tolist(),
        'sudden_drops': sudden_drops.tolist(),
        'n_sudden_drops': len(sudden_drops)
    }


def calculate_feature_importance(model, feature_names: List[str]) -> Dict[str, float]:
    """计算特征重要性
    
    Args:
        model: 训练好的模型
        feature_names: 特征名称列表
        
    Returns:
        特征重要性字典
    """
    importances = {}
    
    # 尝试获取特征重要性
    if hasattr(model, 'feature_importances_'):
        imp_values = model.feature_importances_
        for name, imp in zip(feature_names, imp_values):
            importances[name] = float(imp)
    
    elif hasattr(model, 'coef_'):
        # 线性模型的系数
        coef = model.coef_
        if coef.ndim > 1:
            coef = np.abs(coef).mean(axis=0)
        else:
            coef = np.abs(coef)
        
        # 归一化
        if coef.sum() > 0:
            coef = coef / coef.sum()
        
        for name, imp in zip(feature_names, coef):
            importances[name] = float(imp)
    
    else:
        # 无法获取特征重要性
        importances = {name: 0.0 for name in feature_names}
    
    return importances