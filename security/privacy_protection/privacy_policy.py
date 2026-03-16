"""
隐私策略模块 - 隐私保护策略管理
管理隐私政策的版本、内容和用户确认状态
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..security_monitoring.audit_logger import AuditLogger
from .consent_manager import ConsentManager, get_consent_manager

logger = logging.getLogger(__name__)


class PolicyStatus(Enum):
    """策略状态枚举"""
    DRAFT = "draft"  # 草稿
    ACTIVE = "active"  # 生效中
    DEPRECATED = "deprecated"  # 已废弃
    ARCHIVED = "archived"  # 已归档


class PolicyType(Enum):
    """策略类型枚举"""
    PRIVACY_POLICY = "privacy_policy"  # 隐私政策
    TERMS_OF_SERVICE = "terms_of_service"  # 服务条款
    COOKIE_POLICY = "cookie_policy"  # Cookie政策
    DATA_PROCESSING = "data_processing"  # 数据处理协议
    GDPR_CONSENT = "gdpr_consent"  # GDPR同意书
    CCPA_NOTICE = "ccpa_notice"  # CCPA通知


@dataclass
class PolicyVersion:
    """策略版本"""
    version: str
    content: str
    effective_date: float
    status: PolicyStatus
    created_at: float
    created_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[float] = None
    summary: str = ""
    changes: List[str] = field(default_factory=list)


@dataclass
class UserPolicyAcceptance:
    """用户策略接受记录"""
    user_id: str
    policy_type: PolicyType
    version: str
    accepted_at: float
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PrivacyPolicy:
    """
    隐私策略管理器 - 管理隐私政策和用户同意
    支持多版本控制、用户接受记录、合规检查
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化隐私策略管理器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 策略存储
        self.policies: Dict[str, Dict[str, PolicyVersion]] = {}  # policy_type -> {version -> policy}
        self.active_versions: Dict[str, str] = {}  # policy_type -> active_version
        
        # 用户接受记录
        self.user_acceptances: Dict[str, List[UserPolicyAcceptance]] = {}  # user_id -> list
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/privacy/policies"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.audit_logger = AuditLogger()
        self.consent_manager = get_consent_manager()
        
        # 加载数据
        self._load_policies()
        self._load_acceptances()
        
        # 初始化默认策略
        self._init_default_policies()
        
        logger.info(f"隐私策略管理器初始化完成，存储路径: {self.storage_path}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/privacy/policies",
            "default_policy_version": "1.0.0",
            "require_acceptance_for_new_version": True,
            "acceptance_grace_period_days": 30,  # 新版本接受宽限期
            "enable_audit": True,
            "policy_types": {
                "privacy_policy": {
                    "name": "隐私政策",
                    "required": True,
                    "retention_years": 5
                },
                "terms_of_service": {
                    "name": "服务条款",
                    "required": True,
                    "retention_years": 5
                },
                "cookie_policy": {
                    "name": "Cookie政策",
                    "required": True,
                    "retention_years": 3
                },
                "data_processing": {
                    "name": "数据处理协议",
                    "required": False,
                    "retention_years": 5
                }
            }
        }
    
    def _init_default_policies(self):
        """初始化默认策略"""
        # 如果没有策略，创建默认的隐私政策
        if PolicyType.PRIVACY_POLICY.value not in self.policies or not self.policies[PolicyType.PRIVACY_POLICY.value]:
            default_content = self._get_default_privacy_policy()
            self.create_policy(
                policy_type=PolicyType.PRIVACY_POLICY,
                content=default_content,
                created_by="system",
                summary="默认隐私政策",
                changes=["初始版本"]
            )
        
        # 默认服务条款
        if PolicyType.TERMS_OF_SERVICE.value not in self.policies or not self.policies[PolicyType.TERMS_OF_SERVICE.value]:
            default_content = self._get_default_terms_of_service()
            self.create_policy(
                policy_type=PolicyType.TERMS_OF_SERVICE,
                content=default_content,
                created_by="system",
                summary="默认服务条款",
                changes=["初始版本"]
            )
    
    def _load_policies(self) -> None:
        """从存储加载策略"""
        try:
            policies_file = self.storage_path / "policies.json"
            if not policies_file.exists():
                return
            
            with open(policies_file, 'r', encoding='utf-8') as f:
                policies_data = json.load(f)
            
            for policy_type_str, versions in policies_data.items():
                policy_type = PolicyType(policy_type_str)
                self.policies[policy_type_str] = {}
                
                for version_str, policy_dict in versions.items():
                    policy_dict["status"] = PolicyStatus(policy_dict["status"])
                    policy = PolicyVersion(**policy_dict)
                    self.policies[policy_type_str][version_str] = policy
                    
                    if policy.status == PolicyStatus.ACTIVE:
                        self.active_versions[policy_type_str] = version_str
            
            logger.info(f"加载了 {sum(len(v) for v in self.policies.values())} 个策略版本")
        except Exception as e:
            logger.error(f"加载策略失败: {str(e)}")
    
    def _load_acceptances(self) -> None:
        """从存储加载用户接受记录"""
        try:
            acceptances_file = self.storage_path / "acceptances.json"
            if not acceptances_file.exists():
                return
            
            with open(acceptances_file, 'r', encoding='utf-8') as f:
                acceptances_data = json.load(f)
            
            for user_id, acceptances in acceptances_data.items():
                self.user_acceptances[user_id] = []
                for acc_dict in acceptances:
                    acc_dict["policy_type"] = PolicyType(acc_dict["policy_type"])
                    acceptance = UserPolicyAcceptance(**acc_dict)
                    self.user_acceptances[user_id].append(acceptance)
            
            logger.info(f"加载了 {sum(len(v) for v in self.user_acceptances.values())} 条用户接受记录")
        except Exception as e:
            logger.error(f"加载用户接受记录失败: {str(e)}")
    
    def _save_policies(self) -> None:
        """保存策略到存储"""
        try:
            policies_data = {}
            for policy_type_str, versions in self.policies.items():
                policies_data[policy_type_str] = {}
                for version_str, policy in versions.items():
                    policy_dict = {
                        "version": policy.version,
                        "content": policy.content,
                        "effective_date": policy.effective_date,
                        "status": policy.status.value,
                        "created_at": policy.created_at,
                        "created_by": policy.created_by,
                        "approved_by": policy.approved_by,
                        "approved_at": policy.approved_at,
                        "summary": policy.summary,
                        "changes": policy.changes
                    }
                    policies_data[policy_type_str][version_str] = policy_dict
            
            with open(self.storage_path / "policies.json", 'w', encoding='utf-8') as f:
                json.dump(policies_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"保存了 {sum(len(v) for v in self.policies.values())} 个策略版本")
        except Exception as e:
            logger.error(f"保存策略失败: {str(e)}")
    
    def _save_acceptances(self) -> None:
        """保存用户接受记录到存储"""
        try:
            acceptances_data = {}
            for user_id, acceptances in self.user_acceptances.items():
                acceptances_data[user_id] = []
                for acc in acceptances:
                    acc_dict = {
                        "user_id": acc.user_id,
                        "policy_type": acc.policy_type.value,
                        "version": acc.version,
                        "accepted_at": acc.accepted_at,
                        "ip_address": acc.ip_address,
                        "user_agent": acc.user_agent,
                        "metadata": acc.metadata
                    }
                    acceptances_data[user_id].append(acc_dict)
            
            with open(self.storage_path / "acceptances.json", 'w', encoding='utf-8') as f:
                json.dump(acceptances_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户接受记录失败: {str(e)}")
    
    def create_policy(
        self,
        policy_type: PolicyType,
        content: str,
        created_by: str,
        version: Optional[str] = None,
        summary: str = "",
        changes: Optional[List[str]] = None,
        effective_date: Optional[float] = None
    ) -> Tuple[bool, str, Optional[PolicyVersion]]:
        """
        创建新策略版本
        
        Args:
            policy_type: 策略类型
            content: 策略内容
            created_by: 创建者
            version: 版本号（None则自动生成）
            summary: 摘要
            changes: 变更列表
            effective_date: 生效日期
        
        Returns:
            (成功标志, 消息, 策略版本)
        """
        try:
            # 生成版本号
            if version is None:
                version = self._generate_version(policy_type)
            
            policy_type_str = policy_type.value
            
            # 检查版本是否已存在
            if policy_type_str in self.policies and version in self.policies[policy_type_str]:
                return False, f"版本 {version} 已存在", None
            
            now = time.time()
            effective = effective_date or now
            
            policy = PolicyVersion(
                version=version,
                content=content,
                effective_date=effective,
                status=PolicyStatus.DRAFT,
                created_at=now,
                created_by=created_by,
                summary=summary,
                changes=changes or []
            )
            
            if policy_type_str not in self.policies:
                self.policies[policy_type_str] = {}
            
            self.policies[policy_type_str][version] = policy
            self._save_policies()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="POLICY_CREATE",
                user_id=created_by,
                details={
                    "policy_type": policy_type.value,
                    "version": version,
                    "summary": summary
                },
                severity="INFO"
            )
            
            logger.info(f"创建策略版本: {policy_type.value} v{version}")
            return True, "策略创建成功", policy
            
        except Exception as e:
            logger.error(f"创建策略失败: {str(e)}")
            return False, f"创建失败: {str(e)}", None
    
    def publish_policy(
        self,
        policy_type: PolicyType,
        version: str,
        published_by: str,
        effective_date: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        发布策略版本
        
        Args:
            policy_type: 策略类型
            version: 版本号
            published_by: 发布者
            effective_date: 生效日期
        
        Returns:
            (成功标志, 消息)
        """
        try:
            policy_type_str = policy_type.value
            
            if policy_type_str not in self.policies or version not in self.policies[policy_type_str]:
                return False, f"策略版本不存在: {policy_type.value} v{version}"
            
            policy = self.policies[policy_type_str][version]
            
            if policy.status != PolicyStatus.DRAFT:
                return False, f"策略状态不是草稿: {policy.status.value}"
            
            # 将之前的活跃版本标记为已废弃
            if policy_type_str in self.active_versions:
                old_version = self.active_versions[policy_type_str]
                if old_version in self.policies[policy_type_str]:
                    old_policy = self.policies[policy_type_str][old_version]
                    old_policy.status = PolicyStatus.DEPRECATED
            
            # 发布新版本
            policy.status = PolicyStatus.ACTIVE
            policy.effective_date = effective_date or time.time()
            policy.approved_by = published_by
            policy.approved_at = time.time()
            
            self.active_versions[policy_type_str] = version
            self._save_policies()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="POLICY_PUBLISH",
                user_id=published_by,
                details={
                    "policy_type": policy_type.value,
                    "version": version,
                    "effective_date": policy.effective_date
                },
                severity="INFO"
            )
            
            logger.info(f"发布策略版本: {policy_type.value} v{version}")
            return True, "策略发布成功"
            
        except Exception as e:
            logger.error(f"发布策略失败: {str(e)}")
            return False, f"发布失败: {str(e)}"
    
    def accept_policy(
        self,
        user_id: str,
        policy_type: PolicyType,
        version: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        用户接受策略
        
        Args:
            user_id: 用户ID
            policy_type: 策略类型
            version: 版本号（None表示接受当前活跃版本）
            ip_address: IP地址
            user_agent: 用户代理
            metadata: 元数据
        
        Returns:
            (成功标志, 消息)
        """
        try:
            policy_type_str = policy_type.value
            
            # 确定版本
            if version is None:
                if policy_type_str not in self.active_versions:
                    return False, f"没有活跃的 {policy_type.value} 版本"
                version = self.active_versions[policy_type_str]
            
            # 验证策略存在
            if policy_type_str not in self.policies or version not in self.policies[policy_type_str]:
                return False, f"策略版本不存在: {policy_type.value} v{version}"
            
            policy = self.policies[policy_type_str][version]
            
            # 创建接受记录
            acceptance = UserPolicyAcceptance(
                user_id=user_id,
                policy_type=policy_type,
                version=version,
                accepted_at=time.time(),
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata or {}
            )
            
            if user_id not in self.user_acceptances:
                self.user_acceptances[user_id] = []
            
            self.user_acceptances[user_id].append(acceptance)
            
            # 限制历史记录大小
            if len(self.user_acceptances[user_id]) > 100:
                self.user_acceptances[user_id] = self.user_acceptances[user_id][-100:]
            
            self._save_acceptances()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="POLICY_ACCEPT",
                user_id=user_id,
                details={
                    "policy_type": policy_type.value,
                    "version": version,
                    "ip_address": ip_address
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {user_id} 接受策略: {policy_type.value} v{version}")
            return True, "策略接受成功"
            
        except Exception as e:
            logger.error(f"接受策略失败: {str(e)}")
            return False, f"接受失败: {str(e)}"
    
    def check_acceptance(
        self,
        user_id: str,
        policy_type: PolicyType,
        version: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        检查用户是否已接受策略
        
        Args:
            user_id: 用户ID
            policy_type: 策略类型
            version: 版本号（None表示检查当前活跃版本）
        
        Returns:
            (是否已接受, 已接受的版本, 接受时间)
        """
        if user_id not in self.user_acceptances:
            return False, None, None
        
        policy_type_str = policy_type.value
        
        # 确定要检查的版本
        check_version = version
        if check_version is None:
            if policy_type_str not in self.active_versions:
                return False, None, None
            check_version = self.active_versions[policy_type_str]
        
        # 查找用户是否接受过该版本
        for acceptance in reversed(self.user_acceptances[user_id]):
            if acceptance.policy_type == policy_type and acceptance.version == check_version:
                return True, acceptance.version, acceptance.accepted_at
        
        return False, None, None
    
    def get_pending_acceptances(
        self,
        user_id: str,
        grace_period_days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户待接受的策略
        
        Args:
            user_id: 用户ID
            grace_period_days: 宽限期天数
        
        Returns:
            待接受策略列表
        """
        pending = []
        
        if grace_period_days is None:
            grace_period_days = self.config["acceptance_grace_period_days"]
        
        cutoff_time = time.time() - (grace_period_days * 24 * 3600)
        
        for policy_type_str, active_version in self.active_versions.items():
            policy_type = PolicyType(policy_type_str)
            
            # 检查是否已接受
            accepted, accepted_version, accepted_at = self.check_acceptance(user_id, policy_type)
            
            if not accepted:
                # 未接受过
                policy = self.policies[policy_type_str][active_version]
                
                # 检查是否在宽限期内
                is_grace = policy.effective_date > cutoff_time if policy.effective_date else False
                
                pending.append({
                    "policy_type": policy_type.value,
                    "policy_name": self.config["policy_types"].get(policy_type_str, {}).get("name", policy_type_str),
                    "version": active_version,
                    "effective_date": policy.effective_date,
                    "summary": policy.summary,
                    "changes": policy.changes,
                    "in_grace_period": is_grace,
                    "days_remaining": max(0, (policy.effective_date - time.time()) / (24 * 3600)) if is_grace else 0
                })
            elif accepted_version != active_version:
                # 接受的版本不是最新版本
                policy = self.policies[policy_type_str][active_version]
                old_policy = self.policies[policy_type_str].get(accepted_version)
                
                pending.append({
                    "policy_type": policy_type.value,
                    "policy_name": self.config["policy_types"].get(policy_type_str, {}).get("name", policy_type_str),
                    "version": active_version,
                    "previous_version": accepted_version,
                    "previous_acceptance_date": accepted_at,
                    "effective_date": policy.effective_date,
                    "summary": policy.summary,
                    "changes": policy.changes,
                    "in_grace_period": True,  # 版本更新自动进入宽限期
                    "days_remaining": max(0, (policy.effective_date + grace_period_days * 24 * 3600 - time.time()) / (24 * 3600))
                })
        
        return pending
    
    def get_active_policy(self, policy_type: PolicyType) -> Optional[PolicyVersion]:
        """获取活跃的策略版本"""
        policy_type_str = policy_type.value
        if policy_type_str in self.active_versions:
            version = self.active_versions[policy_type_str]
            return self.policies[policy_type_str].get(version)
        return None
    
    def get_policy(
        self,
        policy_type: PolicyType,
        version: Optional[str] = None
    ) -> Optional[PolicyVersion]:
        """获取指定版本的策略"""
        policy_type_str = policy_type.value
        if policy_type_str not in self.policies:
            return None
        
        if version is None:
            version = self.active_versions.get(policy_type_str)
            if not version:
                return None
        
        return self.policies[policy_type_str].get(version)
    
    def get_policy_history(self, policy_type: PolicyType) -> List[Dict[str, Any]]:
        """获取策略历史"""
        policy_type_str = policy_type.value
        if policy_type_str not in self.policies:
            return []
        
        history = []
        for version, policy in self.policies[policy_type_str].items():
            history.append({
                "version": version,
                "status": policy.status.value,
                "effective_date": policy.effective_date,
                "created_at": policy.created_at,
                "created_by": policy.created_by,
                "summary": policy.summary,
                "changes": policy.changes,
                "is_active": version == self.active_versions.get(policy_type_str)
            })
        
        # 按生效日期排序
        history.sort(key=lambda x: x["effective_date"], reverse=True)
        return history
    
    def get_user_acceptance_history(
        self,
        user_id: str,
        policy_type: Optional[PolicyType] = None
    ) -> List[Dict[str, Any]]:
        """获取用户接受历史"""
        if user_id not in self.user_acceptances:
            return []
        
        history = []
        for acceptance in self.user_acceptances[user_id]:
            if policy_type and acceptance.policy_type != policy_type:
                continue
            
            history.append({
                "policy_type": acceptance.policy_type.value,
                "version": acceptance.version,
                "accepted_at": acceptance.accepted_at,
                "ip_address": acceptance.ip_address,
                "user_agent": acceptance.user_agent
            })
        
        return history
    
    def _generate_version(self, policy_type: PolicyType) -> str:
        """生成新版本号"""
        policy_type_str = policy_type.value
        
        if policy_type_str not in self.policies or not self.policies[policy_type_str]:
            return self.config["default_policy_version"]
        
        # 获取最新版本号并递增
        versions = list(self.policies[policy_type_str].keys())
        versions.sort()
        
        if not versions:
            return self.config["default_policy_version"]
        
        latest = versions[-1]
        parts = latest.split('.')
        
        if len(parts) == 3:
            # 递增补丁版本
            major, minor, patch = parts
            return f"{major}.{minor}.{int(patch) + 1}"
        else:
            return f"{latest}.1"
    
    def _get_default_privacy_policy(self) -> str:
        """获取默认隐私政策内容"""
        return """
# 隐私政策

最后更新日期: 2026年2月28日

## 1. 引言
欢迎使用弥尔思(Mirexs)服务。我们致力于保护您的隐私和个人数据。本隐私政策说明我们如何收集、使用、存储和披露您的个人信息。

## 2. 收集的信息
我们收集以下类型的信息:
- 账户信息: 用户名、邮箱地址
- 使用数据: 交互记录、偏好设置
- 设备信息: 设备型号、操作系统版本
- 生物特征: 经您明确同意后收集的声纹、面部特征

## 3. 使用目的
我们使用您的信息用于:
- 提供和改进服务
- 个性化体验
- 安全保障
- 法律合规

## 4. 数据共享
我们不会出售您的个人信息。仅在以下情况共享:
- 经您明确同意
- 法律要求
- 服务必要（如支付处理）

## 5. 您的权利
您有权:
- 访问您的数据
- 更正不准确的数据
- 删除您的数据
- 撤回同意
- 数据可携

## 6. 数据保留
我们仅在必要期间保留您的数据，通常为账户活跃期间及之后12个月。

## 7. 联系我们
如有疑问，请联系: privacy@mirexs.com
"""
    
    def _get_default_terms_of_service(self) -> str:
        """获取默认服务条款内容"""
        return """
# 服务条款

最后更新日期: 2026年2月28日

## 1. 接受条款
使用弥尔思(Mirexs)服务即表示您同意本条款。

## 2. 服务描述
弥尔思是一个情感化数字生命体伴侣，提供AI驱动的个人助理服务。

## 3. 用户责任
您同意:
- 提供准确信息
- 维护账户安全
- 合法使用服务
- 不滥用或攻击系统

## 4. 知识产权
弥尔思及其相关内容受知识产权法保护。

## 5. 免责声明
服务按"现状"提供，不作任何保证。

## 6. 责任限制
在法律允许的最大范围内，弥尔思不对间接损失承担责任。

## 7. 终止
我们有权终止违反条款的账户。

## 8. 修改
我们可能更新条款，继续使用即表示接受更新。
"""
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_acceptances = sum(len(v) for v in self.user_acceptances.values())
        unique_users = len(self.user_acceptances)
        
        return {
            "total_policies": sum(len(v) for v in self.policies.values()),
            "active_policies": len(self.active_versions),
            "total_acceptances": total_acceptances,
            "unique_users": unique_users,
            "average_acceptances_per_user": total_acceptances / unique_users if unique_users > 0 else 0,
            "policy_types": list(self.config["policy_types"].keys())
        }


# 单例实例
_privacy_policy_instance = None


def get_privacy_policy() -> PrivacyPolicy:
    """获取隐私策略管理器单例实例"""
    global _privacy_policy_instance
    if _privacy_policy_instance is None:
        _privacy_policy_instance = PrivacyPolicy()
    return _privacy_policy_instance

