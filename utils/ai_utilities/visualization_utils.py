"""
可视化工具模块

提供AI模型和数据可视化的工具函数，包括模型性能可视化、数据分布可视化、特征可视化等。
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
from typing import List, Dict, Any, Optional, Union, Tuple, Callable
from sklearn.metrics import confusion_matrix, roc_curve, auc, precision_recall_curve
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import warnings

try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False


class ModelVisualizer:
    """模型可视化器"""
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8),
                 style: str = 'seaborn-v0_8', dpi: int = 100):
        """初始化模型可视化器
        
        Args:
            figsize: 图像尺寸
            style: matplotlib样式
            dpi: 图像分辨率
        """
        self.figsize = figsize
        self.dpi = dpi
        plt.style.use(style)
        sns.set_palette("husl")
    
    def plot_confusion_matrix(self, y_true: np.ndarray, y_pred: np.ndarray,
                             class_names: Optional[List[str]] = None,
                             normalize: bool = False,
                             title: str = 'Confusion Matrix',
                             save_path: str = None,
                             figsize: Tuple[int, int] = None,
                             cmap: str = 'Blues'):
        """绘制混淆矩阵
        
        Args:
            y_true: 真实标签
            y_pred: 预测标签
            class_names: 类别名称
            normalize: 是否归一化
            title: 标题
            save_path: 保存路径
            figsize: 图像尺寸
            cmap: 颜色映射
        """
        cm = confusion_matrix(y_true, y_pred)
        
        if normalize:
            cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
            fmt = '.2f'
        else:
            fmt = 'd'
        
        if class_names is None:
            class_names = [f'Class {i}' for i in range(cm.shape[0])]
        
        figsize = figsize or self.figsize
        plt.figure(figsize=figsize, dpi=self.dpi)
        
        sns.heatmap(cm, annot=True, fmt=fmt, cmap=cmap,
                   xticklabels=class_names, yticklabels=class_names,
                   cbar_kws={'label': 'Normalized Count' if normalize else 'Count'})
        
        plt.title(title, fontsize=14, fontweight='bold')
        plt.xlabel('Predicted Label', fontsize=12)
        plt.ylabel('True Label', fontsize=12)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        plt.show()
    
    def plot_roc_curves(self, y_true: np.ndarray, y_prob: np.ndarray,
                       class_names: Optional[List[str]] = None,
                       title: str = 'ROC Curves',
                       save_path: str = None,
                       figsize: Tuple[int, int] = None):
        """绘制ROC曲线"""
        figsize = figsize or self.figsize
        plt.figure(figsize=figsize, dpi=self.dpi)
        
        n_classes = y_prob.shape[1] if len(y_prob.shape) > 1 else 2
        
        if n_classes == 2:
            fpr, tpr, _ = roc_curve(y_true, y_prob[:, 1] if len(y_prob.shape) > 1 else y_prob)
            roc_auc = auc(fpr, tpr)
            plt.plot(fpr, tpr, lw=2, label=f'ROC (AUC = {roc_auc:.3f})')
        else:
            colors = plt.cm.Set1(np.linspace(0, 1, n_classes))
            for i in range(n_classes):
                y_true_bin = (y_true == i).astype(int)
                fpr, tpr, _ = roc_curve(y_true_bin, y_prob[:, i])
                roc_auc = auc(fpr, tpr)
                label = class_names[i] if class_names else f'Class {i}'
                plt.plot(fpr, tpr, color=colors[i], lw=2,
                        label=f'{label} (AUC = {roc_auc:.3f})')
        
        plt.plot([0, 1], [0, 1], 'k--', lw=2, alpha=0.7)
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate', fontsize=12)
        plt.ylabel('True Positive Rate', fontsize=12)
        plt.title(title, fontsize=14, fontweight='bold')
        plt.legend(loc='lower right', fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        plt.show()
    
    def plot_precision_recall_curves(self, y_true: np.ndarray, y_prob: np.ndarray,
                                     class_names: Optional[List[str]] = None,
                                     title: str = 'Precision-Recall Curves',
                                     save_path: str = None,
                                     figsize: Tuple[int, int] = None):
        """绘制PR曲线"""
        from sklearn.metrics import precision_recall_curve, average_precision_score
        
        figsize = figsize or self.figsize
        plt.figure(figsize=figsize, dpi=self.dpi)
        
        n_classes = y_prob.shape[1] if len(y_prob.shape) > 1 else 2
        
        if n_classes == 2:
            precision, recall, _ = precision_recall_curve(
                y_true, y_prob[:, 1] if len(y_prob.shape) > 1 else y_prob
            )
            ap = average_precision_score(
                y_true, y_prob[:, 1] if len(y_prob.shape) > 1 else y_prob
            )
            plt.plot(recall, precision, lw=2, label=f'PR (AP = {ap:.3f})')
        else:
            colors = plt.cm.Set1(np.linspace(0, 1, n_classes))
            for i in range(n_classes):
                y_true_bin = (y_true == i).astype(int)
                precision, recall, _ = precision_recall_curve(y_true_bin, y_prob[:, i])
                ap = average_precision_score(y_true_bin, y_prob[:, i])
                label = class_names[i] if class_names else f'Class {i}'
                plt.plot(recall, precision, color=colors[i], lw=2,
                        label=f'{label} (AP = {ap:.3f})')
        
        plt.xlabel('Recall', fontsize=12)
        plt.ylabel('Precision', fontsize=12)
        plt.title(title, fontsize=14, fontweight='bold')
        plt.legend(loc='best', fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        plt.show()
    
    def plot_feature_importance(self, feature_names: List[str],
                               importance_scores: np.ndarray,
                               top_k: int = 20,
                               title: str = 'Feature Importance',
                               save_path: str = None,
                               figsize: Tuple[int, int] = None,
                               orientation: str = 'horizontal'):
        """绘制特征重要性"""
        figsize = figsize or self.figsize
        
        # 排序
        indices = np.argsort(importance_scores)[::-1][:top_k]
        sorted_features = [feature_names[i] for i in indices]
        sorted_scores = importance_scores[indices]
        
        plt.figure(figsize=figsize, dpi=self.dpi)
        
        if orientation == 'horizontal':
            y_pos = np.arange(len(sorted_features))
            plt.barh(y_pos, sorted_scores, align='center')
            plt.yticks(y_pos, sorted_features)
            plt.xlabel('Importance Score', fontsize=12)
            plt.gca().invert_yaxis()
        else:
            plt.bar(range(len(sorted_features)), sorted_scores, align='center')
            plt.xticks(range(len(sorted_features)), sorted_features, rotation=45, ha='right')
            plt.ylabel('Importance Score', fontsize=12)
        
        plt.title(f'{title} (Top {top_k})', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        plt.show()
    
    def plot_learning_curves(self, train_scores: List[float],
                            val_scores: List[float],
                            metric_name: str = 'Accuracy',
                            title: str = 'Learning Curves',
                            save_path: str = None,
                            figsize: Tuple[int, int] = None):
        """绘制学习曲线"""
        figsize = figsize or self.figsize
        epochs = range(1, len(train_scores) + 1)
        
        plt.figure(figsize=figsize, dpi=self.dpi)
        
        plt.plot(epochs, train_scores, 'o-', label='Training', linewidth=2, markersize=4)
        plt.plot(epochs, val_scores, 'o-', label='Validation', linewidth=2, markersize=4)
        
        plt.xlabel('Epoch', fontsize=12)
        plt.ylabel(metric_name, fontsize=12)
        plt.title(title, fontsize=14, fontweight='bold')
        plt.legend(loc='best', fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        plt.show()
    
    def plot_training_history(self, history: Dict[str, List[float]],
                             metrics: List[str] = None,
                             title: str = 'Training History',
                             save_path: str = None,
                             figsize: Tuple[int, int] = None):
        """绘制训练历史"""
        if metrics is None:
            metrics = [k for k in history.keys() if not k.startswith('val_')]
        
        n_metrics = len(metrics)
        figsize = figsize or (15, 4 * n_metrics)
        
        fig, axes = plt.subplots(n_metrics, 1, figsize=figsize, dpi=self.dpi)
        if n_metrics == 1:
            axes = [axes]
        
        for i, metric in enumerate(metrics):
            train_values = history.get(metric, [])
            val_values = history.get(f'val_{metric}', [])
            
            epochs = range(1, len(train_values) + 1)
            
            axes[i].plot(epochs, train_values, 'b-', label=f'Training {metric}', linewidth=2)
            if val_values:
                axes[i].plot(epochs, val_values, 'r-', label=f'Validation {metric}', linewidth=2)
            
            axes[i].set_xlabel('Epoch', fontsize=11)
            axes[i].set_ylabel(metric.replace('_', ' ').title(), fontsize=11)
            axes[i].set_title(f'{metric.replace("_", " ").title()} over Time', fontsize=12)
            axes[i].legend(loc='best', fontsize=10)
            axes[i].grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        plt.show()
    
    def plot_model_comparison(self, model_names: List[str],
                             scores: Dict[str, List[float]],
                             metric_name: str = 'Score',
                             title: str = 'Model Comparison',
                             save_path: str = None,
                             figsize: Tuple[int, int] = None):
        """绘制模型比较图"""
        figsize = figsize or self.figsize
        
        x = np.arange(len(model_names))
        width = 0.8 / len(scores) if len(scores) > 1 else 0.4
        
        plt.figure(figsize=figsize, dpi=self.dpi)
        
        colors = plt.cm.Set1(np.linspace(0, 1, len(scores)))
        
        for i, (score_name, values) in enumerate(scores.items()):
            offset = (i - len(scores)/2 + 0.5) * width
            bars = plt.bar(x + offset, values, width, label=score_name,
                          color=colors[i], alpha=0.8)
            
            # 添加数值标签
            for bar, value in zip(bars, values):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{value:.3f}', ha='center', va='bottom', fontsize=9)
        
        plt.xlabel('Models', fontsize=12)
        plt.ylabel(metric_name, fontsize=12)
        plt.title(title, fontsize=14, fontweight='bold')
        plt.xticks(x, model_names, rotation=45, ha='right')
        plt.legend(loc='best', fontsize=10)
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
        plt.show()


class DataVisualizer:
    """数据可视化器"""
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8),
                 style: str = 'seaborn-v0_8'):
        """初始化数据可视化器"""
        self.figsize = figsize
        plt.style.use(style)
    
    def plot_data_distribution(self, data: np.ndarray,
                              feature_names: Optional[List[str]] = None,
                              bins: int = 30,
                              title: str = 'Data Distribution',
                              save_path: str = None,
                              figsize: Tuple[int, int] = None):
        """绘制数据分布"""
        n_features = data.shape[1]
        n_cols = min(4, n_features)
        n_rows = (n_features + n_cols - 1) // n_cols
        
        figsize = figsize or (15, 3 * n_rows)
        fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
        axes = axes.flatten() if n_rows * n_cols > 1 else [axes]
        
        for i in range(n_features):
            axes[i].hist(data[:, i], bins=bins, alpha=0.7, color='steelblue', edgecolor='black')
            feature_name = feature_names[i] if feature_names else f'Feature {i+1}'
            axes[i].set_title(feature_name, fontsize=11)
            axes[i].set_xlabel('Value', fontsize=10)
            axes[i].set_ylabel('Frequency', fontsize=10)
            axes[i].grid(True, alpha=0.3)
        
        # 隐藏多余的子图
        for i in range(n_features, len(axes)):
            axes[i].set_visible(False)
        
        plt.suptitle(title, fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_correlation_matrix(self, data: np.ndarray,
                               feature_names: Optional[List[str]] = None,
                               method: str = 'pearson',
                               title: str = 'Correlation Matrix',
                               save_path: str = None,
                               figsize: Tuple[int, int] = None):
        """绘制相关性矩阵"""
        figsize = figsize or self.figsize
        
        if feature_names is None:
            feature_names = [f'F{i}' for i in range(data.shape[1])]
        
        df = pd.DataFrame(data, columns=feature_names)
        
        if method == 'pearson':
            corr_matrix = df.corr()
        elif method == 'spearman':
            corr_matrix = df.corr(method='spearman')
        elif method == 'kendall':
            corr_matrix = df.corr(method='kendall')
        else:
            corr_matrix = df.corr()
        
        plt.figure(figsize=figsize)
        
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
        sns.heatmap(corr_matrix, mask=mask, annot=True, fmt='.2f', cmap='coolwarm',
                   center=0, square=True, linewidths=1, cbar_kws={'label': 'Correlation'})
        
        plt.title(f'{title} ({method})', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_pairplot(self, data: np.ndarray,
                     labels: Optional[np.ndarray] = None,
                     feature_names: Optional[List[str]] = None,
                     title: str = 'Pair Plot',
                     save_path: str = None):
        """绘制配对图"""
        if feature_names is None:
            feature_names = [f'F{i}' for i in range(data.shape[1])]
        
        df = pd.DataFrame(data, columns=feature_names)
        
        if labels is not None:
            df['label'] = labels
            hue = 'label'
        else:
            hue = None
        
        g = sns.pairplot(df, hue=hue, diag_kind='hist', palette='husl')
        g.fig.suptitle(title, y=1.02, fontsize=14, fontweight='bold')
        
        if save_path:
            g.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_pca_variance(self, explained_variance_ratio: np.ndarray,
                         cumulative: bool = True,
                         title: str = 'PCA Explained Variance',
                         save_path: str = None,
                         figsize: Tuple[int, int] = None):
        """绘制PCA方差解释图"""
        figsize = figsize or self.figsize
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        # 单个组件方差
        n_components = len(explained_variance_ratio)
        x = range(1, n_components + 1)
        
        ax1.bar(x, explained_variance_ratio, alpha=0.7, color='steelblue')
        ax1.set_xlabel('Principal Component', fontsize=11)
        ax1.set_ylabel('Explained Variance Ratio', fontsize=11)
        ax1.set_title('Individual Variance', fontsize=12)
        ax1.grid(True, alpha=0.3)
        
        # 累积方差
        if cumulative:
            cumulative_variance = np.cumsum(explained_variance_ratio)
            ax2.plot(x, cumulative_variance, 'bo-', linewidth=2, markersize=4)
            ax2.axhline(y=0.95, color='r', linestyle='--', alpha=0.7, label='95% threshold')
            ax2.set_xlabel('Number of Components', fontsize=11)
            ax2.set_ylabel('Cumulative Explained Variance', fontsize=11)
            ax2.set_title('Cumulative Variance', fontsize=12)
            ax2.legend(fontsize=10)
            ax2.grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_outliers(self, data: np.ndarray,
                     outlier_mask: np.ndarray,
                     feature_names: Optional[List[str]] = None,
                     title: str = 'Outlier Detection',
                     save_path: str = None,
                     figsize: Tuple[int, int] = None):
        """绘制异常值检测图"""
        if data.shape[1] == 2:
            # 2D数据
            figsize = figsize or self.figsize
            plt.figure(figsize=figsize)
            
            inliers = data[~outlier_mask]
            outliers = data[outlier_mask]
            
            plt.scatter(inliers[:, 0], inliers[:, 1], c='blue', label='Inliers', alpha=0.6)
            plt.scatter(outliers[:, 0], outliers[:, 1], c='red', label='Outliers', alpha=0.8, marker='x')
            
            x_label = feature_names[0] if feature_names else 'Feature 1'
            y_label = feature_names[1] if feature_names else 'Feature 2'
            plt.xlabel(x_label, fontsize=11)
            plt.ylabel(y_label, fontsize=11)
            plt.title(title, fontsize=14, fontweight='bold')
            plt.legend(fontsize=10)
            plt.grid(True, alpha=0.3)
            
        else:
            # 高维数据：使用PCA降维后可视化
            pca = PCA(n_components=2)
            data_2d = pca.fit_transform(data)
            
            figsize = figsize or self.figsize
            plt.figure(figsize=figsize)
            
            inliers = data_2d[~outlier_mask]
            outliers = data_2d[outlier_mask]
            
            plt.scatter(inliers[:, 0], inliers[:, 1], c='blue', label='Inliers', alpha=0.6)
            plt.scatter(outliers[:, 0], outliers[:, 1], c='red', label='Outliers', alpha=0.8, marker='x')
            
            var_ratio = pca.explained_variance_ratio_
            plt.xlabel(f'PC1 ({var_ratio[0]:.1%})', fontsize=11)
            plt.ylabel(f'PC2 ({var_ratio[1]:.1%})', fontsize=11)
            plt.title(f'{title} (PCA Projection)', fontsize=14, fontweight='bold')
            plt.legend(fontsize=10)
            plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()


class FeatureVisualizer:
    """特征可视化器"""
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8)):
        self.figsize = figsize
    
    def plot_feature_histograms(self, X: np.ndarray,
                               feature_names: Optional[List[str]] = None,
                               bins: int = 30,
                               title: str = 'Feature Histograms',
                               save_path: str = None):
        """绘制特征直方图"""
        n_features = X.shape[1]
        n_cols = min(4, n_features)
        n_rows = (n_features + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 3 * n_rows))
        axes = axes.flatten() if n_rows * n_cols > 1 else [axes]
        
        for i in range(n_features):
            axes[i].hist(X[:, i], bins=bins, alpha=0.7, color='steelblue', edgecolor='black')
            axes[i].set_title(feature_names[i] if feature_names else f'Feature {i+1}')
            axes[i].set_xlabel('Value')
            axes[i].set_ylabel('Frequency')
            axes[i].grid(True, alpha=0.3)
        
        for i in range(n_features, len(axes)):
            axes[i].set_visible(False)
        
        plt.suptitle(title, fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_feature_boxplots(self, X: np.ndarray,
                             feature_names: Optional[List[str]] = None,
                             title: str = 'Feature Boxplots',
                             save_path: str = None,
                             figsize: Tuple[int, int] = None):
        """绘制特征箱线图"""
        figsize = figsize or self.figsize
        
        df = pd.DataFrame(X, columns=feature_names if feature_names else [f'F{i}' for i in range(X.shape[1])])
        
        plt.figure(figsize=figsize)
        df.boxplot(rot=45)
        plt.title(title, fontsize=14, fontweight='bold')
        plt.ylabel('Value', fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_feature_violinplots(self, X: np.ndarray,
                                feature_names: Optional[List[str]] = None,
                                title: str = 'Feature Violin Plots',
                                save_path: str = None,
                                figsize: Tuple[int, int] = None):
        """绘制特征小提琴图"""
        figsize = figsize or self.figsize
        
        df = pd.DataFrame(X, columns=feature_names if feature_names else [f'F{i}' for i in range(X.shape[1])])
        df_melted = df.melt(var_name='Feature', value_name='Value')
        
        plt.figure(figsize=figsize)
        sns.violinplot(data=df_melted, x='Feature', y='Value', palette='husl')
        plt.xticks(rotation=45)
        plt.title(title, fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()


class DimensionalityVisualizer:
    """降维可视化器"""
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8)):
        self.figsize = figsize
    
    def plot_pca(self, X: np.ndarray, labels: Optional[np.ndarray] = None,
                n_components: int = 2,
                title: str = 'PCA Projection',
                save_path: str = None,
                figsize: Tuple[int, int] = None):
        """绘制PCA降维结果"""
        figsize = figsize or self.figsize
        
        pca = PCA(n_components=n_components)
        X_pca = pca.fit_transform(X)
        
        if n_components == 2:
            plt.figure(figsize=figsize)
            
            if labels is not None:
                scatter = plt.scatter(X_pca[:, 0], X_pca[:, 1], c=labels, cmap='tab10', alpha=0.6)
                plt.colorbar(scatter)
            else:
                plt.scatter(X_pca[:, 0], X_pca[:, 1], alpha=0.6)
            
            var_ratio = pca.explained_variance_ratio_
            plt.xlabel(f'PC1 ({var_ratio[0]:.1%})', fontsize=11)
            plt.ylabel(f'PC2 ({var_ratio[1]:.1%})', fontsize=11)
            
        elif n_components == 3:
            from mpl_toolkits.mplot3d import Axes3D
            fig = plt.figure(figsize=figsize)
            ax = fig.add_subplot(111, projection='3d')
            
            if labels is not None:
                scatter = ax.scatter(X_pca[:, 0], X_pca[:, 1], X_pca[:, 2],
                                    c=labels, cmap='tab10', alpha=0.6)
                plt.colorbar(scatter)
            else:
                ax.scatter(X_pca[:, 0], X_pca[:, 1], X_pca[:, 2], alpha=0.6)
            
            ax.set_xlabel('PC1', fontsize=11)
            ax.set_ylabel('PC2', fontsize=11)
            ax.set_zlabel('PC3', fontsize=11)
        
        plt.title(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        return X_pca
    
    def plot_tsne(self, X: np.ndarray, labels: Optional[np.ndarray] = None,
                 perplexity: float = 30,
                 title: str = 't-SNE Visualization',
                 save_path: str = None,
                 figsize: Tuple[int, int] = None):
        """绘制t-SNE降维结果"""
        figsize = figsize or self.figsize
        
        tsne = TSNE(n_components=2, perplexity=perplexity, random_state=42)
        X_tsne = tsne.fit_transform(X)
        
        plt.figure(figsize=figsize)
        
        if labels is not None:
            scatter = plt.scatter(X_tsne[:, 0], X_tsne[:, 1], c=labels, cmap='tab10', alpha=0.6)
            plt.colorbar(scatter)
        else:
            plt.scatter(X_tsne[:, 0], X_tsne[:, 1], alpha=0.6)
        
        plt.xlabel('t-SNE Component 1', fontsize=11)
        plt.ylabel('t-SNE Component 2', fontsize=11)
        plt.title(f'{title} (perplexity={perplexity})', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        return X_tsne
    
    def plot_umap(self, X: np.ndarray, labels: Optional[np.ndarray] = None,
                 n_neighbors: int = 15, min_dist: float = 0.1,
                 title: str = 'UMAP Visualization',
                 save_path: str = None,
                 figsize: Tuple[int, int] = None):
        """绘制UMAP降维结果"""
        if not UMAP_AVAILABLE:
            warnings.warn("UMAP not installed. Please install umap-learn.")
            return None
        
        figsize = figsize or self.figsize
        
        reducer = umap.UMAP(n_neighbors=n_neighbors, min_dist=min_dist, random_state=42)
        X_umap = reducer.fit_transform(X)
        
        plt.figure(figsize=figsize)
        
        if labels is not None:
            scatter = plt.scatter(X_umap[:, 0], X_umap[:, 1], c=labels, cmap='tab10', alpha=0.6)
            plt.colorbar(scatter)
        else:
            plt.scatter(X_umap[:, 0], X_umap[:, 1], alpha=0.6)
        
        plt.xlabel('UMAP Component 1', fontsize=11)
        plt.ylabel('UMAP Component 2', fontsize=11)
        plt.title(f'{title} (neighbors={n_neighbors}, min_dist={min_dist})',
                 fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        return X_umap


class InteractiveVisualizer:
    """交互式可视化器"""
    
    @staticmethod
    def plot_3d_scatter(X: np.ndarray, labels: Optional[np.ndarray] = None,
                       feature_names: Optional[List[str]] = None,
                       title: str = '3D Scatter Plot',
                       save_path: str = None) -> go.Figure:
        """绘制3D散点图"""
        if X.shape[1] < 3:
            # 如果维度不足3，使用PCA升维
            pca = PCA(n_components=3)
            X_3d = pca.fit_transform(X)
        else:
            X_3d = X[:, :3]
        
        fig = go.Figure()
        
        if labels is not None:
            unique_labels = np.unique(labels)
            colors = px.colors.qualitative.Set1
            
            for i, label in enumerate(unique_labels):
                mask = labels == label
                fig.add_trace(go.Scatter3d(
                    x=X_3d[mask, 0],
                    y=X_3d[mask, 1],
                    z=X_3d[mask, 2],
                    mode='markers',
                    marker=dict(size=5, color=colors[i % len(colors)]),
                    name=f'Class {label}'
                ))
        else:
            fig.add_trace(go.Scatter3d(
                x=X_3d[:, 0],
                y=X_3d[:, 1],
                z=X_3d[:, 2],
                mode='markers',
                marker=dict(size=5, color='blue', opacity=0.6)
            ))
        
        if feature_names:
            x_name, y_name, z_name = feature_names[:3]
        else:
            x_name, y_name, z_name = 'X', 'Y', 'Z'
        
        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title=x_name,
                yaxis_title=y_name,
                zaxis_title=z_name
            ),
            width=800,
            height=600
        )
        
        if save_path:
            fig.write_html(save_path)
        
        return fig
    
    @staticmethod
    def plot_interactive_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray,
                                         class_names: Optional[List[str]] = None,
                                         title: str = 'Interactive Confusion Matrix',
                                         save_path: str = None) -> go.Figure:
        """绘制交互式混淆矩阵"""
        cm = confusion_matrix(y_true, y_pred)
        
        if class_names is None:
            class_names = [f'Class {i}' for i in range(cm.shape[0])]
        
        fig = go.Figure(data=go.Heatmap(
            z=cm,
            x=class_names,
            y=class_names,
            colorscale='Blues',
            text=cm,
            texttemplate='%{text}',
            textfont={'size': 12},
            hoverongaps=False,
            hovertemplate='True: %{y}<br>Predicted: %{x}<br>Count: %{z}<extra></extra>'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title='Predicted Label',
            yaxis_title='True Label',
            width=700,
            height=600
        )
        
        if save_path:
            fig.write_html(save_path)
        
        return fig
    
    @staticmethod
    def plot_interactive_roc_curves(y_true: np.ndarray, y_prob: np.ndarray,
                                   class_names: Optional[List[str]] = None,
                                   title: str = 'Interactive ROC Curves',
                                   save_path: str = None) -> go.Figure:
        """绘制交互式ROC曲线"""
        fig = go.Figure()
        
        n_classes = y_prob.shape[1] if len(y_prob.shape) > 1 else 2
        
        if n_classes == 2:
            fpr, tpr, _ = roc_curve(y_true, y_prob[:, 1] if len(y_prob.shape) > 1 else y_prob)
            roc_auc = auc(fpr, tpr)
            
            fig.add_trace(go.Scatter(
                x=fpr, y=tpr,
                mode='lines',
                name=f'ROC (AUC = {roc_auc:.3f})',
                line=dict(color='darkorange', width=2)
            ))
        else:
            colors = px.colors.qualitative.Set1
            for i in range(n_classes):
                y_true_bin = (y_true == i).astype(int)
                fpr, tpr, _ = roc_curve(y_true_bin, y_prob[:, i])
                roc_auc = auc(fpr, tpr)
                label = class_names[i] if class_names else f'Class {i}'
                
                fig.add_trace(go.Scatter(
                    x=fpr, y=tpr,
                    mode='lines',
                    name=f'{label} (AUC = {roc_auc:.3f})',
                    line=dict(color=colors[i % len(colors)], width=2)
                ))
        
        # 添加对角线
        fig.add_trace(go.Scatter(
            x=[0, 1], y=[0, 1],
            mode='lines',
            name='Random',
            line=dict(color='black', width=2, dash='dash')
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title='False Positive Rate',
            yaxis_title='True Positive Rate',
            xaxis=dict(range=[0, 1]),
            yaxis=dict(range=[0, 1.05]),
            width=800,
            height=600,
            hovermode='x unified'
        )
        
        if save_path:
            fig.write_html(save_path)
        
        return fig
    
    @staticmethod
    def plot_model_comparison_dashboard(models: Dict[str, Any],
                                       X_test: np.ndarray,
                                       y_test: np.ndarray,
                                       title: str = 'Model Comparison Dashboard',
                                       save_path: str = None) -> go.Figure:
        """绘制模型比较仪表板"""
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Accuracy', 'Precision', 'Recall', 'F1-Score'),
            specs=[[{'type': 'bar'}, {'type': 'bar'}],
                   [{'type': 'bar'}, {'type': 'bar'}]]
        )
        
        metrics = {
            'accuracy': [],
            'precision': [],
            'recall': [],
            'f1_score': []
        }
        
        model_names = list(models.keys())
        
        for name, model in models.items():
            y_pred = model.predict(X_test)
            
            metrics['accuracy'].append(accuracy_score(y_test, y_pred))
            metrics['precision'].append(precision_score(y_test, y_pred, average='weighted', zero_division=0))
            metrics['recall'].append(recall_score(y_test, y_pred, average='weighted', zero_division=0))
            metrics['f1_score'].append(f1_score(y_test, y_pred, average='weighted', zero_division=0))
        
        colors = px.colors.qualitative.Set1
        
        for i, (metric_name, values) in enumerate(metrics.items()):
            row = i // 2 + 1
            col = i % 2 + 1
            
            fig.add_trace(
                go.Bar(
                    x=model_names,
                    y=values,
                    name=metric_name,
                    marker_color=colors[i % len(colors)],
                    text=[f'{v:.3f}' for v in values],
                    textposition='outside'
                ),
                row=row, col=col
            )
        
        fig.update_layout(
            title=title,
            showlegend=False,
            height=800,
            width=1000,
            hovermode='x unified'
        )
        
        if save_path:
            fig.write_html(save_path)
        
        return fig


class SHAPVisualizer:
    """SHAP值可视化器"""
    
    def __init__(self, model, X: np.ndarray, feature_names: Optional[List[str]] = None):
        """初始化SHAP可视化器"""
        if not SHAP_AVAILABLE:
            raise ImportError("SHAP not installed. Please install shap.")
        
        self.model = model
        self.X = X
        self.feature_names = feature_names or [f'Feature {i}' for i in range(X.shape[1])]
        
        # 创建解释器
        if hasattr(model, 'predict_proba'):
            self.explainer = shap.TreeExplainer(model) if hasattr(model, 'tree_') else shap.KernelExplainer(model.predict_proba, X[:100])
        else:
            self.explainer = shap.TreeExplainer(model) if hasattr(model, 'tree_') else shap.KernelExplainer(model.predict, X[:100])
        
        self.shap_values = self.explainer.shap_values(X[:100])  # 限制样本数
    
    def plot_summary(self, max_display: int = 20,
                    save_path: str = None):
        """绘制SHAP摘要图"""
        plt.figure(figsize=(10, max_display // 2))
        shap.summary_plot(self.shap_values, self.X[:100], feature_names=self.feature_names,
                         max_display=max_display, show=False)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_waterfall(self, index: int = 0,
                      save_path: str = None):
        """绘制瀑布图"""
        shap.waterfall_plot(shap.Explanation(values=self.shap_values[index],
                                            base_values=self.explainer.expected_value,
                                            data=self.X[index],
                                            feature_names=self.feature_names),
                           show=False)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_force(self, index: int = 0,
                  save_path: str = None):
        """绘制力图"""
        shap.force_plot(self.explainer.expected_value, self.shap_values[index],
                       self.X[index], feature_names=self.feature_names,
                       matplotlib=True, show=False)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()


def create_dashboard(model_evaluations: Dict[str, Dict[str, Any]],
                    save_path: str = None) -> go.Figure:
    """创建综合仪表板"""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Model Performance', 'Confusion Matrix',
                       'Feature Importance', 'Learning Curves'),
        specs=[[{'type': 'bar'}, {'type': 'heatmap'}],
               [{'type': 'bar'}, {'type': 'scatter'}]]
    )
    
    # 模型性能
    model_names = list(model_evaluations.keys())
    accuracies = [eval.get('accuracy', 0) for eval in model_evaluations.values()]
    
    fig.add_trace(
        go.Bar(x=model_names, y=accuracies, name='Accuracy',
               marker_color='steelblue', text=[f'{v:.3f}' for v in accuracies],
               textposition='outside'),
        row=1, col=1
    )
    
    # 混淆矩阵（取第一个模型）
    if 'confusion_matrix' in model_evaluations[model_names[0]]:
        cm = model_evaluations[model_names[0]]['confusion_matrix']
        fig.add_trace(
            go.Heatmap(z=cm, colorscale='Blues', showscale=False,
                      hovertemplate='True: %{y}<br>Predicted: %{x}<br>Count: %{z}<extra></extra>'),
            row=1, col=2
        )
    
    # 特征重要性
    if 'feature_importance' in model_evaluations[model_names[0]]:
        fi = model_evaluations[model_names[0]]['feature_importance']
        features = list(fi.keys())[:10]
        scores = list(fi.values())[:10]
        
        fig.add_trace(
            go.Bar(x=scores, y=features, orientation='h',
                   name='Importance', marker_color='coral'),
            row=2, col=1
        )
    
    # 学习曲线
    if 'learning_curve' in model_evaluations[model_names[0]]:
        lc = model_evaluations[model_names[0]]['learning_curve']
        fig.add_trace(
            go.Scatter(x=lc.get('train_sizes', []), y=lc.get('train_scores', []),
                      mode='lines+markers', name='Train', line=dict(color='blue')),
            row=2, col=2
        )
        fig.add_trace(
            go.Scatter(x=lc.get('train_sizes', []), y=lc.get('test_scores', []),
                      mode='lines+markers', name='Test', line=dict(color='red')),
            row=2, col=2
        )
    
    fig.update_layout(
        title='Model Evaluation Dashboard',
        height=900,
        width=1200,
        showlegend=True,
        hovermode='x unified'
    )
    
    if save_path:
        fig.write_html(save_path)
    
    return fig


def plot_learning_curves(train_scores: List[float], val_scores: List[float],
                        metric_name: str = 'Accuracy', title: str = 'Learning Curves',
                        save_path: str = None):
    """绘制学习曲线（便捷函数）"""
    visualizer = ModelVisualizer()
    visualizer.plot_learning_curves(train_scores, val_scores, metric_name, title, save_path)


def plot_feature_importance(feature_names: List[str], importance_scores: np.ndarray,
                           top_k: int = 20, title: str = 'Feature Importance',
                           save_path: str = None):
    """绘制特征重要性（便捷函数）"""
    visualizer = ModelVisualizer()
    visualizer.plot_feature_importance(feature_names, importance_scores, top_k, title, save_path)


def plot_correlation_matrix(data: np.ndarray, feature_names: Optional[List[str]] = None,
                           title: str = 'Correlation Matrix', save_path: str = None):
    """绘制相关性矩阵（便捷函数）"""
    visualizer = DataVisualizer()
    visualizer.plot_correlation_matrix(data, feature_names, 'pearson', title, save_path)


def plot_pca_variance(explained_variance_ratio: np.ndarray,
                     title: str = 'PCA Explained Variance', save_path: str = None):
    """绘制PCA方差解释图（便捷函数）"""
    visualizer = DataVisualizer()
    visualizer.plot_pca_variance(explained_variance_ratio, True, title, save_path)


def plot_tsne(X: np.ndarray, labels: Optional[np.ndarray] = None,
             perplexity: float = 30, title: str = 't-SNE Visualization',
             save_path: str = None) -> np.ndarray:
    """绘制t-SNE降维结果（便捷函数）"""
    visualizer = DimensionalityVisualizer()
    return visualizer.plot_tsne(X, labels, perplexity, title, save_path)


def plot_umap(X: np.ndarray, labels: Optional[np.ndarray] = None,
             n_neighbors: int = 15, min_dist: float = 0.1,
             title: str = 'UMAP Visualization', save_path: str = None) -> np.ndarray:
    """绘制UMAP降维结果（便捷函数）"""
    visualizer = DimensionalityVisualizer()
    return visualizer.plot_umap(X, labels, n_neighbors, min_dist, title, save_path)


def plot_shap_values(model, X: np.ndarray, feature_names: Optional[List[str]] = None,
                    max_display: int = 20, save_path: str = None):
    """绘制SHAP值（便捷函数）"""
    if not SHAP_AVAILABLE:
        warnings.warn("SHAP not installed. Please install shap.")
        return
    
    visualizer = SHAPVisualizer(model, X, feature_names)
    visualizer.plot_summary(max_display, save_path)


def plot_lime_explanation(explanation, save_path: str = None):
    """绘制LIME解释（便捷函数）"""
    if not hasattr(explanation, 'as_pyplot_figure'):
        warnings.warn("Invalid LIME explanation object.")
        return
    
    fig = explanation.as_pyplot_figure()
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()