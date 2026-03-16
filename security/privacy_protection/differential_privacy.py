"""
差分隐私模块 - 提供差分隐私保护
实现ε-差分隐私算法，用于统计数据发布时的隐私保护
"""

import logging
import math
import random
import time
import numpy as np
from typing import Dict, Any, Optional, List, Union, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field

from ..security_monitoring.audit_logger import AuditLogger
from ...utils.data_processing.data_analysis import DataAnalyzer

logger = logging.getLogger(__name__)


class PrivacyMechanism(Enum):
    """隐私机制枚举"""
    LAPLACE = "laplace"  # 拉普拉斯机制
    GAUSSIAN = "gaussian"  # 高斯机制
    EXPONENTIAL = "exponential"  # 指数机制
    RANDOM_RESPONSE = "random_response"  # 随机响应


class SensitivityType(Enum):
    """敏感度类型枚举"""
    L1_SENSITIVITY = "l1"  # L1敏感度
    L2_SENSITIVITY = "l2"  # L2敏感度
    LOCAL_SENSITIVITY = "local"  # 局部敏感度
    SMOOTH_SENSITIVITY = "smooth"  # 平滑敏感度


@dataclass
class PrivacyBudget:
    """隐私预算"""
    epsilon: float  # 隐私参数ε
    delta: Optional[float] = None  # 松弛参数δ（用于(ε,δ)-差分隐私）
    remaining_epsilon: float = None  # 剩余ε
    total_queries: int = 0
    composition_method: str = "sequential"  # sequential, parallel, advanced
    
    def __post_init__(self):
        if self.remaining_epsilon is None:
            self.remaining_epsilon = self.epsilon


@dataclass
class DPResult:
    """差分隐私结果"""
    value: Any
    mechanism: PrivacyMechanism
    epsilon_used: float
    delta_used: Optional[float] = None
    sensitivity: float = None
    noise_scale: float = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DifferentialPrivacy:
    """
    差分隐私保护器
    实现ε-差分隐私和(ε,δ)-差分隐私机制
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化差分隐私保护器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 初始化依赖
        self.audit_logger = AuditLogger()
        self.data_analyzer = DataAnalyzer()
        
        # 隐私预算跟踪
        self.privacy_budgets: Dict[str, PrivacyBudget] = {}
        
        # 查询历史
        self.query_history: List[Dict[str, Any]] = []
        
        # 默认隐私预算
        self.default_epsilon = self.config.get("default_epsilon", 1.0)
        self.default_delta = self.config.get("default_delta", 1e-5)
        
        logger.info(f"差分隐私保护器初始化完成，默认ε={self.default_epsilon}, δ={self.default_delta}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "default_epsilon": 1.0,
            "default_delta": 1e-5,
            "max_composition_queries": 1000,
            "enable_budget_tracking": True,
            "sensitivity_calculation_method": "global",
            "random_seed": None,
            "clip_threshold": 10.0  # 数值裁剪阈值
        }
    
    def create_privacy_budget(
        self,
        budget_id: str,
        epsilon: float,
        delta: Optional[float] = None,
        composition_method: str = "sequential"
    ) -> PrivacyBudget:
        """
        创建隐私预算
        
        Args:
            budget_id: 预算ID
            epsilon: 隐私参数ε
            delta: 松弛参数δ
            composition_method: 组合方法
        
        Returns:
            隐私预算对象
        """
        budget = PrivacyBudget(
            epsilon=epsilon,
            delta=delta,
            remaining_epsilon=epsilon,
            composition_method=composition_method
        )
        
        self.privacy_budgets[budget_id] = budget
        
        logger.info(f"创建隐私预算 {budget_id}: ε={epsilon}, δ={delta}")
        return budget
    
    def laplace_mechanism(
        self,
        value: float,
        sensitivity: float,
        epsilon: float,
        budget_id: Optional[str] = None
    ) -> DPResult:
        """
        拉普拉斯机制
        
        Args:
            value: 原始数值
            sensitivity: 敏感度
            epsilon: 隐私预算
            budget_id: 预算ID
        
        Returns:
            加噪后的结果
        """
        # 检查预算
        if budget_id:
            self._check_and_consume_budget(budget_id, epsilon)
        
        # 计算噪声尺度
        scale = sensitivity / epsilon
        
        # 生成拉普拉斯噪声
        noise = np.random.laplace(0, scale)
        
        # 添加噪声
        noisy_value = value + noise
        
        # 裁剪（如果需要）
        clip_threshold = self.config["clip_threshold"]
        if abs(noisy_value) > clip_threshold:
            noisy_value = clip_threshold if noisy_value > 0 else -clip_threshold
        
        result = DPResult(
            value=noisy_value,
            mechanism=PrivacyMechanism.LAPLACE,
            epsilon_used=epsilon,
            sensitivity=sensitivity,
            noise_scale=scale,
            metadata={
                "original_value": value,
                "noise": float(noise),
                "clip_threshold": clip_threshold if abs(noisy_value) == clip_threshold else None
            }
        )
        
        self._record_query("laplace", epsilon, sensitivity, value, noisy_value)
        
        return result
    
    def gaussian_mechanism(
        self,
        value: float,
        sensitivity: float,
        epsilon: float,
        delta: Optional[float] = None,
        budget_id: Optional[str] = None
    ) -> DPResult:
        """
        高斯机制（(ε,δ)-差分隐私）
        
        Args:
            value: 原始数值
            sensitivity: L2敏感度
            epsilon: 隐私参数ε
            delta: 松弛参数δ
            budget_id: 预算ID
        
        Returns:
            加噪后的结果
        """
        if delta is None:
            delta = self.default_delta
        
        # 检查预算
        if budget_id:
            self._check_and_consume_budget(budget_id, epsilon, delta)
        
        # 计算噪声尺度
        # σ = √(2 ln(1.25/δ)) * Δ / ε
        scale = math.sqrt(2 * math.log(1.25 / delta)) * sensitivity / epsilon
        
        # 生成高斯噪声
        noise = np.random.normal(0, scale)
        
        # 添加噪声
        noisy_value = value + noise
        
        result = DPResult(
            value=noisy_value,
            mechanism=PrivacyMechanism.GAUSSIAN,
            epsilon_used=epsilon,
            delta_used=delta,
            sensitivity=sensitivity,
            noise_scale=scale,
            metadata={
                "original_value": value,
                "noise": float(noise)
            }
        )
        
        self._record_query("gaussian", epsilon, sensitivity, value, noisy_value, delta)
        
        return result
    
    def exponential_mechanism(
        self,
        options: List[Any],
        utility_function: Callable[[Any], float],
        epsilon: float,
        sensitivity: float = 1.0,
        budget_id: Optional[str] = None
    ) -> DPResult:
        """
        指数机制（用于非数值型查询）
        
        Args:
            options: 可选值列表
            utility_function: 效用函数
            epsilon: 隐私预算
            sensitivity: 敏感度
            budget_id: 预算ID
        
        Returns:
            选择的选项
        """
        # 检查预算
        if budget_id:
            self._check_and_consume_budget(budget_id, epsilon)
        
        # 计算每个选项的效用分数
        scores = [utility_function(opt) for opt in options]
        
        # 计算指数机制的概率
        # P(选择i) ∝ exp(ε * u_i / (2 * Δu))
        scaled_scores = [epsilon * score / (2 * sensitivity) for score in scores]
        
        # 防止数值溢出
        max_score = max(scaled_scores)
        exp_scores = [math.exp(score - max_score) for score in scaled_scores]
        
        # 归一化概率
        total = sum(exp_scores)
        probabilities = [exp / total for exp in exp_scores]
        
        # 根据概率选择
        selected_idx = np.random.choice(len(options), p=probabilities)
        selected = options[selected_idx]
        
        result = DPResult(
            value=selected,
            mechanism=PrivacyMechanism.EXPONENTIAL,
            epsilon_used=epsilon,
            sensitivity=sensitivity,
            metadata={
                "options_count": len(options),
                "selected_index": selected_idx,
                "probabilities": probabilities,
                "original_scores": scores
            }
        )
        
        self._record_query("exponential", epsilon, sensitivity, None, selected)
        
        return result
    
    def random_response(
        self,
        value: bool,
        epsilon: float,
        p: Optional[float] = None,
        budget_id: Optional[str] = None
    ) -> DPResult:
        """
        随机响应机制（用于布尔值）
        
        Args:
            value: 原始布尔值
            epsilon: 隐私预算
            p: 保持真实的概率
            budget_id: 预算ID
        
        Returns:
            扰动后的布尔值
        """
        # 检查预算
        if budget_id:
            self._check_and_consume_budget(budget_id, epsilon)
        
        # 计算概率
        if p is None:
            # 对于ε-差分隐私的随机响应: p = e^ε / (1 + e^ε)
            p = math.exp(epsilon) / (1 + math.exp(epsilon))
        
        # 应用随机响应
        if random.random() < p:
            response = value
        else:
            response = not value
        
        result = DPResult(
            value=response,
            mechanism=PrivacyMechanism.RANDOM_RESPONSE,
            epsilon_used=epsilon,
            metadata={
                "original_value": value,
                "truth_probability": p
            }
        )
        
        self._record_query("random_response", epsilon, 1.0, value, response)
        
        return result
    
    def calculate_sensitivity(
        self,
        dataset: List[Any],
        query_function: Callable[[List[Any]], float],
        sensitivity_type: SensitivityType = SensitivityType.L1_SENSITIVITY,
        samples: int = 1000
    ) -> float:
        """
        计算查询函数的敏感度
        
        Args:
            dataset: 数据集
            query_function: 查询函数
            sensitivity_type: 敏感度类型
            samples: 采样次数
        
        Returns:
            敏感度估计值
        """
        if sensitivity_type == SensitivityType.L1_SENSITIVITY:
            return self._calculate_l1_sensitivity(dataset, query_function)
        elif sensitivity_type == SensitivityType.L2_SENSITIVITY:
            return self._calculate_l2_sensitivity(dataset, query_function)
        elif sensitivity_type == SensitivityType.LOCAL_SENSITIVITY:
            return self._calculate_local_sensitivity(dataset, query_function)
        elif sensitivity_type == SensitivityType.SMOOTH_SENSITIVITY:
            return self._calculate_smooth_sensitivity(dataset, query_function, samples)
        else:
            raise ValueError(f"不支持的敏感度类型: {sensitivity_type}")
    
    def _calculate_l1_sensitivity(
        self,
        dataset: List[Any],
        query_function: Callable[[List[Any]], float]
    ) -> float:
        """计算L1敏感度"""
        # 对于相邻数据集（相差一条记录），最大L1范数差异
        max_diff = 0.0
        
        # 原始查询结果
        original_result = query_function(dataset)
        
        # 遍历移除每条记录
        for i in range(len(dataset)):
            neighboring_dataset = dataset[:i] + dataset[i+1:]
            neighbor_result = query_function(neighboring_dataset)
            
            diff = abs(original_result - neighbor_result)
            max_diff = max(max_diff, diff)
        
        return max_diff
    
    def _calculate_l2_sensitivity(self, dataset: List[Any], query_function: Callable) -> float:
        """计算L2敏感度"""
        # 对于向量值查询，计算L2范数的最大差异
        max_diff_sq = 0.0
        
        original_result = query_function(dataset)
        
        for i in range(len(dataset)):
            neighboring_dataset = dataset[:i] + dataset[i+1:]
            neighbor_result = query_function(neighboring_dataset)
            
            # 计算L2范数平方
            diff_sq = sum((a - b) ** 2 for a, b in zip(original_result, neighbor_result))
            max_diff_sq = max(max_diff_sq, diff_sq)
        
        return math.sqrt(max_diff_sq)
    
    def _calculate_local_sensitivity(
        self,
        dataset: List[Any],
        query_function: Callable[[List[Any]], float]
    ) -> float:
        """计算局部敏感度"""
        # 对于特定数据集的最大变化
        return self._calculate_l1_sensitivity(dataset, query_function)
    
    def _calculate_smooth_sensitivity(
        self,
        dataset: List[Any],
        query_function: Callable[[List[Any]], float],
        samples: int
    ) -> float:
        """计算平滑敏感度（通过采样）"""
        local_sensitivities = []
        
        # 生成相邻数据集的样本
        for _ in range(samples):
            # 随机移除一条记录
            if len(dataset) > 1:
                idx = random.randrange(len(dataset))
                neighbor = dataset[:idx] + dataset[idx+1:]
                local_sens = self._calculate_local_sensitivity(neighbor, query_function)
                local_sensitivities.append(local_sens)
        
        if not local_sensitivities:
            return self._calculate_local_sensitivity(dataset, query_function)
        
        # 平滑处理（取指数加权）
        beta = 0.1  # 平滑参数
        smooth = max(ls * math.exp(-beta * k) 
                    for k, ls in enumerate(sorted(local_sensitivities, reverse=True)))
        
        return smooth
    
    def compose_budgets(
        self,
        budgets: List[PrivacyBudget],
        composition_method: str = "sequential"
    ) -> PrivacyBudget:
        """
        组合多个隐私预算
        
        Args:
            budgets: 预算列表
            composition_method: 组合方法
        
        Returns:
            组合后的预算
        """
        total_epsilon = 0.0
        total_delta = 0.0
        
        if composition_method == "sequential":
            # 顺序组合：ε相加
            for budget in budgets:
                total_epsilon += budget.epsilon
                if budget.delta:
                    total_delta += budget.delta
        
        elif composition_method == "parallel":
            # 并行组合：取最大ε
            total_epsilon = max(b.epsilon for b in budgets)
            total_delta = max((b.delta for b in budgets if b.delta), default=0.0)
        
        elif composition_method == "advanced":
            # 高级组合（用于(ε,δ)-差分隐私）
            # 使用高级组合定理
            epsilon_sum = sum(b.epsilon for b in budgets)
            delta_sum = sum(b.delta for b in budgets if b.delta)
            
            delta_prime = 1e-5  # 目标δ
            epsilon_prime = epsilon_sum + math.sqrt(2 * epsilon_sum * math.log(1/delta_prime))
            
            total_epsilon = epsilon_prime
            total_delta = delta_sum + delta_prime
        
        composed = PrivacyBudget(
            epsilon=total_epsilon,
            delta=total_delta if total_delta > 0 else None,
            composition_method=composition_method
        )
        
        return composed
    
    def _check_and_consume_budget(
        self,
        budget_id: str,
        epsilon: float,
        delta: Optional[float] = None
    ) -> None:
        """
        检查并消耗隐私预算
        
        Args:
            budget_id: 预算ID
            epsilon: 消耗的ε
            delta: 消耗的δ
        """
        if not self.config["enable_budget_tracking"]:
            return
        
        if budget_id not in self.privacy_budgets:
            raise ValueError(f"隐私预算不存在: {budget_id}")
        
        budget = self.privacy_budgets[budget_id]
        
        if budget.remaining_epsilon < epsilon:
            raise ValueError(
                f"隐私预算不足: 剩余 ε={budget.remaining_epsilon}, 需要 ε={epsilon}"
            )
        
        if delta and budget.delta and budget.delta < delta:
            raise ValueError(
                f"隐私预算不足: 剩余 δ={budget.delta}, 需要 δ={delta}"
            )
        
        # 消耗预算
        budget.remaining_epsilon -= epsilon
        budget.total_queries += 1
        
        logger.debug(f"消耗隐私预算 {budget_id}: ε={epsilon}, 剩余 ε={budget.remaining_epsilon}")
    
    def _record_query(
        self,
        mechanism: str,
        epsilon: float,
        sensitivity: float,
        original: Any,
        noisy: Any,
        delta: Optional[float] = None
    ) -> None:
        """记录查询历史"""
        query_record = {
            "timestamp": time.time(),
            "mechanism": mechanism,
            "epsilon": epsilon,
            "delta": delta,
            "sensitivity": sensitivity,
            "original": original,
            "noisy": noisy
        }
        
        self.query_history.append(query_record)
        
        # 限制历史记录大小
        max_history = 10000
        if len(self.query_history) > max_history:
            self.query_history = self.query_history[-max_history:]
    
    def get_remaining_budget(self, budget_id: str) -> Optional[float]:
        """获取剩余隐私预算"""
        if budget_id in self.privacy_budgets:
            return self.privacy_budgets[budget_id].remaining_epsilon
        return None
    
    def get_query_history(
        self,
        limit: int = 100,
        mechanism: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取查询历史"""
        history = self.query_history
        
        if mechanism:
            history = [q for q in history if q["mechanism"] == mechanism]
        
        return history[-limit:]
    
    def reset_budget(self, budget_id: str) -> None:
        """重置隐私预算"""
        if budget_id in self.privacy_budgets:
            budget = self.privacy_budgets[budget_id]
            budget.remaining_epsilon = budget.epsilon
            budget.total_queries = 0
            logger.info(f"重置隐私预算 {budget_id}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "active_budgets": len(self.privacy_budgets),
            "total_queries": len(self.query_history),
            "default_epsilon": self.default_epsilon,
            "default_delta": self.default_delta,
            "mechanisms_used": list(set(q["mechanism"] for q in self.query_history)),
            "total_epsilon_consumed": sum(q["epsilon"] for q in self.query_history)
        }


# 单例实例
_differential_privacy_instance = None


def get_differential_privacy() -> DifferentialPrivacy:
    """获取差分隐私保护器单例实例"""
    global _differential_privacy_instance
    if _differential_privacy_instance is None:
        _differential_privacy_instance = DifferentialPrivacy()
    return _differential_privacy_instance

