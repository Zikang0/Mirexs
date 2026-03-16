"""
安全意识模块 - 安全意识和培训
管理安全培训、意识提升和考核
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

from ..access_control.access_logger import AccessLogger, get_access_logger

logger = logging.getLogger(__name__)


class TrainingType(Enum):
    """培训类型枚举"""
    SECURITY_BASICS = "security_basics"  # 安全基础
    PHISHING_AWARENESS = "phishing_awareness"  # 钓鱼意识
    DATA_PROTECTION = "data_protection"  # 数据保护
    INCIDENT_RESPONSE = "incident_response"  # 事件响应
    COMPLIANCE = "compliance"  # 合规
    PASSWORD_SECURITY = "password_security"  # 密码安全
    SOCIAL_ENGINEERING = "social_engineering"  # 社会工程学
    MOBILE_SECURITY = "mobile_security"  # 移动安全
    CLOUD_SECURITY = "cloud_security"  # 云安全


class TrainingStatus(Enum):
    """培训状态枚举"""
    NOT_STARTED = "not_started"  # 未开始
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    EXPIRED = "expired"  # 已过期
    FAILED = "failed"  # 失败


@dataclass
class TrainingModule:
    """培训模块"""
    module_id: str
    name: str
    type: TrainingType
    description: str
    content: str
    duration_minutes: int
    passing_score: int
    required_for_roles: List[str]
    version: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    created_by: str = "system"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserTraining:
    """用户培训记录"""
    record_id: str
    user_id: str
    module_id: str
    status: TrainingStatus
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    score: Optional[int] = None
    attempts: int = 0
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityAwareness:
    """
    安全意识管理器 - 管理安全培训和意识提升
    提供培训课程、考核和进度跟踪
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化安全意识管理器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 培训模块
        self.modules: Dict[str, TrainingModule] = {}
        
        # 用户培训记录
        self.user_trainings: Dict[str, List[UserTraining]] = {}
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/security/awareness"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.access_logger = get_access_logger()
        
        # 加载数据
        self._load_modules()
        self._load_trainings()
        
        # 初始化默认培训模块
        self._init_default_modules()
        
        logger.info(f"安全意识管理器初始化完成，存储路径: {self.storage_path}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/security/awareness",
            "training_expiry_days": 365,  # 培训有效期
            "require_annual_training": True,
            "auto_assign_new_users": True,
            "reminder_days": [30, 7, 1],  # 提醒提前天数
            "phishing_simulation_enabled": True,
            "awareness_campaign_interval": 90,  # 意识宣传间隔
            "minimum_passing_score": 80,
            "certificate_enabled": True
        }
    
    def _init_default_modules(self):
        """初始化默认培训模块"""
        default_modules = [
            {
                "module_id": "sec_basics_101",
                "name": "安全基础培训",
                "type": TrainingType.SECURITY_BASICS,
                "description": "学习基本的安全概念和最佳实践",
                "content": """
# 安全基础培训

## 1. 为什么安全很重要
- 保护个人和公司数据
- 防止安全事件
- 遵守法规要求

## 2. 常见威胁
- 恶意软件
- 钓鱼攻击
- 社会工程学

## 3. 基本防护措施
- 强密码策略
- 双因素认证
- 定期更新
- 备份数据

## 4. 报告流程
发现安全问题应立即报告给安全团队
                """,
                "duration_minutes": 30,
                "passing_score": 80,
                "required_for_roles": ["*"],
                "version": "1.0.0"
            },
            {
                "module_id": "phishing_101",
                "name": "钓鱼攻击识别",
                "type": TrainingType.PHISHING_AWARENESS,
                "description": "学习如何识别和防范钓鱼攻击",
                "content": """
# 钓鱼攻击识别培训

## 1. 什么是钓鱼攻击
- 假冒可信实体
- 诱导点击恶意链接
- 窃取敏感信息

## 2. 钓鱼邮件特征
- 紧急语气
- 拼写错误
- 可疑链接
- 未知发件人

## 3. 如何识别
- 检查发件人地址
- 悬停查看链接
- 不要轻易点击附件

## 4. 报告钓鱼
- 使用报告按钮
- 转发给安全团队
                """,
                "duration_minutes": 20,
                "passing_score": 80,
                "required_for_roles": ["*"],
                "version": "1.0.0"
            },
            {
                "module_id": "data_protection_101",
                "name": "数据保护基础",
                "type": TrainingType.DATA_PROTECTION,
                "description": "学习如何保护敏感数据",
                "content": """
# 数据保护培训

## 1. 数据分类
- 公开数据
- 内部数据
- 敏感数据
- 机密数据

## 2. 数据处理规则
- 最小权限原则
- 加密要求
- 传输安全

## 3. 数据泄露防范
- 不要随意分享
- 使用安全存储
- 注意物理安全

## 4. 数据泄露响应
- 立即报告
- 不要自行处理
- 配合调查
                """,
                "duration_minutes": 25,
                "passing_score": 80,
                "required_for_roles": ["admin", "manager", "developer"],
                "version": "1.0.0"
            }
        ]
        
        for module_config in default_modules:
            if module_config["module_id"] not in self.modules:
                module = TrainingModule(**module_config)
                self.modules[module.module_id] = module
        
        self._save_modules()
        logger.info(f"初始化了 {len(default_modules)} 个默认培训模块")
    
    def _load_modules(self):
        """从存储加载培训模块"""
        try:
            modules_file = self.storage_path / "modules.json"
            if modules_file.exists():
                with open(modules_file, 'r', encoding='utf-8') as f:
                    modules_data = json.load(f)
                    for module_id, module_dict in modules_data.items():
                        module_dict["type"] = TrainingType(module_dict["type"])
                        self.modules[module_id] = TrainingModule(**module_dict)
            
            logger.info(f"加载了 {len(self.modules)} 个培训模块")
        except Exception as e:
            logger.error(f"加载培训模块失败: {str(e)}")
    
    def _load_trainings(self):
        """从存储加载用户培训记录"""
        try:
            trainings_file = self.storage_path / "trainings.json"
            if trainings_file.exists():
                with open(trainings_file, 'r', encoding='utf-8') as f:
                    trainings_data = json.load(f)
                    for user_id, trainings_list in trainings_data.items():
                        self.user_trainings[user_id] = []
                        for t_dict in trainings_list:
                            t_dict["status"] = TrainingStatus(t_dict["status"])
                            self.user_trainings[user_id].append(UserTraining(**t_dict))
            
            logger.info(f"加载了 {sum(len(v) for v in self.user_trainings.values())} 条用户培训记录")
        except Exception as e:
            logger.error(f"加载用户培训记录失败: {str(e)}")
    
    def _save_modules(self):
        """保存培训模块到存储"""
        try:
            modules_data = {}
            for module_id, module in self.modules.items():
                module_dict = {
                    "module_id": module.module_id,
                    "name": module.name,
                    "type": module.type.value,
                    "description": module.description,
                    "content": module.content,
                    "duration_minutes": module.duration_minutes,
                    "passing_score": module.passing_score,
                    "required_for_roles": module.required_for_roles,
                    "version": module.version,
                    "created_at": module.created_at,
                    "updated_at": module.updated_at,
                    "created_by": module.created_by,
                    "metadata": module.metadata
                }
                modules_data[module_id] = module_dict
            
            with open(self.storage_path / "modules.json", 'w', encoding='utf-8') as f:
                json.dump(modules_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存培训模块失败: {str(e)}")
    
    def _save_trainings(self):
        """保存用户培训记录到存储"""
        try:
            trainings_data = {}
            for user_id, trainings in self.user_trainings.items():
                trainings_data[user_id] = []
                for t in trainings:
                    t_dict = {
                        "record_id": t.record_id,
                        "user_id": t.user_id,
                        "module_id": t.module_id,
                        "status": t.status.value,
                        "started_at": t.started_at,
                        "completed_at": t.completed_at,
                        "score": t.score,
                        "attempts": t.attempts,
                        "expires_at": t.expires_at,
                        "metadata": t.metadata
                    }
                    trainings_data[user_id].append(t_dict)
            
            with open(self.storage_path / "trainings.json", 'w', encoding='utf-8') as f:
                json.dump(trainings_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户培训记录失败: {str(e)}")
    
    def assign_training(
        self,
        user_id: str,
        module_id: str,
        assigned_by: str = "system"
    ) -> Tuple[bool, str, Optional[UserTraining]]:
        """
        分配培训给用户
        
        Args:
            user_id: 用户ID
            module_id: 模块ID
            assigned_by: 分配者
        
        Returns:
            (成功标志, 消息, 培训记录)
        """
        if module_id not in self.modules:
            return False, f"培训模块不存在: {module_id}", None
        
        module = self.modules[module_id]
        
        # 检查是否已有进行中的培训
        existing = self.get_user_training(user_id, module_id)
        if existing and existing.status in [TrainingStatus.IN_PROGRESS, TrainingStatus.COMPLETED]:
            if existing.status == TrainingStatus.COMPLETED:
                # 检查是否过期
                if existing.expires_at and existing.expires_at > time.time():
                    return False, "用户已完成此培训且仍在有效期内", None
        
        # 计算过期时间
        expires_at = time.time() + (self.config["training_expiry_days"] * 24 * 3600)
        
        record = UserTraining(
            record_id=f"tr_{int(time.time())}_{user_id[-8:]}_{module_id[:8]}",
            user_id=user_id,
            module_id=module_id,
            status=TrainingStatus.NOT_STARTED,
            expires_at=expires_at,
            metadata={"assigned_by": assigned_by, "assigned_at": time.time()}
        )
        
        if user_id not in self.user_trainings:
            self.user_trainings[user_id] = []
        
        self.user_trainings[user_id].append(record)
        self._save_trainings()
        
        # 记录审计日志
        self.access_logger.log_security_event(
            user_id=assigned_by,
            event_type="TRAINING_ASSIGNED",
            severity="info",
            details={
                "target_user": user_id,
                "module_id": module_id,
                "module_name": module.name
            }
        )
        
        logger.info(f"为用户 {user_id} 分配培训: {module.name}")
        return True, "培训分配成功", record
    
    def start_training(
        self,
        user_id: str,
        module_id: str
    ) -> Tuple[bool, str, Optional[TrainingModule]]:
        """
        开始培训
        
        Args:
            user_id: 用户ID
            module_id: 模块ID
        
        Returns:
            (成功标志, 消息, 培训模块)
        """
        training = self.get_user_training(user_id, module_id)
        if not training:
            return False, "未找到培训记录", None
        
        if training.status != TrainingStatus.NOT_STARTED:
            return False, f"培训已开始或已完成，当前状态: {training.status.value}", None
        
        module = self.modules.get(module_id)
        if not module:
            return False, "培训模块不存在", None
        
        training.status = TrainingStatus.IN_PROGRESS
        training.started_at = time.time()
        training.attempts += 1
        
        self._save_trainings()
        
        logger.info(f"用户 {user_id} 开始培训: {module.name}")
        return True, "培训已开始", module
    
    def complete_training(
        self,
        user_id: str,
        module_id: str,
        score: int
    ) -> Tuple[bool, str]:
        """
        完成培训
        
        Args:
            user_id: 用户ID
            module_id: 模块ID
            score: 得分
        
        Returns:
            (成功标志, 消息)
        """
        training = self.get_user_training(user_id, module_id)
        if not training:
            return False, "未找到培训记录"
        
        if training.status != TrainingStatus.IN_PROGRESS:
            return False, f"培训未在进行中，当前状态: {training.status.value}"
        
        module = self.modules.get(module_id)
        if not module:
            return False, "培训模块不存在"
        
        passing_score = module.passing_score
        passed = score >= passing_score
        
        training.completed_at = time.time()
        training.score = score
        
        if passed:
            training.status = TrainingStatus.COMPLETED
            # 计算新过期时间
            training.expires_at = time.time() + (self.config["training_expiry_days"] * 24 * 3600)
            message = f"培训完成，得分: {score}，通过"
        else:
            training.status = TrainingStatus.FAILED
            message = f"培训未通过，得分: {score}，需要 {passing_score} 分"
        
        self._save_trainings()
        
        # 记录审计日志
        self.access_logger.log_security_event(
            user_id=user_id,
            event_type="TRAINING_COMPLETED" if passed else "TRAINING_FAILED",
            severity="info",
            details={
                "module_id": module_id,
                "module_name": module.name,
                "score": score,
                "passing_score": passing_score
            }
        )
        
        logger.info(f"用户 {user_id} 完成培训 {module.name}: {message}")
        return passed, message
    
    def get_user_training(self, user_id: str, module_id: str) -> Optional[UserTraining]:
        """获取用户的特定培训记录"""
        if user_id not in self.user_trainings:
            return None
        
        for training in self.user_trainings[user_id]:
            if training.module_id == module_id:
                return training
        
        return None
    
    def get_user_trainings(
        self,
        user_id: str,
        status: Optional[TrainingStatus] = None
    ) -> List[Dict[str, Any]]:
        """获取用户的所有培训记录"""
        if user_id not in self.user_trainings:
            return []
        
        trainings = []
        for training in self.user_trainings[user_id]:
            module = self.modules.get(training.module_id)
            if not module:
                continue
            
            if status and training.status != status:
                continue
            
            trainings.append({
                "record_id": training.record_id,
                "module_id": training.module_id,
                "module_name": module.name,
                "module_type": module.type.value,
                "status": training.status.value,
                "started_at": training.started_at,
                "completed_at": training.completed_at,
                "score": training.score,
                "attempts": training.attempts,
                "expires_at": training.expires_at,
                "duration_minutes": module.duration_minutes
            })
        
        return trainings
    
    def get_required_trainings(self, user_id: str, roles: List[str]) -> List[Dict[str, Any]]:
        """获取用户需要完成的培训"""
        required = []
        
        for module in self.modules.values():
            # 检查角色要求
            if "*" in module.required_for_roles:
                required_for_user = True
            elif any(role in module.required_for_roles for role in roles):
                required_for_user = True
            else:
                required_for_user = False
            
            if not required_for_user:
                continue
            
            # 检查是否已完成
            training = self.get_user_training(user_id, module.module_id)
            if not training or training.status != TrainingStatus.COMPLETED:
                required.append({
                    "module_id": module.module_id,
                    "name": module.name,
                    "type": module.type.value,
                    "description": module.description,
                    "duration_minutes": module.duration_minutes
                })
            elif training.status == TrainingStatus.COMPLETED:
                # 检查是否过期
                if training.expires_at and training.expires_at < time.time():
                    required.append({
                        "module_id": module.module_id,
                        "name": module.name,
                        "type": module.type.value,
                        "description": module.description,
                        "duration_minutes": module.duration_minutes,
                        "expired": True
                    })
        
        return required
    
    def check_compliance(self, user_id: str, roles: List[str]) -> Dict[str, Any]:
        """检查用户培训合规状态"""
        required = self.get_required_trainings(user_id, roles)
        completed = self.get_user_trainings(user_id, TrainingStatus.COMPLETED)
        
        result = {
            "user_id": user_id,
            "compliant": len(required) == 0,
            "total_required": len(required),
            "total_completed": len(completed),
            "required_trainings": required,
            "completed_trainings": [
                {
                    "module_id": t["module_id"],
                    "name": t["module_name"],
                    "completed_at": t["completed_at"],
                    "expires_at": t["expires_at"]
                }
                for t in completed
            ]
        }
        
        return result
    
    def add_module(self, module: TrainingModule) -> Tuple[bool, str]:
        """添加培训模块"""
        if module.module_id in self.modules:
            return False, f"模块ID已存在: {module.module_id}"
        
        self.modules[module.module_id] = module
        self._save_modules()
        
        logger.info(f"添加培训模块: {module.name}")
        return True, "模块添加成功"
    
    def update_module(self, module_id: str, **kwargs) -> Tuple[bool, str]:
        """更新培训模块"""
        if module_id not in self.modules:
            return False, f"模块不存在: {module_id}"
        
        module = self.modules[module_id]
        for key, value in kwargs.items():
            if hasattr(module, key):
                setattr(module, key, value)
        
        module.updated_at = time.time()
        self._save_modules()
        
        logger.info(f"更新培训模块: {module_id}")
        return True, "模块更新成功"
    
    def get_modules(
        self,
        training_type: Optional[TrainingType] = None,
        required_for: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取培训模块列表"""
        modules = list(self.modules.values())
        
        if training_type:
            modules = [m for m in modules if m.type == training_type]
        
        if required_for:
            modules = [m for m in modules if "*" in m.required_for_roles or required_for in m.required_for_roles]
        
        return [
            {
                "module_id": m.module_id,
                "name": m.name,
                "type": m.type.value,
                "description": m.description,
                "duration_minutes": m.duration_minutes,
                "version": m.version,
                "required_for_roles": m.required_for_roles
            }
            for m in modules
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_modules": len(self.modules),
            "total_users": len(self.user_trainings),
            "total_trainings": sum(len(t) for t in self.user_trainings.values()),
            "by_type": {},
            "by_status": {},
            "completion_rate": 0
        }
        
        total_completed = 0
        
        for user_id, trainings in self.user_trainings.items():
            for training in trainings:
                # 按类型统计
                module = self.modules.get(training.module_id)
                if module:
                    mtype = module.type.value
                    stats["by_type"][mtype] = stats["by_type"].get(mtype, 0) + 1
                
                # 按状态统计
                status = training.status.value
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
                
                if training.status == TrainingStatus.COMPLETED:
                    total_completed += 1
        
        if stats["total_trainings"] > 0:
            stats["completion_rate"] = (total_completed / stats["total_trainings"]) * 100
        
        return stats


# 单例实例
_security_awareness_instance = None


def get_security_awareness() -> SecurityAwareness:
    """获取安全意识管理器单例实例"""
    global _security_awareness_instance
    if _security_awareness_instance is None:
        _security_awareness_instance = SecurityAwareness()
    return _security_awareness_instance

