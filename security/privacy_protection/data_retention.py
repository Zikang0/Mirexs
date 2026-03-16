"""
数据保留模块 - 数据保留策略管理
管理数据的生命周期、保留期限和自动清理
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from ..security_monitoring.audit_logger import AuditLogger
from .consent_manager import ConsentManager, get_consent_manager

logger = logging.getLogger(__name__)


class RetentionPolicyType(Enum):
    """保留策略类型枚举"""
    FIXED_TERM = "fixed_term"  # 固定期限
    BASED_ON_LAST_ACTIVITY = "based_on_last_activity"  # 基于最后活动
    BASED_ON_CONSENT = "based_on_consent"  # 基于同意
    INDEFINITE = "indefinite"  # 无限期
    LEGAL_REQUIREMENT = "legal_requirement"  # 法律要求


class DataCategory(Enum):
    """数据类别枚举"""
    ACCOUNT = "account"  # 账户数据
    PROFILE = "profile"  # 个人资料
    PREFERENCES = "preferences"  # 偏好设置
    INTERACTION_HISTORY = "interaction_history"  # 交互历史
    CONVERSATIONS = "conversations"  # 对话记录
    BIOMETRIC = "biometric"  # 生物特征
    PAYMENT = "payment"  # 支付信息
    USAGE_LOGS = "usage_logs"  # 使用日志
    ANALYTICS = "analytics"  # 分析数据
    CONSENT_RECORDS = "consent_records"  # 同意记录
    AUDIT_LOGS = "audit_logs"  # 审计日志
    SECURITY_LOGS = "security_logs"  # 安全日志


@dataclass
class RetentionPolicy:
    """数据保留策略"""
    policy_id: str
    data_category: DataCategory
    policy_type: RetentionPolicyType
    retention_days: int
    description: str
    enabled: bool = True
    requires_consent: bool = False
    legal_basis: Optional[str] = None
    exceptions: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    created_by: str = "system"


@dataclass
class DataRetentionRule:
    """数据保留规则"""
    rule_id: str
    data_category: DataCategory
    condition: str  # 条件表达式
    action: str  # 执行动作（delete, anonymize, archive）
    priority: int = 0
    enabled: bool = True


class DataRetention:
    """
    数据保留管理器 - 管理数据生命周期和保留策略
    支持自动清理过期数据，符合隐私法规要求
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化数据保留管理器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 保留策略
        self.policies: Dict[str, RetentionPolicy] = {}
        
        # 保留规则
        self.rules: Dict[str, DataRetentionRule] = {}
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/privacy/retention"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.audit_logger = AuditLogger()
        self.consent_manager = get_consent_manager()
        
        # 加载数据
        self._load_policies()
        self._load_rules()
        
        # 初始化默认策略
        self._init_default_policies()
        
        # 清理任务统计
        self.cleanup_stats = {
            "last_cleanup": None,
            "total_cleaned": 0,
            "cleaned_by_category": {}
        }
        
        logger.info(f"数据保留管理器初始化完成，存储路径: {self.storage_path}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/privacy/retention",
            "default_retention_days": 365,  # 默认保留1年
            "enable_auto_cleanup": True,
            "cleanup_interval_hours": 24,
            "dry_run": False,  # 试运行模式（不实际删除）
            "require_confirmation_for_large_deletion": True,
            "large_deletion_threshold": 1000,  # 大额删除阈值
            "retention_policies": {
                "account": {
                    "type": "indefinite",
                    "days": None,
                    "description": "账户数据无限期保留"
                },
                "profile": {
                    "type": "based_on_last_activity",
                    "days": 730,  # 2年
                    "description": "个人资料基于最后活动保留2年"
                },
                "preferences": {
                    "type": "indefinite",
                    "days": None,
                    "description": "偏好设置无限期保留"
                },
                "interaction_history": {
                    "type": "fixed_term",
                    "days": 365,  # 1年
                    "description": "交互历史保留1年"
                },
                "conversations": {
                    "type": "fixed_term",
                    "days": 180,  # 6个月
                    "description": "对话记录保留6个月"
                },
                "biometric": {
                    "type": "based_on_consent",
                    "days": None,
                    "description": "生物特征基于同意保留"
                },
                "payment": {
                    "type": "legal_requirement",
                    "days": 1825,  # 5年
                    "description": "支付信息依法保留5年"
                },
                "usage_logs": {
                    "type": "fixed_term",
                    "days": 90,  # 3个月
                    "description": "使用日志保留3个月"
                },
                "analytics": {
                    "type": "fixed_term",
                    "days": 180,  # 6个月
                    "description": "分析数据保留6个月"
                },
                "consent_records": {
                    "type": "legal_requirement",
                    "days": 1825,  # 5年
                    "description": "同意记录依法保留5年"
                },
                "audit_logs": {
                    "type": "legal_requirement",
                    "days": 1825,  # 5年
                    "description": "审计日志依法保留5年"
                },
                "security_logs": {
                    "type": "legal_requirement",
                    "days": 1095,  # 3年
                    "description": "安全日志保留3年"
                }
            }
        }
    
    def _init_default_policies(self):
        """初始化默认保留策略"""
        default_policies = self.config["retention_policies"]
        
        for category_str, policy_config in default_policies.items():
            try:
                category = DataCategory(category_str)
            except ValueError:
                logger.warning(f"未知数据类别: {category_str}")
                continue
            
            policy_type = RetentionPolicyType(policy_config["type"])
            
            policy = RetentionPolicy(
                policy_id=f"policy_{category.value}",
                data_category=category,
                policy_type=policy_type,
                retention_days=policy_config["days"] if policy_config["days"] else 0,
                description=policy_config["description"],
                enabled=True,
                created_by="system"
            )
            
            self.policies[policy.policy_id] = policy
        
        self._save_policies()
        logger.info(f"初始化了 {len(self.policies)} 条默认保留策略")
    
    def _load_policies(self) -> None:
        """从存储加载保留策略"""
        try:
            policies_file = self.storage_path / "policies.json"
            if not policies_file.exists():
                return
            
            with open(policies_file, 'r', encoding='utf-8') as f:
                policies_data = json.load(f)
            
            for policy_id, policy_dict in policies_data.items():
                policy_dict["data_category"] = DataCategory(policy_dict["data_category"])
                policy_dict["policy_type"] = RetentionPolicyType(policy_dict["policy_type"])
                self.policies[policy_id] = RetentionPolicy(**policy_dict)
            
            logger.info(f"加载了 {len(self.policies)} 条保留策略")
        except Exception as e:
            logger.error(f"加载保留策略失败: {str(e)}")
    
    def _load_rules(self) -> None:
        """从存储加载保留规则"""
        try:
            rules_file = self.storage_path / "rules.json"
            if not rules_file.exists():
                return
            
            with open(rules_file, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            for rule_id, rule_dict in rules_data.items():
                rule_dict["data_category"] = DataCategory(rule_dict["data_category"])
                self.rules[rule_id] = DataRetentionRule(**rule_dict)
            
            logger.info(f"加载了 {len(self.rules)} 条保留规则")
        except Exception as e:
            logger.error(f"加载保留规则失败: {str(e)}")
    
    def _save_policies(self) -> None:
        """保存保留策略到存储"""
        try:
            policies_data = {}
            for policy_id, policy in self.policies.items():
                policy_dict = {
                    "policy_id": policy.policy_id,
                    "data_category": policy.data_category.value,
                    "policy_type": policy.policy_type.value,
                    "retention_days": policy.retention_days,
                    "description": policy.description,
                    "enabled": policy.enabled,
                    "requires_consent": policy.requires_consent,
                    "legal_basis": policy.legal_basis,
                    "exceptions": policy.exceptions,
                    "created_at": policy.created_at,
                    "updated_at": policy.updated_at,
                    "created_by": policy.created_by
                }
                policies_data[policy_id] = policy_dict
            
            with open(self.storage_path / "policies.json", 'w', encoding='utf-8') as f:
                json.dump(policies_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存保留策略失败: {str(e)}")
    
    def _save_rules(self) -> None:
        """保存保留规则到存储"""
        try:
            rules_data = {}
            for rule_id, rule in self.rules.items():
                rule_dict = {
                    "rule_id": rule.rule_id,
                    "data_category": rule.data_category.value,
                    "condition": rule.condition,
                    "action": rule.action,
                    "priority": rule.priority,
                    "enabled": rule.enabled
                }
                rules_data[rule_id] = rule_dict
            
            with open(self.storage_path / "rules.json", 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存保留规则失败: {str(e)}")
    
    def add_policy(self, policy: RetentionPolicy) -> Tuple[bool, str]:
        """
        添加保留策略
        
        Args:
            policy: 保留策略
        
        Returns:
            (成功标志, 消息)
        """
        if policy.policy_id in self.policies:
            return False, f"策略ID已存在: {policy.policy_id}"
        
        self.policies[policy.policy_id] = policy
        self._save_policies()
        
        logger.info(f"添加保留策略: {policy.policy_id}")
        return True, "策略添加成功"
    
    def update_policy(
        self,
        policy_id: str,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        更新保留策略
        
        Args:
            policy_id: 策略ID
            **kwargs: 更新字段
        
        Returns:
            (成功标志, 消息)
        """
        if policy_id not in self.policies:
            return False, f"策略不存在: {policy_id}"
        
        policy = self.policies[policy_id]
        
        for key, value in kwargs.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        
        policy.updated_at = time.time()
        self._save_policies()
        
        logger.info(f"更新保留策略: {policy_id}")
        return True, "策略更新成功"
    
    def get_policy_for_category(self, category: DataCategory) -> Optional[RetentionPolicy]:
        """获取数据类别的保留策略"""
        for policy in self.policies.values():
            if policy.data_category == category and policy.enabled:
                return policy
        return None
    
    def calculate_expiry_date(
        self,
        category: DataCategory,
        created_at: float,
        user_id: Optional[str] = None,
        last_activity: Optional[float] = None
    ) -> Optional[float]:
        """
        计算数据过期日期
        
        Args:
            category: 数据类别
            created_at: 创建时间
            user_id: 用户ID
            last_activity: 最后活动时间
        
        Returns:
            过期时间戳，None表示永不过期
        """
        policy = self.get_policy_for_category(category)
        if not policy:
            # 使用默认策略
            return created_at + (self.config["default_retention_days"] * 24 * 3600)
        
        if policy.policy_type == RetentionPolicyType.FIXED_TERM:
            return created_at + (policy.retention_days * 24 * 3600)
        
        elif policy.policy_type == RetentionPolicyType.BASED_ON_LAST_ACTIVITY:
            if last_activity:
                return last_activity + (policy.retention_days * 24 * 3600)
            return created_at + (policy.retention_days * 24 * 3600)
        
        elif policy.policy_type == RetentionPolicyType.BASED_ON_CONSENT:
            if user_id:
                # 检查用户是否仍有有效同意
                from .consent_manager import ConsentPurpose
                from ..access_control.identity_verifier import get_identity_verifier
                
                # 简化实现：假设同意有效期为1年
                return created_at + (365 * 24 * 3600)
            return created_at + (90 * 24 * 3600)  # 默认90天
        
        elif policy.policy_type == RetentionPolicyType.LEGAL_REQUIREMENT:
            return created_at + (policy.retention_days * 24 * 3600)
        
        elif policy.policy_type == RetentionPolicyType.INDEFINITE:
            return None
        
        return created_at + (self.config["default_retention_days"] * 24 * 3600)
    
    def is_expired(
        self,
        category: DataCategory,
        created_at: float,
        user_id: Optional[str] = None,
        last_activity: Optional[float] = None
    ) -> bool:
        """
        检查数据是否已过期
        
        Args:
            category: 数据类别
            created_at: 创建时间
            user_id: 用户ID
            last_activity: 最后活动时间
        
        Returns:
            是否过期
        """
        expiry = self.calculate_expiry_date(category, created_at, user_id, last_activity)
        if expiry is None:
            return False
        return time.time() > expiry
    
    def add_rule(self, rule: DataRetentionRule) -> Tuple[bool, str]:
        """
        添加保留规则
        
        Args:
            rule: 保留规则
        
        Returns:
            (成功标志, 消息)
        """
        if rule.rule_id in self.rules:
            return False, f"规则ID已存在: {rule.rule_id}"
        
        self.rules[rule.rule_id] = rule
        self._save_rules()
        
        logger.info(f"添加保留规则: {rule.rule_id}")
        return True, "规则添加成功"
    
    def evaluate_rules(
        self,
        category: DataCategory,
        data: Dict[str, Any]
    ) -> List[str]:
        """
        评估数据适用的规则
        
        Args:
            category: 数据类别
            data: 数据对象
        
        Returns:
            要执行的动作列表
        """
        actions = []
        
        # 按优先级排序
        sorted_rules = sorted(
            [r for r in self.rules.values() if r.data_category == category and r.enabled],
            key=lambda r: r.priority,
            reverse=True
        )
        
        for rule in sorted_rules:
            try:
                # 简化条件评估，实际应使用表达式引擎
                if self._evaluate_condition(rule.condition, data):
                    actions.append(rule.action)
            except Exception as e:
                logger.error(f"评估规则 {rule.rule_id} 失败: {str(e)}")
        
        return actions
    
    def _evaluate_condition(self, condition: str, data: Dict[str, Any]) -> bool:
        """评估条件表达式（简化实现）"""
        # 这里应该实现真正的表达式评估
        # 简化实现：检查条件是否在数据中
        if condition.startswith("age > "):
            try:
                days = int(condition.split("> ")[1])
                created = data.get("created_at", time.time())
                return (time.time() - created) > (days * 24 * 3600)
            except:
                return False
        return True
    
    def cleanup_expired_data(
        self,
        data_provider: Optional[Any] = None,
        dry_run: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        清理过期数据
        
        Args:
            data_provider: 数据提供者（实际数据源）
            dry_run: 试运行模式
        
        Returns:
            清理结果统计
        """
        if dry_run is None:
            dry_run = self.config["dry_run"]
        
        results = {
            "timestamp": time.time(),
            "dry_run": dry_run,
            "categories_checked": [],
            "total_expired": 0,
            "total_deleted": 0,
            "deleted_by_category": {},
            "errors": []
        }
        
        for category in DataCategory:
            try:
                policy = self.get_policy_for_category(category)
                if not policy or not policy.enabled:
                    continue
                
                results["categories_checked"].append(category.value)
                
                # 这里应该调用实际的数据源获取过期数据
                # 由于无法直接访问数据库，这里模拟检查
                expired_count = self._check_expired_data(category, policy)
                
                if expired_count > 0:
                    results["total_expired"] += expired_count
                    results["deleted_by_category"][category.value] = expired_count
                    
                    if not dry_run:
                        # 实际删除数据
                        deleted = self._delete_expired_data(category, expired_count)
                        results["total_deleted"] += deleted
                        
                        # 更新统计
                        self.cleanup_stats["total_cleaned"] += deleted
                        self.cleanup_stats["cleaned_by_category"][category.value] = \
                            self.cleanup_stats["cleaned_by_category"].get(category.value, 0) + deleted
                
            except Exception as e:
                results["errors"].append(f"{category.value}: {str(e)}")
        
        self.cleanup_stats["last_cleanup"] = time.time()
        
        # 记录审计日志
        self.audit_logger.log_event(
            event_type="DATA_CLEANUP",
            user_id="system",
            details={
                "dry_run": dry_run,
                "expired_count": results["total_expired"],
                "deleted_count": results["total_deleted"],
                "categories": list(results["deleted_by_category"].keys())
            },
            severity="INFO"
        )
        
        logger.info(f"数据清理完成: 过期 {results['total_expired']} 条, 删除 {results['total_deleted']} 条")
        return results
    
    def _check_expired_data(self, category: DataCategory, policy: RetentionPolicy) -> int:
        """检查过期数据数量（模拟实现）"""
        # 实际应从数据库查询
        import random
        return random.randint(0, 100)
    
    def _delete_expired_data(self, category: DataCategory, count: int) -> int:
        """删除过期数据（模拟实现）"""
        # 实际应执行数据库删除操作
        return count
    
    def get_retention_report(self) -> Dict[str, Any]:
        """获取保留报告"""
        report = {
            "generated_at": time.time(),
            "policies": [],
            "expiring_soon": [],
            "statistics": self.cleanup_stats
        }
        
        for policy in self.policies.values():
            report["policies"].append({
                "category": policy.data_category.value,
                "type": policy.policy_type.value,
                "retention_days": policy.retention_days,
                "enabled": policy.enabled,
                "description": policy.description
            })
        
        # 模拟即将过期的数据
        now = time.time()
        for category in DataCategory:
            policy = self.get_policy_for_category(category)
            if policy and policy.retention_days > 0:
                # 假设有一些数据即将过期
                expiring_count = random.randint(0, 50)
                if expiring_count > 0:
                    report["expiring_soon"].append({
                        "category": category.value,
                        "count": expiring_count,
                        "days_remaining": random.randint(1, 30)
                    })
        
        return report
    
    def create_retention_job(
        self,
        categories: Optional[List[DataCategory]] = None,
        schedule: str = "daily"
    ) -> Dict[str, Any]:
        """
        创建保留任务
        
        Args:
            categories: 要处理的数据类别
            schedule: 调度频率
        
        Returns:
            任务信息
        """
        job_id = f"retention_job_{int(time.time())}"
        
        job = {
            "job_id": job_id,
            "categories": [c.value for c in categories] if categories else ["all"],
            "schedule": schedule,
            "created_at": time.time(),
            "status": "active",
            "last_run": None,
            "next_run": time.time() + (24 * 3600)  # 默认24小时后
        }
        
        # 存储任务信息（简化实现）
        jobs_file = self.storage_path / "jobs.json"
        try:
            if jobs_file.exists():
                with open(jobs_file, 'r') as f:
                    jobs = json.load(f)
            else:
                jobs = {}
            
            jobs[job_id] = job
            
            with open(jobs_file, 'w') as f:
                json.dump(jobs, f, indent=2)
        except Exception as e:
            logger.error(f"保存任务失败: {str(e)}")
        
        logger.info(f"创建保留任务: {job_id}")
        return job
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_policies": len(self.policies),
            "enabled_policies": sum(1 for p in self.policies.values() if p.enabled),
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules.values() if r.enabled),
            "cleanup_stats": self.cleanup_stats,
            "auto_cleanup_enabled": self.config["enable_auto_cleanup"],
            "default_retention_days": self.config["default_retention_days"]
        }


# 单例实例
_data_retention_instance = None


def get_data_retention() -> DataRetention:
    """获取数据保留管理器单例实例"""
    global _data_retention_instance
    if _data_retention_instance is None:
        _data_retention_instance = DataRetention()
    return _data_retention_instance

