"""
训练工具模块

提供AI模型训练的工具函数，包括PyTorch、TensorFlow训练器、回调函数、学习率调度等。
"""

import os
import json
import time
import copy
import warnings
from typing import List, Dict, Any, Optional, Union, Tuple, Callable
from datetime import datetime
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, TensorDataset
import tensorflow as tf
from tensorflow import keras
import matplotlib.pyplot as plt


class TrainingHistory:
    """训练历史记录类"""
    
    def __init__(self):
        self.epochs = []
        self.metrics = {}
        self.best_epoch = -1
        self.best_value = None
    
    def add_epoch(self, epoch: int, **kwargs):
        """添加一个epoch的记录"""
        self.epochs.append(epoch)
        for key, value in kwargs.items():
            if key not in self.metrics:
                self.metrics[key] = []
            self.metrics[key].append(value)
    
    def get_metric(self, metric_name: str) -> List[float]:
        """获取指定指标的历史"""
        return self.metrics.get(metric_name, [])
    
    def get_best(self, metric_name: str, mode: str = 'min') -> Tuple[float, int]:
        """获取最佳指标值及对应epoch"""
        values = self.metrics.get(metric_name, [])
        if not values:
            return None, -1
        
        if mode == 'min':
            best_value = min(values)
        else:
            best_value = max(values)
        
        best_epoch = values.index(best_value)
        return best_value, best_epoch
    
    def plot(self, metrics: List[str] = None, save_path: str = None):
        """绘制训练曲线"""
        if metrics is None:
            metrics = list(self.metrics.keys())
        
        n_metrics = len(metrics)
        fig, axes = plt.subplots(1, n_metrics, figsize=(5 * n_metrics, 4))
        if n_metrics == 1:
            axes = [axes]
        
        for i, metric in enumerate(metrics):
            axes[i].plot(self.epochs, self.metrics[metric], 'b-', label=metric)
            axes[i].set_xlabel('Epoch')
            axes[i].set_ylabel(metric)
            axes[i].set_title(f'{metric} over time')
            axes[i].legend()
            axes[i].grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'epochs': self.epochs,
            'metrics': self.metrics,
            'best_epoch': self.best_epoch,
            'best_value': self.best_value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrainingHistory':
        """从字典创建"""
        history = cls()
        history.epochs = data.get('epochs', [])
        history.metrics = data.get('metrics', {})
        history.best_epoch = data.get('best_epoch', -1)
        history.best_value = data.get('best_value')
        return history


class EarlyStopping:
    """早停回调"""
    
    def __init__(self, monitor: str = 'val_loss', mode: str = 'min',
                 patience: int = 10, min_delta: float = 0.0,
                 restore_best_weights: bool = True, verbose: bool = True):
        """初始化早停
        
        Args:
            monitor: 监控指标
            mode: 模式 ('min' 或 'max')
            patience: 耐心值
            min_delta: 最小改善
            restore_best_weights: 是否恢复最佳权重
            verbose: 是否打印信息
        """
        self.monitor = monitor
        self.mode = mode
        self.patience = patience
        self.min_delta = min_delta
        self.restore_best_weights = restore_best_weights
        self.verbose = verbose
        
        self.best_value = float('inf') if mode == 'min' else float('-inf')
        self.best_weights = None
        self.wait = 0
        self.stopped_epoch = 0
        self.stop_training = False
    
    def __call__(self, epoch: int, model: Any, **kwargs):
        """检查是否停止训练"""
        current_value = kwargs.get(self.monitor)
        
        if current_value is None:
            return
        
        # 检查是否改善
        if self.mode == 'min':
            improved = current_value < self.best_value - self.min_delta
        else:
            improved = current_value > self.best_value + self.min_delta
        
        if improved:
            self.best_value = current_value
            self.wait = 0
            if self.restore_best_weights:
                self.best_weights = self._get_model_weights(model)
            if self.verbose:
                print(f"Epoch {epoch}: {self.monitor} improved to {current_value:.6f}")
        else:
            self.wait += 1
            if self.wait >= self.patience:
                self.stopped_epoch = epoch
                self.stop_training = True
                if self.verbose:
                    print(f"Early stopping triggered after epoch {epoch}")
    
    def _get_model_weights(self, model: Any) -> Any:
        """获取模型权重"""
        if isinstance(model, nn.Module):
            return copy.deepcopy(model.state_dict())
        elif isinstance(model, tf.keras.Model):
            return model.get_weights()
        else:
            return None
    
    def restore_best(self, model: Any):
        """恢复最佳权重"""
        if self.restore_best_weights and self.best_weights is not None:
            if isinstance(model, nn.Module):
                model.load_state_dict(self.best_weights)
            elif isinstance(model, tf.keras.Model):
                model.set_weights(self.best_weights)


class LearningRateScheduler:
    """学习率调度器"""
    
    def __init__(self, schedule_type: str = 'step', initial_lr: float = 0.01,
                 schedule_config: Optional[Dict[str, Any]] = None):
        """初始化学习率调度器
        
        Args:
            schedule_type: 调度类型 ('step', 'exponential', 'cosine', 'plateau', 'cyclic', 'one_cycle')
            initial_lr: 初始学习率
            schedule_config: 调度配置
        """
        self.schedule_type = schedule_type
        self.initial_lr = initial_lr
        self.schedule_config = schedule_config or {}
        self.current_epoch = 0
    
    def get_lr(self, epoch: int = None, metrics: Dict[str, float] = None) -> float:
        """获取当前学习率"""
        if epoch is not None:
            self.current_epoch = epoch
        
        if self.schedule_type == 'step':
            step_size = self.schedule_config.get('step_size', 10)
            gamma = self.schedule_config.get('gamma', 0.1)
            lr = self.initial_lr * (gamma ** (self.current_epoch // step_size))
        
        elif self.schedule_type == 'exponential':
            decay_rate = self.schedule_config.get('decay_rate', 0.95)
            lr = self.initial_lr * (decay_rate ** self.current_epoch)
        
        elif self.schedule_type == 'cosine':
            T_max = self.schedule_config.get('T_max', 100)
            eta_min = self.schedule_config.get('eta_min', 0)
            lr = eta_min + (self.initial_lr - eta_min) * (1 + np.cos(np.pi * self.current_epoch / T_max)) / 2
        
        elif self.schedule_type == 'plateau':
            if metrics is None:
                return self.initial_lr
            
            factor = self.schedule_config.get('factor', 0.1)
            patience = self.schedule_config.get('patience', 10)
            monitor = self.schedule_config.get('monitor', 'loss')
            mode = self.schedule_config.get('mode', 'min')
            
            # 这里需要历史记录，简化实现
            lr = self.initial_lr
        
        elif self.schedule_type == 'cyclic':
            base_lr = self.schedule_config.get('base_lr', self.initial_lr / 10)
            max_lr = self.schedule_config.get('max_lr', self.initial_lr)
            step_size = self.schedule_config.get('step_size', 20)
            
            cycle = np.floor(1 + self.current_epoch / (2 * step_size))
            x = np.abs(self.current_epoch / step_size - 2 * cycle + 1)
            lr = base_lr + (max_lr - base_lr) * np.maximum(0, (1 - x))
        
        elif self.schedule_type == 'one_cycle':
            max_lr = self.schedule_config.get('max_lr', self.initial_lr)
            total_steps = self.schedule_config.get('total_steps', 100)
            pct_start = self.schedule_config.get('pct_start', 0.3)
            
            if self.current_epoch < pct_start * total_steps:
                # 上升阶段
                lr = self.current_epoch / (pct_start * total_steps) * max_lr
            else:
                # 下降阶段
                lr = max_lr * (1 - (self.current_epoch - pct_start * total_steps) / 
                              (total_steps * (1 - pct_start)))
        
        else:
            lr = self.initial_lr
        
        return lr
    
    def step(self, epoch: int = None, metrics: Dict[str, float] = None) -> float:
        """步进一个epoch"""
        if epoch is not None:
            self.current_epoch = epoch
        else:
            self.current_epoch += 1
        
        return self.get_lr(metrics=metrics)


class ModelCheckpoint:
    """模型检查点"""
    
    def __init__(self, filepath: str, monitor: str = 'val_loss',
                 mode: str = 'min', save_best_only: bool = True,
                 save_weights_only: bool = False, verbose: bool = True):
        """初始化模型检查点
        
        Args:
            filepath: 保存路径
            monitor: 监控指标
            mode: 模式 ('min' 或 'max')
            save_best_only: 是否只保存最佳
            save_weights_only: 是否只保存权重
            verbose: 是否打印信息
        """
        self.filepath = filepath
        self.monitor = monitor
        self.mode = mode
        self.save_best_only = save_best_only
        self.save_weights_only = save_weights_only
        self.verbose = verbose
        
        self.best_value = float('inf') if mode == 'min' else float('-inf')
        self.best_epoch = -1
    
    def __call__(self, epoch: int, model: Any, **kwargs):
        """检查并保存模型"""
        current_value = kwargs.get(self.monitor)
        
        if current_value is None:
            return
        
        # 检查是否改善
        if self.mode == 'min':
            improved = current_value < self.best_value
        else:
            improved = current_value > self.best_value
        
        if improved:
            self.best_value = current_value
            self.best_epoch = epoch
            
            if self.save_best_only:
                self._save_model(model, epoch, current_value)
        elif not self.save_best_only:
            self._save_model(model, epoch, current_value)
    
    def _save_model(self, model: Any, epoch: int, value: float):
        """保存模型"""
        if self.verbose:
            print(f"Epoch {epoch}: saving model to {self.filepath} ({self.monitor}={value:.6f})")
        
        # 创建目录
        os.makedirs(os.path.dirname(os.path.abspath(self.filepath)), exist_ok=True)
        
        if isinstance(model, nn.Module):
            if self.save_weights_only:
                torch.save(model.state_dict(), self.filepath)
            else:
                torch.save(model, self.filepath)
        elif isinstance(model, tf.keras.Model):
            if self.save_weights_only:
                model.save_weights(self.filepath)
            else:
                model.save(self.filepath)


class TrainingMonitor:
    """训练监控器"""
    
    def __init__(self, log_dir: str = None, metrics: List[str] = None):
        """初始化训练监控器
        
        Args:
            log_dir: 日志目录
            metrics: 监控指标
        """
        self.log_dir = log_dir
        self.metrics = metrics or []
        self.history = TrainingHistory()
        self.start_time = None
        
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            self.log_file = os.path.join(log_dir, 'training_log.json')
    
    def on_train_begin(self):
        """训练开始"""
        self.start_time = time.time()
    
    def on_epoch_end(self, epoch: int, **kwargs):
        """epoch结束"""
        self.history.add_epoch(epoch, **kwargs)
        
        # 打印信息
        log_msg = f"Epoch {epoch}"
        for key, value in kwargs.items():
            if key in self.metrics or not self.metrics:
                log_msg += f" - {key}: {value:.6f}"
        print(log_msg)
        
        # 保存日志
        if self.log_dir:
            self._save_log()
    
    def on_train_end(self):
        """训练结束"""
        total_time = time.time() - self.start_time
        print(f"Training finished. Total time: {total_time:.2f}s")
        
        if self.log_dir:
            with open(os.path.join(self.log_dir, 'training_time.txt'), 'w') as f:
                f.write(f"Total time: {total_time:.2f}s")
    
    def _save_log(self):
        """保存日志"""
        log_data = {
            'history': self.history.to_dict(),
            'metrics': self.metrics
        }
        with open(self.log_file, 'w') as f:
            json.dump(log_data, f, indent=2)


class GradientClipper:
    """梯度裁剪器"""
    
    def __init__(self, clip_value: float = 1.0, clip_norm: float = None,
                 clip_type: str = 'value'):
        """初始化梯度裁剪器
        
        Args:
            clip_value: 裁剪值
            clip_norm: 裁剪范数
            clip_type: 裁剪类型 ('value', 'norm')
        """
        self.clip_value = clip_value
        self.clip_norm = clip_norm
        self.clip_type = clip_type
    
    def clip(self, model: nn.Module):
        """裁剪梯度"""
        if self.clip_type == 'value':
            torch.nn.utils.clip_grad_value_(model.parameters(), self.clip_value)
        elif self.clip_type == 'norm':
            torch.nn.utils.clip_grad_norm_(model.parameters(), self.clip_norm or self.clip_value)


class LearningRateWarmup:
    """学习率预热"""
    
    def __init__(self, warmup_steps: int, initial_lr: float, target_lr: float):
        """初始化学习率预热
        
        Args:
            warmup_steps: 预热步数
            initial_lr: 初始学习率
            target_lr: 目标学习率
        """
        self.warmup_steps = warmup_steps
        self.initial_lr = initial_lr
        self.target_lr = target_lr
        self.current_step = 0
    
    def get_lr(self) -> float:
        """获取当前学习率"""
        if self.current_step >= self.warmup_steps:
            return self.target_lr
        
        alpha = self.current_step / self.warmup_steps
        return self.initial_lr + alpha * (self.target_lr - self.initial_lr)
    
    def step(self):
        """步进"""
        self.current_step += 1
        return self.get_lr()


class CyclicLR:
    """循环学习率"""
    
    def __init__(self, base_lr: float, max_lr: float, step_size: int,
                 mode: str = 'triangular', gamma: float = 1.0):
        """初始化循环学习率
        
        Args:
            base_lr: 基础学习率
            max_lr: 最大学习率
            step_size: 步长
            mode: 模式 ('triangular', 'triangular2', 'exp_range')
            gamma: 衰减因子
        """
        self.base_lr = base_lr
        self.max_lr = max_lr
        self.step_size = step_size
        self.mode = mode
        self.gamma = gamma
        self.current_step = 0
    
    def get_lr(self) -> float:
        """获取当前学习率"""
        cycle = np.floor(1 + self.current_step / (2 * self.step_size))
        x = np.abs(self.current_step / self.step_size - 2 * cycle + 1)
        
        if self.mode == 'triangular':
            lr = self.base_lr + (self.max_lr - self.base_lr) * np.maximum(0, (1 - x))
        elif self.mode == 'triangular2':
            lr = self.base_lr + (self.max_lr - self.base_lr) * np.maximum(0, (1 - x)) / (2 ** (cycle - 1))
        elif self.mode == 'exp_range':
            lr = self.base_lr + (self.max_lr - self.base_lr) * np.maximum(0, (1 - x)) * (self.gamma ** self.current_step)
        else:
            lr = self.base_lr
        
        return lr
    
    def step(self):
        """步进"""
        self.current_step += 1
        return self.get_lr()


class TorchTrainer:
    """PyTorch训练器"""
    
    def __init__(self, model: nn.Module, criterion: nn.Module,
                 optimizer: optim.Optimizer, device: str = 'cuda',
                 scheduler: Any = None, clip_grad: GradientClipper = None):
        """初始化训练器
        
        Args:
            model: PyTorch模型
            criterion: 损失函数
            optimizer: 优化器
            device: 设备类型
            scheduler: 学习率调度器
            clip_grad: 梯度裁剪器
        """
        self.model = model.to(device)
        self.criterion = criterion
        self.optimizer = optimizer
        self.device = device
        self.scheduler = scheduler
        self.clip_grad = clip_grad
        
        self.history = TrainingHistory()
        self.monitor = TrainingMonitor()
        self.callbacks = []
    
    def add_callback(self, callback: Any):
        """添加回调"""
        self.callbacks.append(callback)
    
    def train_epoch(self, train_loader: DataLoader) -> Dict[str, float]:
        """训练一个epoch
        
        Args:
            train_loader: 训练数据加载器
            
        Returns:
            训练指标
        """
        self.model.train()
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        
        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(self.device), target.to(self.device)
            
            self.optimizer.zero_grad()
            output = self.model(data)
            loss = self.criterion(output, target)
            loss.backward()
            
            if self.clip_grad:
                self.clip_grad.clip(self.model)
            
            self.optimizer.step()
            
            total_loss += loss.item() * data.size(0)
            
            # 计算准确率（如果是分类任务）
            if output.size(1) > 1:  # 多分类
                pred = output.argmax(dim=1)
                total_correct += pred.eq(target).sum().item()
            else:  # 二分类
                pred = (output > 0.5).float()
                total_correct += pred.eq(target).sum().item()
            
            total_samples += data.size(0)
        
        avg_loss = total_loss / total_samples
        accuracy = total_correct / total_samples if total_correct > 0 else 0
        
        return {'loss': avg_loss, 'accuracy': accuracy}
    
    def validate(self, val_loader: DataLoader) -> Dict[str, float]:
        """验证
        
        Args:
            val_loader: 验证数据加载器
            
        Returns:
            验证指标
        """
        self.model.eval()
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        
        with torch.no_grad():
            for data, target in val_loader:
                data, target = data.to(self.device), target.to(self.device)
                output = self.model(data)
                loss = self.criterion(output, target)
                
                total_loss += loss.item() * data.size(0)
                
                if output.size(1) > 1:
                    pred = output.argmax(dim=1)
                    total_correct += pred.eq(target).sum().item()
                else:
                    pred = (output > 0.5).float()
                    total_correct += pred.eq(target).sum().item()
                
                total_samples += data.size(0)
        
        avg_loss = total_loss / total_samples
        accuracy = total_correct / total_samples if total_correct > 0 else 0
        
        return {'val_loss': avg_loss, 'val_accuracy': accuracy}
    
    def train(self, train_loader: DataLoader, val_loader: DataLoader = None,
              epochs: int = 100, callbacks: List[Any] = None) -> TrainingHistory:
        """完整训练过程
        
        Args:
            train_loader: 训练数据加载器
            val_loader: 验证数据加载器
            epochs: 训练轮数
            callbacks: 回调函数列表
            
        Returns:
            训练历史
        """
        all_callbacks = self.callbacks + (callbacks or [])
        self.monitor.on_train_begin()
        
        for epoch in range(1, epochs + 1):
            # 训练
            train_metrics = self.train_epoch(train_loader)
            
            # 验证
            if val_loader:
                val_metrics = self.validate(val_loader)
                metrics = {**train_metrics, **val_metrics}
            else:
                metrics = train_metrics
            
            # 更新学习率
            if self.scheduler:
                if isinstance(self.scheduler, LearningRateScheduler):
                    lr = self.scheduler.step(epoch, metrics)
                elif hasattr(self.scheduler, 'step'):
                    self.scheduler.step()
                elif callable(self.scheduler):
                    lr = self.scheduler(epoch, metrics)
            
            # 记录历史
            self.history.add_epoch(epoch, **metrics)
            
            # 回调
            for callback in all_callbacks:
                if hasattr(callback, '__call__'):
                    callback(epoch, model=self.model, **metrics)
            
            # 监控
            self.monitor.on_epoch_end(epoch, **metrics)
        
        self.monitor.on_train_end()
        return self.history
    
    def predict(self, test_loader: DataLoader) -> np.ndarray:
        """预测"""
        self.model.eval()
        predictions = []
        
        with torch.no_grad():
            for data, _ in test_loader:
                data = data.to(self.device)
                output = self.model(data)
                predictions.append(output.cpu().numpy())
        
        return np.concatenate(predictions)
    
    def save(self, path: str):
        """保存模型"""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'history': self.history.to_dict()
        }, path)
    
    def load(self, path: str):
        """加载模型"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.history = TrainingHistory.from_dict(checkpoint.get('history', {}))


class TensorFlowTrainer:
    """TensorFlow训练器"""
    
    def __init__(self, model: tf.keras.Model, optimizer: str = 'adam',
                 loss: str = 'sparse_categorical_crossentropy',
                 metrics: List[str] = None, callbacks: List = None):
        """初始化训练器
        
        Args:
            model: TensorFlow模型
            optimizer: 优化器
            loss: 损失函数
            metrics: 评估指标
            callbacks: 回调函数
        """
        self.model = model
        self.optimizer = optimizer
        self.loss = loss
        self.metrics = metrics or ['accuracy']
        self.callbacks = callbacks or []
        
        # 编译模型
        self.model.compile(
            optimizer=optimizer,
            loss=loss,
            metrics=self.metrics
        )
        
        self.history = None
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              X_val: np.ndarray = None, y_val: np.ndarray = None,
              epochs: int = 100, batch_size: int = 32,
              class_weight: Dict = None, sample_weight: np.ndarray = None,
              validation_split: float = 0.0, shuffle: bool = True,
              initial_epoch: int = 0, steps_per_epoch: int = None,
              validation_steps: int = None, verbose: int = 1) -> tf.keras.callbacks.History:
        """训练模型"""
        
        # 准备验证数据
        validation_data = None
        if X_val is not None and y_val is not None:
            validation_data = (X_val, y_val)
        
        # 训练模型
        self.history = self.model.fit(
            X_train, y_train,
            validation_data=validation_data,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            class_weight=class_weight,
            sample_weight=sample_weight,
            shuffle=shuffle,
            initial_epoch=initial_epoch,
            steps_per_epoch=steps_per_epoch,
            validation_steps=validation_steps,
            callbacks=self.callbacks,
            verbose=verbose
        )
        
        return self.history
    
    def train_generator(self, train_generator, steps_per_epoch: int,
                        validation_generator=None, validation_steps: int = None,
                        epochs: int = 100, class_weight: Dict = None,
                        initial_epoch: int = 0, verbose: int = 1) -> tf.keras.callbacks.History:
        """使用生成器训练"""
        
        self.history = self.model.fit(
            train_generator,
            steps_per_epoch=steps_per_epoch,
            validation_data=validation_generator,
            validation_steps=validation_steps,
            epochs=epochs,
            class_weight=class_weight,
            initial_epoch=initial_epoch,
            callbacks=self.callbacks,
            verbose=verbose
        )
        
        return self.history
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray,
                 batch_size: int = 32, verbose: int = 1) -> Dict[str, float]:
        """评估模型"""
        results = self.model.evaluate(X_test, y_test, batch_size=batch_size, verbose=verbose)
        
        if isinstance(results, list):
            return {name: value for name, value in zip(self.model.metrics_names, results)}
        else:
            return {self.model.metrics_names[0]: results}
    
    def predict(self, X: np.ndarray, batch_size: int = 32, verbose: int = 0) -> np.ndarray:
        """预测"""
        return self.model.predict(X, batch_size=batch_size, verbose=verbose)
    
    def save(self, path: str):
        """保存模型"""
        self.model.save(path)
    
    def load(self, path: str):
        """加载模型"""
        self.model = tf.keras.models.load_model(path)


def create_data_loader(X: np.ndarray, y: Optional[np.ndarray] = None,
                       batch_size: int = 32, shuffle: bool = True,
                       num_workers: int = 0, pin_memory: bool = False) -> DataLoader:
    """创建PyTorch数据加载器
    
    Args:
        X: 特征数据
        y: 标签数据
        batch_size: 批大小
        shuffle: 是否打乱
        num_workers: 工作线程数
        pin_memory: 是否固定内存
        
    Returns:
        数据加载器
    """
    if y is not None:
        if isinstance(y, np.ndarray):
            y = torch.from_numpy(y).long()
        dataset = TensorDataset(torch.FloatTensor(X), y)
    else:
        dataset = TensorDataset(torch.FloatTensor(X))
    
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=pin_memory
    )


class ExperimentTracker:
    """实验追踪器"""
    
    def __init__(self, experiment_name: str, log_dir: str = './experiments'):
        """初始化实验追踪器
        
        Args:
            experiment_name: 实验名称
            log_dir: 日志目录
        """
        self.experiment_name = experiment_name
        self.log_dir = os.path.join(log_dir, experiment_name, datetime.now().strftime('%Y%m%d_%H%M%S'))
        self.config = {}
        self.metrics = {}
        self.artifacts = []
        
        os.makedirs(self.log_dir, exist_ok=True)
    
    def log_config(self, config: Dict[str, Any]):
        """记录配置"""
        self.config.update(config)
        with open(os.path.join(self.log_dir, 'config.json'), 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def log_metrics(self, metrics: Dict[str, float], step: int = None):
        """记录指标"""
        for key, value in metrics.items():
            if key not in self.metrics:
                self.metrics[key] = []
            self.metrics[key].append({'value': value, 'step': step})
        
        # 保存指标
        with open(os.path.join(self.log_dir, 'metrics.json'), 'w') as f:
            json.dump(self.metrics, f, indent=2)
    
    def log_artifact(self, file_path: str, artifact_name: str = None):
        """记录工件"""
        import shutil
        
        if artifact_name is None:
            artifact_name = os.path.basename(file_path)
        
        dest_path = os.path.join(self.log_dir, artifact_name)
        shutil.copy2(file_path, dest_path)
        self.artifacts.append(artifact_name)
    
    def log_model(self, model: Any, model_name: str = 'model'):
        """记录模型"""
        if isinstance(model, nn.Module):
            model_path = os.path.join(self.log_dir, f'{model_name}.pt')
            torch.save(model.state_dict(), model_path)
        elif isinstance(model, tf.keras.Model):
            model_path = os.path.join(self.log_dir, model_name)
            model.save(model_path)
        
        self.artifacts.append(model_name)


class HyperparameterTuner:
    """超参数调优器"""
    
    def __init__(self, model_fn: Callable, param_grid: Dict[str, List],
                 scoring: str = 'val_accuracy', cv: int = 5,
                 n_trials: int = 10, random_state: int = 42):
        """初始化超参数调优器
        
        Args:
            model_fn: 模型创建函数
            param_grid: 参数网格
            scoring: 评分指标
            cv: 交叉验证折数
            n_trials: 试验次数
            random_state: 随机种子
        """
        self.model_fn = model_fn
        self.param_grid = param_grid
        self.scoring = scoring
        self.cv = cv
        self.n_trials = n_trials
        self.random_state = random_state
        self.best_params = None
        self.best_score = None
        self.results = []
    
    def grid_search(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """网格搜索"""
        from sklearn.model_selection import GridSearchCV
        
        # 创建包装器
        class ModelWrapper:
            def __init__(self, model_fn):
                self.model_fn = model_fn
                self.model = None
            
            def fit(self, X, y):
                self.model = self.model_fn(**self.model_params)
                if hasattr(self.model, 'fit'):
                    self.model.fit(X, y)
                return self
            
            def predict(self, X):
                if hasattr(self.model, 'predict'):
                    return self.model.predict(X)
                return None
            
            def score(self, X, y):
                if hasattr(self.model, 'score'):
                    return self.model.score(X, y)
                return 0
        
        # 创建参数网格
        param_grid = {}
        for key, values in self.param_grid.items():
            param_grid[f'model_params__{key}'] = values
        
        # 执行网格搜索
        grid_search = GridSearchCV(
            ModelWrapper(self.model_fn),
            param_grid,
            cv=self.cv,
            scoring=self.scoring,
            n_jobs=-1
        )
        
        grid_search.fit(X, y)
        
        self.best_params = grid_search.best_params_
        self.best_score = grid_search.best_score_
        self.results = grid_search.cv_results_
        
        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'results': self.results
        }
    
    def random_search(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """随机搜索"""
        from sklearn.model_selection import RandomizedSearchCV
        
        # 创建包装器（同上）
        class ModelWrapper:
            def __init__(self, model_fn):
                self.model_fn = model_fn
                self.model = None
            
            def fit(self, X, y):
                self.model = self.model_fn(**self.model_params)
                if hasattr(self.model, 'fit'):
                    self.model.fit(X, y)
                return self
            
            def predict(self, X):
                if hasattr(self.model, 'predict'):
                    return self.model.predict(X)
                return None
            
            def score(self, X, y):
                if hasattr(self.model, 'score'):
                    return self.model.score(X, y)
                return 0
        
        # 创建参数分布
        param_dist = {}
        for key, values in self.param_grid.items():
            param_dist[f'model_params__{key}'] = values
        
        # 执行随机搜索
        random_search = RandomizedSearchCV(
            ModelWrapper(self.model_fn),
            param_dist,
            n_iter=self.n_trials,
            cv=self.cv,
            scoring=self.scoring,
            random_state=self.random_state,
            n_jobs=-1
        )
        
        random_search.fit(X, y)
        
        self.best_params = random_search.best_params_
        self.best_score = random_search.best_score_
        self.results = random_search.cv_results_
        
        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'results': self.results
        }


def save_training_config(config: Dict[str, Any], save_path: str) -> None:
    """保存训练配置"""
    config['saved_at'] = datetime.now().isoformat()
    with open(save_path, 'w') as f:
        json.dump(config, f, indent=2)


def load_training_config(config_path: str) -> Dict[str, Any]:
    """加载训练配置"""
    with open(config_path, 'r') as f:
        return json.load(f)