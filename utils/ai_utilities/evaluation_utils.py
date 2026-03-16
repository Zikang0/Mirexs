"""
评估工具模块

提供AI模型评估的工具函数，包括分类、回归、聚类、排序等任务的评估指标和可视化。
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Union, Tuple, Callable
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_curve, auc,
    precision_recall_curve, average_precision_score,
    mean_squared_error, mean_absolute_error, r2_score,
    explained_variance_score, mean_squared_log_error,
    silhouette_score, calinski_harabasz_score, davies_bouldin_score,
    adjusted_rand_score, normalized_mutual_info_score,
    homogeneity_score, completeness_score, v_measure_score
)
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns


class ClassificationEvaluator:
    """分类评估器"""
    
    def __init__(self, y_true: np.ndarray, y_pred: np.ndarray,
                 y_prob: Optional[np.ndarray] = None,
                 class_names: Optional[List[str]] = None):
        """初始化分类评估器
        
        Args:
            y_true: 真实标签
            y_pred: 预测标签
            y_prob: 预测概率
            class_names: 类别名称
        """
        self.y_true = np.array(y_true)
        self.y_pred = np.array(y_pred)
        self.y_prob = np.array(y_prob) if y_prob is not None else None
        self.class_names = class_names
        self.n_classes = len(np.unique(y_true))
        
        # 确保分类名称
        if self.class_names is None:
            self.class_names = [f"Class_{i}" for i in range(self.n_classes)]
    
    def accuracy(self) -> float:
        """计算准确率"""
        return accuracy_score(self.y_true, self.y_pred)
    
    def precision(self, average: str = 'weighted') -> float:
        """计算精确率"""
        return precision_score(self.y_true, self.y_pred, average=average, zero_division=0)
    
    def recall(self, average: str = 'weighted') -> float:
        """计算召回率"""
        return recall_score(self.y_true, self.y_pred, average=average, zero_division=0)
    
    def f1(self, average: str = 'weighted') -> float:
        """计算F1分数"""
        return f1_score(self.y_true, self.y_pred, average=average, zero_division=0)
    
    def confusion_matrix(self) -> np.ndarray:
        """计算混淆矩阵"""
        return confusion_matrix(self.y_true, self.y_pred)
    
    def classification_report(self) -> Dict[str, Any]:
        """生成分类报告"""
        report = classification_report(
            self.y_true, self.y_pred,
            target_names=self.class_names,
            output_dict=True,
            zero_division=0
        )
        return report
    
    def roc_auc(self, average: str = 'macro') -> float:
        """计算ROC-AUC"""
        if self.y_prob is None:
            return 0.0
        
        if self.n_classes == 2:
            fpr, tpr, _ = roc_curve(self.y_true, self.y_prob[:, 1])
            return auc(fpr, tpr)
        else:
            from sklearn.metrics import roc_auc_score
            return roc_auc_score(self.y_true, self.y_prob, multi_class='ovr', average=average)
    
    def precision_recall_auc(self, average: str = 'macro') -> float:
        """计算PR-AUC"""
        if self.y_prob is None:
            return 0.0
        
        if self.n_classes == 2:
            precision, recall, _ = precision_recall_curve(self.y_true, self.y_prob[:, 1])
            return auc(recall, precision)
        else:
            scores = []
            for i in range(self.n_classes):
                y_true_bin = (self.y_true == i).astype(int)
                score = average_precision_score(y_true_bin, self.y_prob[:, i])
                scores.append(score)
            return np.mean(scores)
    
    def log_loss(self) -> float:
        """计算对数损失"""
        if self.y_prob is None:
            return 0.0
        
        from sklearn.metrics import log_loss
        return log_loss(self.y_true, self.y_prob)
    
    def matthews_corrcoef(self) -> float:
        """计算马修斯相关系数"""
        from sklearn.metrics import matthews_corrcoef
        return matthews_corrcoef(self.y_true, self.y_pred)
    
    def cohen_kappa(self) -> float:
        """计算Cohen's Kappa"""
        from sklearn.metrics import cohen_kappa_score
        return cohen_kappa_score(self.y_true, self.y_pred)
    
    def hamming_loss(self) -> float:
        """计算汉明损失"""
        from sklearn.metrics import hamming_loss
        return hamming_loss(self.y_true, self.y_pred)
    
    def balanced_accuracy(self) -> float:
        """计算平衡准确率"""
        from sklearn.metrics import balanced_accuracy_score
        return balanced_accuracy_score(self.y_true, self.y_pred)
    
    def top_k_accuracy(self, k: int = 3) -> float:
        """计算Top-K准确率"""
        if self.y_prob is None:
            return 0.0
        
        from sklearn.metrics import top_k_accuracy_score
        return top_k_accuracy_score(self.y_true, self.y_prob, k=k)
    
    def per_class_metrics(self) -> Dict[str, Dict[str, float]]:
        """计算每个类别的指标"""
        metrics = {}
        
        for i, class_name in enumerate(self.class_names):
            # 二值化
            y_true_bin = (self.y_true == i).astype(int)
            y_pred_bin = (self.y_pred == i).astype(int)
            
            # 计算指标
            tn = np.sum((y_true_bin == 0) & (y_pred_bin == 0))
            fp = np.sum((y_true_bin == 0) & (y_pred_bin == 1))
            fn = np.sum((y_true_bin == 1) & (y_pred_bin == 0))
            tp = np.sum((y_true_bin == 1) & (y_pred_bin == 1))
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            metrics[class_name] = {
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'true_positives': int(tp),
                'false_positives': int(fp),
                'true_negatives': int(tn),
                'false_negatives': int(fn),
                'support': int(np.sum(y_true_bin))
            }
        
        return metrics
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        metrics = {
            'accuracy': self.accuracy(),
            'precision': self.precision(),
            'recall': self.recall(),
            'f1_score': self.f1(),
            'balanced_accuracy': self.balanced_accuracy(),
            'matthews_corrcoef': self.matthews_corrcoef(),
            'cohen_kappa': self.cohen_kappa(),
            'hamming_loss': self.hamming_loss()
        }
        
        if self.y_prob is not None:
            metrics['roc_auc'] = self.roc_auc()
            metrics['pr_auc'] = self.precision_recall_auc()
            metrics['log_loss'] = self.log_loss()
            metrics['top_3_accuracy'] = self.top_k_accuracy(3)
        
        metrics['confusion_matrix'] = self.confusion_matrix().tolist()
        metrics['classification_report'] = self.classification_report()
        metrics['per_class_metrics'] = self.per_class_metrics()
        
        return metrics


class RegressionEvaluator:
    """回归评估器"""
    
    def __init__(self, y_true: np.ndarray, y_pred: np.ndarray):
        """初始化回归评估器
        
        Args:
            y_true: 真实值
            y_pred: 预测值
        """
        self.y_true = np.array(y_true)
        self.y_pred = np.array(y_pred)
    
    def mean_squared_error(self) -> float:
        """计算均方误差"""
        return mean_squared_error(self.y_true, self.y_pred)
    
    def root_mean_squared_error(self) -> float:
        """计算均方根误差"""
        return np.sqrt(self.mean_squared_error())
    
    def mean_absolute_error(self) -> float:
        """计算平均绝对误差"""
        return mean_absolute_error(self.y_true, self.y_pred)
    
    def r2_score(self) -> float:
        """计算R²分数"""
        return r2_score(self.y_true, self.y_pred)
    
    def explained_variance(self) -> float:
        """计算解释方差"""
        return explained_variance_score(self.y_true, self.y_pred)
    
    def mean_absolute_percentage_error(self) -> float:
        """计算平均绝对百分比误差"""
        mask = self.y_true != 0
        if np.any(mask):
            return np.mean(np.abs((self.y_true[mask] - self.y_pred[mask]) / self.y_true[mask])) * 100
        return 0.0
    
    def mean_squared_log_error(self) -> float:
        """计算均方对数误差"""
        return mean_squared_log_error(self.y_true, self.y_pred)
    
    def median_absolute_error(self) -> float:
        """计算中位数绝对误差"""
        from sklearn.metrics import median_absolute_error
        return median_absolute_error(self.y_true, self.y_pred)
    
    def max_error(self) -> float:
        """计算最大误差"""
        from sklearn.metrics import max_error
        return max_error(self.y_true, self.y_pred)
    
    def residuals(self) -> np.ndarray:
        """计算残差"""
        return self.y_true - self.y_pred
    
    def residual_std(self) -> float:
        """计算残差标准差"""
        return np.std(self.residuals())
    
    def durbin_watson(self) -> float:
        """计算Durbin-Watson统计量"""
        from statsmodels.stats.stattools import durbin_watson
        return durbin_watson(self.residuals())
    
    def jarque_bera(self) -> Dict[str, float]:
        """计算Jarque-Bera正态性检验"""
        jb_stat, p_value, skew, kurtosis = stats.jarque_bera(self.residuals())
        return {
            'statistic': jb_stat,
            'p_value': p_value,
            'skewness': skew,
            'kurtosis': kurtosis
        }
    
    def get_all_metrics(self) -> Dict[str, float]:
        """获取所有指标"""
        return {
            'mse': self.mean_squared_error(),
            'rmse': self.root_mean_squared_error(),
            'mae': self.mean_absolute_error(),
            'r2': self.r2_score(),
            'explained_variance': self.explained_variance(),
            'mape': self.mean_absolute_percentage_error(),
            'msle': self.mean_squared_log_error(),
            'median_ae': self.median_absolute_error(),
            'max_error': self.max_error(),
            'residual_std': self.residual_std()
        }


class ClusteringEvaluator:
    """聚类评估器"""
    
    def __init__(self, X: np.ndarray, labels: np.ndarray,
                 true_labels: Optional[np.ndarray] = None):
        """初始化聚类评估器
        
        Args:
            X: 特征矩阵
            labels: 聚类标签
            true_labels: 真实标签（可选）
        """
        self.X = np.array(X)
        self.labels = np.array(labels)
        self.true_labels = np.array(true_labels) if true_labels is not None else None
    
    def silhouette_score(self) -> float:
        """计算轮廓系数"""
        if len(np.unique(self.labels)) < 2:
            return 0.0
        return silhouette_score(self.X, self.labels)
    
    def calinski_harabasz_score(self) -> float:
        """计算Calinski-Harabasz指数"""
        if len(np.unique(self.labels)) < 2:
            return 0.0
        return calinski_harabasz_score(self.X, self.labels)
    
    def davies_bouldin_score(self) -> float:
        """计算Davies-Bouldin指数"""
        if len(np.unique(self.labels)) < 2:
            return 0.0
        return davies_bouldin_score(self.X, self.labels)
    
    def inertia(self) -> float:
        """计算惯性（簇内平方和）"""
        from sklearn.metrics import pairwise_distances
        inertia = 0
        for i in range(len(np.unique(self.labels))):
            cluster_points = self.X[self.labels == i]
            if len(cluster_points) > 0:
                center = np.mean(cluster_points, axis=0)
                inertia += np.sum(pairwise_distances([center], cluster_points) ** 2)
        return inertia
    
    def homogeneity_score(self) -> float:
        """计算同质性分数"""
        if self.true_labels is None:
            return 0.0
        return homogeneity_score(self.true_labels, self.labels)
    
    def completeness_score(self) -> float:
        """计算完整性分数"""
        if self.true_labels is None:
            return 0.0
        return completeness_score(self.true_labels, self.labels)
    
    def v_measure_score(self) -> float:
        """计算V-measure分数"""
        if self.true_labels is None:
            return 0.0
        return v_measure_score(self.true_labels, self.labels)
    
    def adjusted_rand_score(self) -> float:
        """计算调整兰德指数"""
        if self.true_labels is None:
            return 0.0
        return adjusted_rand_score(self.true_labels, self.labels)
    
    def normalized_mutual_info_score(self) -> float:
        """计算归一化互信息"""
        if self.true_labels is None:
            return 0.0
        return normalized_mutual_info_score(self.true_labels, self.labels)
    
    def fowlkes_mallows_score(self) -> float:
        """计算Fowlkes-Mallows指数"""
        if self.true_labels is None:
            return 0.0
        from sklearn.metrics import fowlkes_mallows_score
        return fowlkes_mallows_score(self.true_labels, self.labels)
    
    def get_all_metrics(self) -> Dict[str, float]:
        """获取所有指标"""
        metrics = {
            'silhouette_score': self.silhouette_score(),
            'calinski_harabasz_score': self.calinski_harabasz_score(),
            'davies_bouldin_score': self.davies_bouldin_score(),
            'inertia': self.inertia(),
            'n_clusters': len(np.unique(self.labels))
        }
        
        if self.true_labels is not None:
            metrics.update({
                'homogeneity_score': self.homogeneity_score(),
                'completeness_score': self.completeness_score(),
                'v_measure_score': self.v_measure_score(),
                'adjusted_rand_score': self.adjusted_rand_score(),
                'normalized_mutual_info_score': self.normalized_mutual_info_score(),
                'fowlkes_mallows_score': self.fowlkes_mallows_score()
            })
        
        return metrics


class RankingEvaluator:
    """排序评估器"""
    
    def __init__(self, y_true: List[int], y_score: List[float],
                 k: Optional[int] = None):
        """初始化排序评估器
        
        Args:
            y_true: 真实标签（1表示相关，0表示不相关）
            y_score: 预测分数
            k: 评估的截断位置
        """
        self.y_true = np.array(y_true)
        self.y_score = np.array(y_score)
        self.k = k or len(y_true)
    
    def precision_at_k(self) -> float:
        """计算Precision@K"""
        indices = np.argsort(self.y_score)[::-1][:self.k]
        return np.mean(self.y_true[indices])
    
    def recall_at_k(self) -> float:
        """计算Recall@K"""
        indices = np.argsort(self.y_score)[::-1][:self.k]
        total_relevant = np.sum(self.y_true)
        if total_relevant == 0:
            return 0.0
        return np.sum(self.y_true[indices]) / total_relevant
    
    def average_precision(self) -> float:
        """计算平均精度（AP）"""
        from sklearn.metrics import average_precision_score
        return average_precision_score(self.y_true, self.y_score)
    
    def ndcg_at_k(self) -> float:
        """计算NDCG@K"""
        def dcg(scores, k):
            scores = np.array(scores)[:k]
            return np.sum((2**scores - 1) / np.log2(np.arange(2, len(scores) + 2)))
        
        # 按分数排序
        sorted_indices = np.argsort(self.y_score)[::-1]
        sorted_true = self.y_true[sorted_indices]
        
        dcg_k = dcg(sorted_true, self.k)
        
        # 理想DCG
        ideal_true = np.sort(self.y_true)[::-1]
        idcg_k = dcg(ideal_true, self.k)
        
        return dcg_k / idcg_k if idcg_k > 0 else 0
    
    def mean_reciprocal_rank(self) -> float:
        """计算平均倒数排名（MRR）"""
        sorted_indices = np.argsort(self.y_score)[::-1]
        for rank, idx in enumerate(sorted_indices, 1):
            if self.y_true[idx] == 1:
                return 1.0 / rank
        return 0.0
    
    def get_all_metrics(self) -> Dict[str, float]:
        """获取所有指标"""
        return {
            f'precision@{self.k}': self.precision_at_k(),
            f'recall@{self.k}': self.recall_at_k(),
            f'ndcg@{self.k}': self.ndcg_at_k(),
            'map': self.average_precision(),
            'mrr': self.mean_reciprocal_rank()
        }


class TimeSeriesEvaluator:
    """时间序列评估器"""
    
    def __init__(self, y_true: np.ndarray, y_pred: np.ndarray):
        """初始化时间序列评估器
        
        Args:
            y_true: 真实值
            y_pred: 预测值
        """
        self.y_true = np.array(y_true)
        self.y_pred = np.array(y_pred)
    
    def mase(self, y_train: np.ndarray, seasonality: int = 1) -> float:
        """计算平均绝对缩放误差（MASE）
        
        Args:
            y_train: 训练数据
            seasonality: 季节性周期
            
        Returns:
            MASE值
        """
        # 计算训练集的朴素预测误差
        if len(y_train) > seasonality:
            naive_errors = np.abs(y_train[seasonality:] - y_train[:-seasonality])
            scale = np.mean(naive_errors)
        else:
            scale = np.mean(np.abs(np.diff(y_train))) if len(y_train) > 1 else 1.0
        
        if scale == 0:
            return 0.0
        
        # 计算预测误差
        errors = np.abs(self.y_true - self.y_pred)
        return np.mean(errors) / scale
    
    def smape(self) -> float:
        """计算对称平均绝对百分比误差（SMAPE）"""
        denominator = (np.abs(self.y_true) + np.abs(self.y_pred)) / 2
        mask = denominator > 0
        if np.any(mask):
            return np.mean(2 * np.abs(self.y_true[mask] - self.y_pred[mask]) / denominator[mask]) * 100
        return 0.0
    
    def mape(self) -> float:
        """计算平均绝对百分比误差（MAPE）"""
        mask = self.y_true != 0
        if np.any(mask):
            return np.mean(np.abs((self.y_true[mask] - self.y_pred[mask]) / self.y_true[mask])) * 100
        return 0.0
    
    def rmse(self) -> float:
        """计算均方根误差"""
        return np.sqrt(np.mean((self.y_true - self.y_pred) ** 2))
    
    def mae(self) -> float:
        """计算平均绝对误差"""
        return np.mean(np.abs(self.y_true - self.y_pred))
    
    def get_all_metrics(self, y_train: Optional[np.ndarray] = None) -> Dict[str, float]:
        """获取所有指标"""
        metrics = {
            'rmse': self.rmse(),
            'mae': self.mae(),
            'mape': self.mape(),
            'smape': self.smape()
        }
        
        if y_train is not None:
            metrics['mase'] = self.mase(y_train)
        
        return metrics


class ModelEvaluator:
    """模型评估器（综合）"""
    
    def __init__(self, model: Any = None, model_name: str = "Model"):
        """初始化模型评估器
        
        Args:
            model: 模型对象
            model_name: 模型名称
        """
        self.model = model
        self.model_name = model_name
        self.results = {}
    
    def evaluate_classification(self, X_test: np.ndarray, y_test: np.ndarray,
                                class_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """评估分类模型"""
        # 预测
        if hasattr(self.model, 'predict_proba'):
            y_prob = self.model.predict_proba(X_test)
            y_pred = np.argmax(y_prob, axis=1) if y_prob.shape[1] > 1 else (y_prob > 0.5).astype(int).flatten()
        else:
            y_pred = self.model.predict(X_test)
            y_prob = None
        
        # 评估
        evaluator = ClassificationEvaluator(y_test, y_pred, y_prob, class_names)
        results = evaluator.get_all_metrics()
        
        self.results['classification'] = results
        return results
    
    def evaluate_regression(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """评估回归模型"""
        y_pred = self.model.predict(X_test)
        
        evaluator = RegressionEvaluator(y_test, y_pred)
        results = evaluator.get_all_metrics()
        
        self.results['regression'] = results
        return results
    
    def evaluate_clustering(self, X: np.ndarray, labels: np.ndarray,
                           true_labels: Optional[np.ndarray] = None) -> Dict[str, float]:
        """评估聚类模型"""
        evaluator = ClusteringEvaluator(X, labels, true_labels)
        results = evaluator.get_all_metrics()
        
        self.results['clustering'] = results
        return results
    
    def evaluate_ranking(self, y_true: List[int], y_score: List[float],
                         k: int = 10) -> Dict[str, float]:
        """评估排序模型"""
        evaluator = RankingEvaluator(y_true, y_score, k)
        results = evaluator.get_all_metrics()
        
        self.results['ranking'] = results
        return results
    
    def cross_validate(self, X: np.ndarray, y: np.ndarray, cv: int = 5,
                       scoring: str = 'accuracy') -> Dict[str, Any]:
        """交叉验证"""
        from sklearn.model_selection import cross_validate as cv_validate
        
        scores = cv_validate(self.model, X, y, cv=cv, scoring=scoring, return_train_score=True)
        
        results = {
            'test_scores': scores['test_score'].tolist(),
            'train_scores': scores['train_score'].tolist(),
            'test_mean': np.mean(scores['test_score']),
            'test_std': np.std(scores['test_score']),
            'train_mean': np.mean(scores['train_score']),
            'train_std': np.std(scores['train_score'])
        }
        
        self.results['cross_validation'] = results
        return results
    
    def learning_curve(self, X: np.ndarray, y: np.ndarray,
                       train_sizes: np.ndarray = None,
                       cv: int = 5) -> Dict[str, Any]:
        """学习曲线"""
        from sklearn.model_selection import learning_curve
        
        if train_sizes is None:
            train_sizes = np.linspace(0.1, 1.0, 10)
        
        train_sizes_abs, train_scores, test_scores = learning_curve(
            self.model, X, y, train_sizes=train_sizes, cv=cv, n_jobs=-1
        )
        
        results = {
            'train_sizes': train_sizes_abs.tolist(),
            'train_mean': np.mean(train_scores, axis=1).tolist(),
            'train_std': np.std(train_scores, axis=1).tolist(),
            'test_mean': np.mean(test_scores, axis=1).tolist(),
            'test_std': np.std(test_scores, axis=1).tolist()
        }
        
        self.results['learning_curve'] = results
        return results
    
    def validation_curve(self, X: np.ndarray, y: np.ndarray,
                         param_name: str, param_range: List[Any],
                         cv: int = 5) -> Dict[str, Any]:
        """验证曲线"""
        from sklearn.model_selection import validation_curve
        
        train_scores, test_scores = validation_curve(
            self.model, X, y, param_name=param_name, param_range=param_range,
            cv=cv, n_jobs=-1
        )
        
        results = {
            'param_name': param_name,
            'param_range': [str(p) for p in param_range],
            'train_mean': np.mean(train_scores, axis=1).tolist(),
            'train_std': np.std(train_scores, axis=1).tolist(),
            'test_mean': np.mean(test_scores, axis=1).tolist(),
            'test_std': np.std(test_scores, axis=1).tolist()
        }
        
        self.results['validation_curve'] = results
        return results
    
    def generate_report(self) -> str:
        """生成评估报告"""
        report = "\n" + "=" * 60 + "\n"
        report += f"MODEL EVALUATION REPORT - {self.model_name}\n"
        report += "=" * 60 + "\n\n"
        
        for task_type, results in self.results.items():
            if task_type == 'classification':
                report += "Classification Metrics:\n"
                report += "-" * 40 + "\n"
                report += f"  Accuracy: {results.get('accuracy', 0):.4f}\n"
                report += f"  Precision: {results.get('precision', 0):.4f}\n"
                report += f"  Recall: {results.get('recall', 0):.4f}\n"
                report += f"  F1-Score: {results.get('f1_score', 0):.4f}\n"
                if 'roc_auc' in results:
                    report += f"  ROC-AUC: {results['roc_auc']:.4f}\n"
                if 'pr_auc' in results:
                    report += f"  PR-AUC: {results['pr_auc']:.4f}\n"
                report += "\n"
            
            elif task_type == 'regression':
                report += "Regression Metrics:\n"
                report += "-" * 40 + "\n"
                report += f"  MSE: {results.get('mse', 0):.4f}\n"
                report += f"  RMSE: {results.get('rmse', 0):.4f}\n"
                report += f"  MAE: {results.get('mae', 0):.4f}\n"
                report += f"  R²: {results.get('r2', 0):.4f}\n"
                report += f"  MAPE: {results.get('mape', 0):.2f}%\n"
                report += "\n"
            
            elif task_type == 'clustering':
                report += "Clustering Metrics:\n"
                report += "-" * 40 + "\n"
                report += f"  Silhouette Score: {results.get('silhouette_score', 0):.4f}\n"
                report += f"  Calinski-Harabasz: {results.get('calinski_harabasz_score', 0):.4f}\n"
                report += f"  Davies-Bouldin: {results.get('davies_bouldin_score', 0):.4f}\n"
                report += "\n"
            
            elif task_type == 'ranking':
                report += "Ranking Metrics:\n"
                report += "-" * 40 + "\n"
                for key, value in results.items():
                    report += f"  {key}: {value:.4f}\n"
                report += "\n"
            
            elif task_type == 'cross_validation':
                report += "Cross Validation:\n"
                report += "-" * 40 + "\n"
                report += f"  Test Mean: {results.get('test_mean', 0):.4f} ± {results.get('test_std', 0):.4f}\n"
                report += f"  Train Mean: {results.get('train_mean', 0):.4f} ± {results.get('train_std', 0):.4f}\n"
                report += "\n"
        
        return report


class CrossValidator:
    """交叉验证器"""
    
    def __init__(self, model: Any, cv: int = 5, scoring: str = 'accuracy',
                 random_state: int = 42):
        """初始化交叉验证器
        
        Args:
            model: 模型对象
            cv: 交叉验证折数
            scoring: 评分指标
            random_state: 随机种子
        """
        self.model = model
        self.cv = cv
        self.scoring = scoring
        self.random_state = random_state
    
    def validate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """执行交叉验证"""
        from sklearn.model_selection import cross_val_score, cross_val_predict
        
        scores = cross_val_score(self.model, X, y, cv=self.cv, scoring=self.scoring)
        predictions = cross_val_predict(self.model, X, y, cv=self.cv)
        
        return {
            'scores': scores.tolist(),
            'mean': np.mean(scores),
            'std': np.std(scores),
            'predictions': predictions.tolist()
        }
    
    def grid_search(self, X: np.ndarray, y: np.ndarray,
                   param_grid: Dict[str, List[Any]]) -> Dict[str, Any]:
        """网格搜索"""
        from sklearn.model_selection import GridSearchCV
        
        grid_search = GridSearchCV(
            self.model, param_grid, cv=self.cv, scoring=self.scoring,
            n_jobs=-1, return_train_score=True
        )
        grid_search.fit(X, y)
        
        return {
            'best_params': grid_search.best_params_,
            'best_score': grid_search.best_score_,
            'cv_results': grid_search.cv_results_
        }


class ModelComparison:
    """模型比较器"""
    
    def __init__(self, models: Dict[str, Any]):
        """初始化模型比较器
        
        Args:
            models: 模型字典 {模型名: 模型对象}
        """
        self.models = models
        self.results = {}
    
    def compare(self, X_test: np.ndarray, y_test: np.ndarray,
                metrics: List[str] = None) -> pd.DataFrame:
        """比较模型"""
        if metrics is None:
            metrics = ['accuracy', 'precision', 'recall', 'f1_score']
        
        results = []
        
        for name, model in self.models.items():
            row = {'model': name}
            
            # 预测
            y_pred = model.predict(X_test)
            
            if hasattr(model, 'predict_proba'):
                y_prob = model.predict_proba(X_test)
            else:
                y_prob = None
            
            # 计算指标
            if 'accuracy' in metrics:
                row['accuracy'] = accuracy_score(y_test, y_pred)
            
            if 'precision' in metrics:
                row['precision'] = precision_score(y_test, y_pred, average='weighted', zero_division=0)
            
            if 'recall' in metrics:
                row['recall'] = recall_score(y_test, y_pred, average='weighted', zero_division=0)
            
            if 'f1_score' in metrics:
                row['f1_score'] = f1_score(y_test, y_pred, average='weighted', zero_division=0)
            
            if 'roc_auc' in metrics and y_prob is not None:
                from sklearn.metrics import roc_auc_score
                if len(np.unique(y_test)) == 2:
                    row['roc_auc'] = roc_auc_score(y_test, y_prob[:, 1])
                else:
                    row['roc_auc'] = roc_auc_score(y_test, y_prob, multi_class='ovr')
            
            results.append(row)
        
        df = pd.DataFrame(results)
        self.results = df
        return df
    
    def get_best_model(self, metric: str = 'accuracy') -> str:
        """获取最佳模型"""
        if self.results.empty:
            return None
        
        best_idx = self.results[metric].idxmax()
        return self.results.loc[best_idx, 'model']


def generate_evaluation_report(y_true: np.ndarray, y_pred: np.ndarray,
                               task_type: str = 'classification',
                               y_prob: Optional[np.ndarray] = None) -> str:
    """生成评估报告"""
    if task_type == 'classification':
        evaluator = ClassificationEvaluator(y_true, y_pred, y_prob)
        metrics = evaluator.get_all_metrics()
        
        report = "\nClassification Report:\n"
        report += "=" * 50 + "\n"
        report += f"Accuracy: {metrics['accuracy']:.4f}\n"
        report += f"Precision: {metrics['precision']:.4f}\n"
        report += f"Recall: {metrics['recall']:.4f}\n"
        report += f"F1-Score: {metrics['f1_score']:.4f}\n"
        
        if 'roc_auc' in metrics:
            report += f"ROC-AUC: {metrics['roc_auc']:.4f}\n"
        
        report += "\nConfusion Matrix:\n"
        cm = metrics['confusion_matrix']
        report += str(np.array(cm)) + "\n"
        
        return report
    
    elif task_type == 'regression':
        evaluator = RegressionEvaluator(y_true, y_pred)
        metrics = evaluator.get_all_metrics()
        
        report = "\nRegression Report:\n"
        report += "=" * 50 + "\n"
        report += f"MSE: {metrics['mse']:.4f}\n"
        report += f"RMSE: {metrics['rmse']:.4f}\n"
        report += f"MAE: {metrics['mae']:.4f}\n"
        report += f"R²: {metrics['r2']:.4f}\n"
        report += f"MAPE: {metrics['mape']:.2f}%\n"
        
        return report
    
    else:
        return "Unsupported task type"


def plot_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray,
                         class_names: Optional[List[str]] = None,
                         save_path: str = None):
    """绘制混淆矩阵"""
    cm = confusion_matrix(y_true, y_pred)
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names)
    plt.title('Confusion Matrix')
    plt.xlabel('Predicted Label')
    plt.ylabel('True Label')
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()


def plot_roc_curve(y_true: np.ndarray, y_prob: np.ndarray,
                  class_names: Optional[List[str]] = None,
                  save_path: str = None):
    """绘制ROC曲线"""
    plt.figure(figsize=(10, 8))
    
    n_classes = y_prob.shape[1] if len(y_prob.shape) > 1 else 2
    
    if n_classes == 2:
        fpr, tpr, _ = roc_curve(y_true, y_prob[:, 1] if len(y_prob.shape) > 1 else y_prob)
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, lw=2, label=f'ROC (AUC = {roc_auc:.2f})')
    else:
        for i in range(n_classes):
            y_true_bin = (y_true == i).astype(int)
            fpr, tpr, _ = roc_curve(y_true_bin, y_prob[:, i])
            roc_auc = auc(fpr, tpr)
            label = class_names[i] if class_names else f'Class {i}'
            plt.plot(fpr, tpr, lw=2, label=f'{label} (AUC = {roc_auc:.2f})')
    
    plt.plot([0, 1], [0, 1], 'k--', lw=2)
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curves')
    plt.legend(loc='lower right')
    plt.grid(True)
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()


def plot_precision_recall_curve(y_true: np.ndarray, y_prob: np.ndarray,
                                class_names: Optional[List[str]] = None,
                                save_path: str = None):
    """绘制精确率-召回率曲线"""
    plt.figure(figsize=(10, 8))
    
    n_classes = y_prob.shape[1] if len(y_prob.shape) > 1 else 2
    
    if n_classes == 2:
        precision, recall, _ = precision_recall_curve(y_true, y_prob[:, 1] if len(y_prob.shape) > 1 else y_prob)
        ap = average_precision_score(y_true, y_prob[:, 1] if len(y_prob.shape) > 1 else y_prob)
        plt.plot(recall, precision, lw=2, label=f'PR (AP = {ap:.2f})')
    else:
        for i in range(n_classes):
            y_true_bin = (y_true == i).astype(int)
            precision, recall, _ = precision_recall_curve(y_true_bin, y_prob[:, i])
            ap = average_precision_score(y_true_bin, y_prob[:, i])
            label = class_names[i] if class_names else f'Class {i}'
            plt.plot(recall, precision, lw=2, label=f'{label} (AP = {ap:.2f})')
    
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curves')
    plt.legend(loc='best')
    plt.grid(True)
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()
        