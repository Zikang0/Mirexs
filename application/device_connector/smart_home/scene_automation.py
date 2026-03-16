"""
场景自动化模块 - Mirexs智能家居集成

提供智能家居场景自动化功能，包括：
1. 场景管理
2. 自动化规则
3. 条件触发
4. 动作执行
5. 定时任务
6. 场景联动
"""

import logging
import time
import threading
import croniter
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)

class TriggerType(Enum):
    """触发类型枚举"""
    DEVICE = "device"          # 设备状态变化
    SCHEDULE = "schedule"      # 定时
    LOCATION = "location"      # 地理位置
    WEATHER = "weather"        # 天气
    SUN = "sun"                # 日出日落
    MANUAL = "manual"          # 手动触发
    SYSTEM = "system"          # 系统事件
    CUSTOM = "custom"          # 自定义

class ConditionType(Enum):
    """条件类型枚举"""
    DEVICE = "device"          # 设备状态条件
    TIME = "time"              # 时间条件
    LOCATION = "location"      # 位置条件
    WEATHER = "weather"        # 天气条件
    AND = "and"                # 与条件
    OR = "or"                  # 或条件
    NOT = "not"                # 非条件

class ActionType(Enum):
    """动作类型枚举"""
    DEVICE = "device"          # 控制设备
    SCENE = "scene"            # 激活场景
    DELAY = "delay"            # 延迟
    NOTIFICATION = "notification"  # 发送通知
    WEBHOOK = "webhook"        # 调用webhook
    SCRIPT = "script"          # 执行脚本
    CUSTOM = "custom"          # 自定义

class AutomationStatus(Enum):
    """自动化状态枚举"""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"

@dataclass
class Trigger:
    """触发条件"""
    id: str
    type: TriggerType
    config: Dict[str, Any]
    enabled: bool = True

@dataclass
class Condition:
    """执行条件"""
    id: str
    type: ConditionType
    config: Dict[str, Any]
    enabled: bool = True

@dataclass
class Action:
    """执行动作"""
    id: str
    type: ActionType
    config: Dict[str, Any]
    enabled: bool = True

@dataclass
class AutomationRule:
    """自动化规则"""
    id: str
    name: str
    description: str = ""
    triggers: List[Trigger] = field(default_factory=list)
    conditions: List[Condition] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    status: AutomationStatus = AutomationStatus.ACTIVE
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_triggered: Optional[float] = None
    trigger_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Scene:
    """场景"""
    id: str
    name: str
    description: str = ""
    actions: List[Action] = field(default_factory=list)
    icon: Optional[str] = None
    color: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_activated: Optional[float] = None
    activate_count: int = 0

@dataclass
class SceneAutomationConfig:
    """场景自动化配置"""
    # 调度配置
    check_interval: int = 1  # 秒
    schedule_precision: int = 60  # 秒
    
    # 执行配置
    max_concurrent_rules: int = 10
    action_timeout: int = 30  # 秒
    retry_on_failure: bool = True
    max_retries: int = 3
    
    # 历史记录
    keep_history: bool = True
    max_history: int = 1000

class SceneAutomation:
    """
    场景自动化管理器
    
    负责智能家居场景和自动化规则的管理。
    """
    
    def __init__(self, config: Optional[SceneAutomationConfig] = None):
        """
        初始化场景自动化管理器
        
        Args:
            config: 场景自动化配置
        """
        self.config = config or SceneAutomationConfig()
        
        # 场景和规则存储
        self.scenes: Dict[str, Scene] = {}
        self.rules: Dict[str, AutomationRule] = {}
        
        # 触发队列
        self.trigger_queue: List[str] = []
        
        # 执行历史
        self.execution_history: List[Dict[str, Any]] = []
        
        # 调度线程
        self._scheduler_thread: Optional[threading.Thread] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_scheduler = threading.Event()
        
        # 回调函数
        self.on_scene_activated: Optional[Callable[[str], None]] = None
        self.on_rule_triggered: Optional[Callable[[str], None]] = None
        self.on_action_executed: Optional[Callable[[Action, bool], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 统计
        self.stats = {
            "scenes_activated": 0,
            "rules_triggered": 0,
            "actions_executed": 0,
            "actions_succeeded": 0,
            "actions_failed": 0,
            "errors": 0
        }
        
        # 启动调度器
        self._start_scheduler()
        
        logger.info("SceneAutomation initialized")
    
    def _start_scheduler(self):
        """启动调度器"""
        def scheduler_loop():
            while not self._stop_scheduler.is_set():
                try:
                    self._check_triggers()
                    self._stop_scheduler.wait(self.config.check_interval)
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
                    self.stats["errors"] += 1
        
        def worker_loop():
            while not self._stop_scheduler.is_set():
                try:
                    if self.trigger_queue:
                        rule_id = self.trigger_queue.pop(0)
                        self._execute_rule(rule_id)
                    self._stop_scheduler.wait(0.1)
                except Exception as e:
                    logger.error(f"Worker error: {e}")
                    self.stats["errors"] += 1
        
        self._scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        self._worker_thread = threading.Thread(target=worker_loop, daemon=True)
        self._worker_thread.start()
        
        logger.debug("Scene automation scheduler started")
    
    def _check_triggers(self):
        """检查所有触发条件"""
        current_time = time.time()
        
        for rule in self.rules.values():
            if rule.status != AutomationStatus.ACTIVE:
                continue
            
            for trigger in rule.triggers:
                if not trigger.enabled:
                    continue
                
                if self._check_trigger(trigger, current_time):
                    if rule.id not in self.trigger_queue:
                        self.trigger_queue.append(rule.id)
                        logger.debug(f"Rule {rule.name} triggered by {trigger.type.value}")
                    break
    
    def _check_trigger(self, trigger: Trigger, current_time: float) -> bool:
        """检查单个触发条件"""
        if trigger.type == TriggerType.SCHEDULE:
            return self._check_schedule_trigger(trigger, current_time)
        elif trigger.type == TriggerType.SUN:
            return self._check_sun_trigger(trigger, current_time)
        elif trigger.type == TriggerType.DEVICE:
            # 设备触发由外部调用
            return False
        else:
            return False
    
    def _check_schedule_trigger(self, trigger: Trigger, current_time: float) -> bool:
        """检查定时触发"""
        cron_expr = trigger.config.get("cron")
        if not cron_expr:
            return False
        
        try:
            cron = croniter.croniter(cron_expr, datetime.fromtimestamp(current_time))
            next_time = cron.get_next(float)
            return abs(next_time - current_time) < self.config.schedule_precision
        except:
            return False
    
    def _check_sun_trigger(self, trigger: Trigger, current_time: float) -> bool:
        """检查日出日落触发"""
        event = trigger.config.get("event")  # sunrise, sunset
        latitude = trigger.config.get("latitude")
        longitude = trigger.config.get("longitude")
        
        # 实际实现中会计算日出日落时间
        return False
    
    def _execute_rule(self, rule_id: str):
        """执行自动化规则"""
        if rule_id not in self.rules:
            return
        
        rule = self.rules[rule_id]
        
        # 检查条件
        if not self._check_conditions(rule.conditions):
            logger.debug(f"Rule {rule.name} conditions not met")
            return
        
        logger.info(f"Executing rule: {rule.name}")
        
        rule.last_triggered = time.time()
        rule.trigger_count += 1
        self.stats["rules_triggered"] += 1
        
        if self.on_rule_triggered:
            self.on_rule_triggered(rule_id)
        
        # 执行动作
        for action in rule.actions:
            if action.enabled:
                success = self._execute_action(action)
                
                if not success and self.config.retry_on_failure:
                    self._retry_action(action)
    
    def _check_conditions(self, conditions: List[Condition]) -> bool:
        """检查条件列表"""
        if not conditions:
            return True
        
        # 简单实现：所有条件都必须满足
        for condition in conditions:
            if not condition.enabled:
                continue
            
            if not self._check_condition(condition):
                return False
        
        return True
    
    def _check_condition(self, condition: Condition) -> bool:
        """检查单个条件"""
        if condition.type == ConditionType.DEVICE:
            device_id = condition.config.get("device_id")
            state = condition.config.get("state")
            value = condition.config.get("value")
            # 实际实现中会检查设备状态
            return True
        
        elif condition.type == ConditionType.TIME:
            start = condition.config.get("start")
            end = condition.config.get("end")
            current_time = datetime.now().time()
            # 检查当前时间是否在范围内
            return True
        
        elif condition.type == ConditionType.LOCATION:
            # 检查地理位置
            return True
        
        elif condition.type == ConditionType.WEATHER:
            # 检查天气条件
            return True
        
        return True
    
    def _execute_action(self, action: Action) -> bool:
        """执行动作"""
        logger.debug(f"Executing action: {action.type.value}")
        
        success = False
        
        if action.type == ActionType.DEVICE:
            device_id = action.config.get("device_id")
            command = action.config.get("command")
            params = action.config.get("params", {})
            
            # 实际实现中会调用设备管理器
            success = True
            
        elif action.type == ActionType.SCENE:
            scene_id = action.config.get("scene_id")
            self.activate_scene(scene_id)
            success = True
            
        elif action.type == ActionType.DELAY:
            duration = action.config.get("duration", 1)
            time.sleep(duration)
            success = True
            
        elif action.type == ActionType.NOTIFICATION:
            title = action.config.get("title", "Mirexs")
            message = action.config.get("message", "")
            # 发送通知
            success = True
        
        # 更新统计
        self.stats["actions_executed"] += 1
        if success:
            self.stats["actions_succeeded"] += 1
        else:
            self.stats["actions_failed"] += 1
        
        if self.on_action_executed:
            self.on_action_executed(action, success)
        
        return success
    
    def _retry_action(self, action: Action, max_retries: int = 3):
        """重试动作"""
        for attempt in range(max_retries):
            logger.debug(f"Retrying action (attempt {attempt + 1}/{max_retries})")
            time.sleep(2 ** attempt)  # 指数退避
            
            if self._execute_action(action):
                return
        
        logger.error(f"Action failed after {max_retries} retries")
    
    def device_triggered(self, device_id: str, state: Dict[str, Any]):
        """
        设备状态变化触发
        
        Args:
            device_id: 设备ID
            state: 新状态
        """
        logger.debug(f"Device triggered: {device_id}")
        
        for rule in self.rules.values():
            if rule.status != AutomationStatus.ACTIVE:
                continue
            
            for trigger in rule.triggers:
                if trigger.type == TriggerType.DEVICE:
                    trigger_device = trigger.config.get("device_id")
                    trigger_state = trigger.config.get("state")
                    
                    if trigger_device == device_id and trigger_state in state:
                        if rule.id not in self.trigger_queue:
                            self.trigger_queue.append(rule.id)
                        break
    
    def create_scene(self, name: str, actions: List[Dict[str, Any]],
                    description: str = "", icon: Optional[str] = None) -> str:
        """
        创建场景
        
        Args:
            name: 场景名称
            actions: 动作列表
            description: 描述
            icon: 图标
        
        Returns:
            场景ID
        """
        scene_id = str(uuid.uuid4())
        
        scene_actions = []
        for i, action_config in enumerate(actions):
            action = Action(
                id=f"action_{i}",
                type=ActionType(action_config["type"]),
                config=action_config.get("config", {})
            )
            scene_actions.append(action)
        
        scene = Scene(
            id=scene_id,
            name=name,
            description=description,
            actions=scene_actions,
            icon=icon
        )
        
        self.scenes[scene_id] = scene
        
        logger.info(f"Scene created: {name} ({scene_id})")
        
        return scene_id
    
    def activate_scene(self, scene_id: str) -> bool:
        """
        激活场景
        
        Args:
            scene_id: 场景ID
        
        Returns:
            是否成功
        """
        if scene_id not in self.scenes:
            logger.warning(f"Scene {scene_id} not found")
            return False
        
        scene = self.scenes[scene_id]
        
        logger.info(f"Activating scene: {scene.name}")
        
        scene.last_activated = time.time()
        scene.activate_count += 1
        self.stats["scenes_activated"] += 1
        
        # 执行场景动作
        for action in scene.actions:
            if action.enabled:
                self._execute_action(action)
        
        if self.on_scene_activated:
            self.on_scene_activated(scene_id)
        
        return True
    
    def create_rule(self, name: str, triggers: List[Dict[str, Any]],
                   actions: List[Dict[str, Any]],
                   conditions: Optional[List[Dict[str, Any]]] = None,
                   description: str = "") -> str:
        """
        创建自动化规则
        
        Args:
            name: 规则名称
            triggers: 触发条件列表
            actions: 动作列表
            conditions: 条件列表
            description: 描述
        
        Returns:
            规则ID
        """
        rule_id = str(uuid.uuid4())
        
        rule_triggers = []
        for i, trigger_config in enumerate(triggers):
            trigger = Trigger(
                id=f"trigger_{i}",
                type=TriggerType(trigger_config["type"]),
                config=trigger_config.get("config", {})
            )
            rule_triggers.append(trigger)
        
        rule_actions = []
        for i, action_config in enumerate(actions):
            action = Action(
                id=f"action_{i}",
                type=ActionType(action_config["type"]),
                config=action_config.get("config", {})
            )
            rule_actions.append(action)
        
        rule_conditions = []
        if conditions:
            for i, condition_config in enumerate(conditions):
                condition = Condition(
                    id=f"condition_{i}",
                    type=ConditionType(condition_config["type"]),
                    config=condition_config.get("config", {})
                )
                rule_conditions.append(condition)
        
        rule = AutomationRule(
            id=rule_id,
            name=name,
            description=description,
            triggers=rule_triggers,
            actions=rule_actions,
            conditions=rule_conditions
        )
        
        self.rules[rule_id] = rule
        
        logger.info(f"Automation rule created: {name} ({rule_id})")
        
        return rule_id
    
    def update_rule_status(self, rule_id: str, status: AutomationStatus) -> bool:
        """
        更新规则状态
        
        Args:
            rule_id: 规则ID
            status: 新状态
        
        Returns:
            是否成功
        """
        if rule_id not in self.rules:
            logger.warning(f"Rule {rule_id} not found")
            return False
        
        self.rules[rule_id].status = status
        logger.info(f"Rule {rule_id} status updated to {status.value}")
        
        return True
    
    def delete_scene(self, scene_id: str) -> bool:
        """
        删除场景
        
        Args:
            scene_id: 场景ID
        
        Returns:
            是否成功
        """
        if scene_id in self.scenes:
            del self.scenes[scene_id]
            logger.info(f"Scene deleted: {scene_id}")
            return True
        return False
    
    def delete_rule(self, rule_id: str) -> bool:
        """
        删除规则
        
        Args:
            rule_id: 规则ID
        
        Returns:
            是否成功
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Rule deleted: {rule_id}")
            return True
        return False
    
    def get_scenes(self) -> List[Scene]:
        """获取所有场景"""
        return list(self.scenes.values())
    
    def get_rules(self, status: Optional[AutomationStatus] = None) -> List[AutomationRule]:
        """
        获取规则列表
        
        Args:
            status: 状态过滤
        
        Returns:
            规则列表
        """
        rules = list(self.rules.values())
        
        if status:
            rules = [r for r in rules if r.status == status]
        
        return rules
    
    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取执行历史
        
        Args:
            limit: 返回数量
        
        Returns:
            历史记录
        """
        return self.execution_history[-limit:]
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取场景自动化管理器状态
        
        Returns:
            状态字典
        """
        return {
            "scenes": {
                "total": len(self.scenes)
            },
            "rules": {
                "total": len(self.rules),
                "active": len([r for r in self.rules.values() if r.status == AutomationStatus.ACTIVE]),
                "paused": len([r for r in self.rules.values() if r.status == AutomationStatus.PAUSED])
            },
            "queue_size": len(self.trigger_queue),
            "stats": self.stats,
            "history_size": len(self.execution_history)
        }
    
    def shutdown(self):
        """关闭场景自动化管理器"""
        logger.info("Shutting down SceneAutomation...")
        
        self._stop_scheduler.set()
        
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=2)
        
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2)
        
        self.scenes.clear()
        self.rules.clear()
        self.trigger_queue.clear()
        self.execution_history.clear()
        
        logger.info("SceneAutomation shutdown completed")

# 单例模式实现
_scene_automation_instance: Optional[SceneAutomation] = None

def get_scene_automation(config: Optional[SceneAutomationConfig] = None) -> SceneAutomation:
    """
    获取场景自动化管理器单例
    
    Args:
        config: 场景自动化配置
    
    Returns:
        场景自动化管理器实例
    """
    global _scene_automation_instance
    if _scene_automation_instance is None:
        _scene_automation_instance = SceneAutomation(config)
    return _scene_automation_instance

