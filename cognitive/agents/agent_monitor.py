"""
智能体监控器：监控智能体状态和性能
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import defaultdict, deque
import time
import psutil
import threading

from ..memory.episodic_memory import EpisodicMemory
from ..memory.semantic_memory import SemanticMemory
from ..memory.working_memory import WorkingMemory
from ...infrastructure.communication.message_bus import MessageBus
from ...data.databases.vector_db.similarity_search import SimilaritySearch

class AgentStatus(Enum):
    """智能体状态枚举"""
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"
    RECOVERING = "recovering"

class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class AgentMetrics:
    """智能体指标"""
    agent_id: str
    timestamp: float
    cpu_usage: float
    memory_usage: float
    response_time: float
    task_success_rate: float
    error_rate: float
    communication_volume: int

@dataclass
class HealthCheck:
    """健康检查结果"""
    agent_id: str
    health_status: HealthStatus
    check_timestamp: float
    issues_detected: List[str]
    recommendations: List[str]
    overall_score: float

@dataclass
class PerformanceAlert:
    """性能告警"""
    alert_id: str
    agent_id: str
    alert_type: str
    severity: str
    description: str
    triggered_value: float
    threshold: float
    timestamp: float

class AgentMonitor:
    """
    智能体监控器 - 监控智能体状态、性能和健康度
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # 核心组件
        self.episodic_memory = EpisodicMemory(config.get("memory", {}))
        self.semantic_memory = SemanticMemory(config.get("memory", {}))
        self.working_memory = WorkingMemory(config.get("memory", {}))
        self.message_bus = MessageBus(config.get("message_bus", {}))
        self.similarity_search = SimilaritySearch(config.get("vector_db", {}))
        
        # 监控状态
        self.monitored_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.health_check_results: Dict[str, HealthCheck] = {}
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        
        # 监控配置
        self.monitoring_config = {
            "metrics_collection_interval": config.get("metrics_interval", 30),
            "health_check_interval": config.get("health_check_interval", 300),
            "alert_check_interval": config.get("alert_check_interval", 60),
            "performance_thresholds": config.get("performance_thresholds", {
                "cpu_usage": 0.8,
                "memory_usage": 0.8,
                "response_time": 5.0,
                "error_rate": 0.1,
                "task_success_rate": 0.7
            })
        }
        
        # 监控任务
        self.metrics_collection_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
        self.alert_monitor_task: Optional[asyncio.Task] = None
        
        # 性能指标
        self.monitoring_metrics = {
            "agents_monitored": 0,
            "metrics_collected": 0,
            "health_checks_performed": 0,
            "alerts_triggered": 0,
            "average_health_score": 0.0
        }
        
        # 模型加载
        self.health_assessment_model = self._load_health_assessment_model()
        self.anomaly_detection_model = self._load_anomaly_detection_model()
        
        self.logger.info("AgentMonitor initialized")

    def _load_health_assessment_model(self):
        """加载健康评估模型"""
        try:
            self.logger.info("Loading health assessment model...")
            
            # 模拟健康评估模型
            health_config = {
                "weight_cpu": 0.2,
                "weight_memory": 0.2,
                "weight_response_time": 0.25,
                "weight_success_rate": 0.2,
                "weight_error_rate": 0.15,
                "degraded_threshold": 0.7,
                "critical_threshold": 0.4
            }
            
            self.logger.info("Health assessment model loaded successfully")
            return health_config
            
        except Exception as e:
            self.logger.error(f"Failed to load health assessment model: {e}")
            raise

    def _load_anomaly_detection_model(self):
        """加载异常检测模型"""
        try:
            self.logger.info("Loading anomaly detection model...")
            
            # 模拟异常检测模型
            anomaly_config = {
                "z_score_threshold": 3.0,
                "moving_average_window": 10,
                "change_point_sensitivity": 0.1,
                "seasonality_detection": True
            }
            
            self.logger.info("Anomaly detection model loaded successfully")
            return anomaly_config
            
        except Exception as e:
            self.logger.error(f"Failed to load anomaly detection model: {e}")
            raise

    async def start_monitoring(self):
        """启动监控系统"""
        self.logger.info("Starting AgentMonitor system...")
        
        # 启动监控任务
        self.metrics_collection_task = asyncio.create_task(self._metrics_collection_loop())
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        self.alert_monitor_task = asyncio.create_task(self._alert_monitoring_loop())
        
        self.logger.info("AgentMonitor system started successfully")

    async def stop_monitoring(self):
        """停止监控系统"""
        self.logger.info("Stopping AgentMonitor system...")
        
        # 停止监控任务
        if self.metrics_collection_task:
            self.metrics_collection_task.cancel()
            try:
                await self.metrics_collection_task
            except asyncio.CancelledError:
                pass
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.alert_monitor_task:
            self.alert_monitor_task.cancel()
            try:
                await self.alert_monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("AgentMonitor system stopped")

    async def register_agent(self, agent_id: str, agent_info: Dict[str, Any]) -> bool:
        """
        注册智能体进行监控
        
        Args:
            agent_id: 智能体ID
            agent_info: 智能体信息
            
        Returns:
            注册是否成功
        """
        try:
            self.monitored_agents[agent_id] = {
                **agent_info,
                "registration_time": time.time(),
                "last_metrics_update": time.time(),
                "status": AgentStatus.ACTIVE,
                "monitoring_enabled": True
            }
            
            # 初始化指标历史
            self.agent_metrics_history[agent_id] = deque(maxlen=1000)
            
            self.monitoring_metrics["agents_monitored"] += 1
            
            self.logger.info(f"Agent {agent_id} registered for monitoring")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_id} for monitoring: {e}")
            return False

    async def unregister_agent(self, agent_id: str):
        """注销智能体监控"""
        if agent_id in self.monitored_agents:
            del self.monitored_agents[agent_id]
            
            if agent_id in self.agent_metrics_history:
                del self.agent_metrics_history[agent_id]
            
            if agent_id in self.health_check_results:
                del self.health_check_results[agent_id]
            
            # 清理相关告警
            alerts_to_remove = [alert_id for alert_id, alert in self.active_alerts.items() 
                              if alert.agent_id == agent_id]
            for alert_id in alerts_to_remove:
                del self.active_alerts[alert_id]
            
            self.monitoring_metrics["agents_monitored"] = max(0, self.monitoring_metrics["agents_monitored"] - 1)
            
            self.logger.info(f"Agent {agent_id} unregistered from monitoring")

    async def _metrics_collection_loop(self):
        """指标收集循环"""
        self.logger.info("Metrics collection loop started")
        
        try:
            while True:
                collection_start = time.time()
                metrics_collected = 0
                
                # 收集所有监控智能体的指标
                for agent_id in list(self.monitored_agents.keys()):
                    if self.monitored_agents[agent_id].get("monitoring_enabled", True):
                        try:
                            metrics = await self._collect_agent_metrics(agent_id)
                            if metrics:
                                self.agent_metrics_history[agent_id].append(metrics)
                                self.monitored_agents[agent_id]["last_metrics_update"] = time.time()
                                metrics_collected += 1
                        except Exception as e:
                            self.logger.error(f"Failed to collect metrics for agent {agent_id}: {e}")
                
                self.monitoring_metrics["metrics_collected"] += metrics_collected
                
                collection_time = time.time() - collection_start
                self.logger.debug(f"Metrics collection completed: {metrics_collected} agents, "
                                f"time: {collection_time:.2f}s")
                
                # 等待下一个收集周期
                await asyncio.sleep(self.monitoring_config["metrics_collection_interval"])
                
        except asyncio.CancelledError:
            self.logger.info("Metrics collection loop stopped")
        except Exception as e:
            self.logger.error(f"Metrics collection loop error: {e}")

    async def _collect_agent_metrics(self, agent_id: str) -> Optional[AgentMetrics]:
        """收集智能体指标"""
        try:
            # 获取系统资源使用情况
            cpu_usage = await self._get_agent_cpu_usage(agent_id)
            memory_usage = await self._get_agent_memory_usage(agent_id)
            
            # 获取性能指标
            response_time = await self._get_agent_response_time(agent_id)
            task_success_rate = await self._get_agent_task_success_rate(agent_id)
            error_rate = await self._get_agent_error_rate(agent_id)
            communication_volume = await self._get_agent_communication_volume(agent_id)
            
            metrics = AgentMetrics(
                agent_id=agent_id,
                timestamp=time.time(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                response_time=response_time,
                task_success_rate=task_success_rate,
                error_rate=error_rate,
                communication_volume=communication_volume
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics for agent {agent_id}: {e}")
            return None

    async def _get_agent_cpu_usage(self, agent_id: str) -> float:
        """获取智能体CPU使用率"""
        try:
            # 模拟CPU使用率获取
            # 实际项目中会通过系统监控或智能体报告获取
            return psutil.cpu_percent(interval=0.1) / 100.0  # 转换为0-1范围
        except Exception:
            return 0.0

    async def _get_agent_memory_usage(self, agent_id: str) -> float:
        """获取智能体内存使用率"""
        try:
            # 模拟内存使用率获取
            memory_info = psutil.virtual_memory()
            return memory_info.percent / 100.0  # 转换为0-1范围
        except Exception:
            return 0.0

    async def _get_agent_response_time(self, agent_id: str) -> float:
        """获取智能体响应时间"""
        try:
            # 模拟响应时间获取
            # 实际项目中会通过性能监控获取
            recent_metrics = list(self.agent_metrics_history[agent_id])
            if recent_metrics:
                return np.mean([m.response_time for m in recent_metrics[-5:]])  # 最近5次的平均值
            return 1.0  # 默认值
        except Exception:
            return 1.0

    async def _get_agent_task_success_rate(self, agent_id: str) -> float:
        """获取智能体任务成功率"""
        try:
            # 从记忆系统获取任务成功率
            success_rate = await self.episodic_memory.get_agent_success_rate(agent_id)
            return success_rate or 0.8  # 默认值
        except Exception:
            return 0.8

    async def _get_agent_error_rate(self, agent_id: str) -> float:
        """获取智能体错误率"""
        try:
            # 从记忆系统获取错误率
            error_rate = await self.episodic_memory.get_agent_error_rate(agent_id)
            return error_rate or 0.05  # 默认值
        except Exception:
            return 0.05

    async def _get_agent_communication_volume(self, agent_id: str) -> int:
        """获取智能体通信量"""
        try:
            # 从消息总线获取通信量
            # 简化实现：返回模拟值
            return 100  # 模拟通信量
        except Exception:
            return 0

    async def _health_check_loop(self):
        """健康检查循环"""
        self.logger.info("Health check loop started")
        
        try:
            while True:
                health_checks_performed = 0
                
                # 对所有监控智能体进行健康检查
                for agent_id in list(self.monitored_agents.keys()):
                    if self.monitored_agents[agent_id].get("monitoring_enabled", True):
                        try:
                            health_check = await self._perform_health_check(agent_id)
                            if health_check:
                                self.health_check_results[agent_id] = health_check
                                health_checks_performed += 1
                                
                                # 更新智能体状态
                                await self._update_agent_status(agent_id, health_check)
                        except Exception as e:
                            self.logger.error(f"Health check failed for agent {agent_id}: {e}")
                
                self.monitoring_metrics["health_checks_performed"] += health_checks_performed
                
                # 更新平均健康分数
                if self.health_check_results:
                    avg_score = np.mean([h.overall_score for h in self.health_check_results.values()])
                    self.monitoring_metrics["average_health_score"] = avg_score
                
                self.logger.debug(f"Health checks completed: {health_checks_performed} agents")
                
                # 等待下一个检查周期
                await asyncio.sleep(self.monitoring_config["health_check_interval"])
                
        except asyncio.CancelledError:
            self.logger.info("Health check loop stopped")
        except Exception as e:
            self.logger.error(f"Health check loop error: {e}")

    async def _perform_health_check(self, agent_id: str) -> Optional[HealthCheck]:
        """执行健康检查"""
        try:
            # 获取最近指标
            recent_metrics = list(self.agent_metrics_history[agent_id])
            if not recent_metrics:
                self.logger.warning(f"No metrics available for health check of agent {agent_id}")
                return None
            
            latest_metrics = recent_metrics[-1]
            
            # 计算各项健康分数
            cpu_score = self._calculate_cpu_health(latest_metrics.cpu_usage)
            memory_score = self._calculate_memory_health(latest_metrics.memory_usage)
            response_score = self._calculate_response_health(latest_metrics.response_time)
            success_score = self._calculate_success_health(latest_metrics.task_success_rate)
            error_score = self._calculate_error_health(latest_metrics.error_rate)
            
            # 计算综合健康分数
            overall_score = (
                cpu_score * self.health_assessment_model["weight_cpu"] +
                memory_score * self.health_assessment_model["weight_memory"] +
                response_score * self.health_assessment_model["weight_response_time"] +
                success_score * self.health_assessment_model["weight_success_rate"] +
                error_score * self.health_assessment_model["weight_error_rate"]
            )
            
            # 确定健康状态
            if overall_score >= self.health_assessment_model["degraded_threshold"]:
                health_status = HealthStatus.HEALTHY
            elif overall_score >= self.health_assessment_model["critical_threshold"]:
                health_status = HealthStatus.DEGRADED
            else:
                health_status = HealthStatus.CRITICAL
            
            # 检测问题
            issues_detected = await self._detect_health_issues(latest_metrics, overall_score)
            
            # 生成建议
            recommendations = await self._generate_health_recommendations(issues_detected, latest_metrics)
            
            health_check = HealthCheck(
                agent_id=agent_id,
                health_status=health_status,
                check_timestamp=time.time(),
                issues_detected=issues_detected,
                recommendations=recommendations,
                overall_score=overall_score
            )
            
            self.logger.debug(f"Health check completed for agent {agent_id}: {health_status.value} "
                            f"(score: {overall_score:.2f})")
            
            return health_check
            
        except Exception as e:
            self.logger.error(f"Health check failed for agent {agent_id}: {e}")
            return None

    def _calculate_cpu_health(self, cpu_usage: float) -> float:
        """计算CPU健康分数"""
        threshold = self.monitoring_config["performance_thresholds"]["cpu_usage"]
        if cpu_usage <= threshold * 0.7:
            return 1.0
        elif cpu_usage <= threshold:
            return 0.7
        else:
            return 0.3

    def _calculate_memory_health(self, memory_usage: float) -> float:
        """计算内存健康分数"""
        threshold = self.monitoring_config["performance_thresholds"]["memory_usage"]
        if memory_usage <= threshold * 0.7:
            return 1.0
        elif memory_usage <= threshold:
            return 0.7
        else:
            return 0.3

    def _calculate_response_health(self, response_time: float) -> float:
        """计算响应时间健康分数"""
        threshold = self.monitoring_config["performance_thresholds"]["response_time"]
        if response_time <= threshold * 0.5:
            return 1.0
        elif response_time <= threshold:
            return 0.7
        else:
            return 0.3

    def _calculate_success_health(self, success_rate: float) -> float:
        """计算成功率健康分数"""
        threshold = self.monitoring_config["performance_thresholds"]["task_success_rate"]
        if success_rate >= 0.9:
            return 1.0
        elif success_rate >= threshold:
            return 0.7
        else:
            return 0.3

    def _calculate_error_health(self, error_rate: float) -> float:
        """计算错误率健康分数"""
        threshold = self.monitoring_config["performance_thresholds"]["error_rate"]
        if error_rate <= threshold * 0.5:
            return 1.0
        elif error_rate <= threshold:
            return 0.7
        else:
            return 0.3

    async def _detect_health_issues(self, metrics: AgentMetrics, overall_score: float) -> List[str]:
        """检测健康问题"""
        issues = []
        thresholds = self.monitoring_config["performance_thresholds"]
        
        if metrics.cpu_usage > thresholds["cpu_usage"]:
            issues.append("high_cpu_usage")
        
        if metrics.memory_usage > thresholds["memory_usage"]:
            issues.append("high_memory_usage")
        
        if metrics.response_time > thresholds["response_time"]:
            issues.append("slow_response_time")
        
        if metrics.task_success_rate < thresholds["task_success_rate"]:
            issues.append("low_task_success_rate")
        
        if metrics.error_rate > thresholds["error_rate"]:
            issues.append("high_error_rate")
        
        # 检测异常模式
        anomalies = await self._detect_metric_anomalies(metrics)
        issues.extend(anomalies)
        
        return issues

    async def _detect_metric_anomalies(self, metrics: AgentMetrics) -> List[str]:
        """检测指标异常"""
        anomalies = []
        agent_id = metrics.agent_id
        
        # 获取历史指标进行对比
        history = list(self.agent_metrics_history[agent_id])
        if len(history) < 5:  # 需要足够的历史数据
            return anomalies
        
        recent_metrics = history[-5:]
        
        # 检查CPU使用率异常
        cpu_values = [m.cpu_usage for m in recent_metrics]
        if self._is_statistical_anomaly(metrics.cpu_usage, cpu_values):
            anomalies.append("cpu_usage_anomaly")
        
        # 检查内存使用率异常
        memory_values = [m.memory_usage for m in recent_metrics]
        if self._is_statistical_anomaly(metrics.memory_usage, memory_values):
            anomalies.append("memory_usage_anomaly")
        
        # 检查响应时间异常
        response_values = [m.response_time for m in recent_metrics]
        if self._is_statistical_anomaly(metrics.response_time, response_values):
            anomalies.append("response_time_anomaly")
        
        return anomalies

    def _is_statistical_anomaly(self, value: float, historical_values: List[float]) -> bool:
        """检查统计异常"""
        if len(historical_values) < 3:
            return False
        
        mean = np.mean(historical_values)
        std = np.std(historical_values)
        
        if std == 0:
            return False
        
        z_score = abs(value - mean) / std
        return z_score > self.anomaly_detection_model["z_score_threshold"]

    async def _generate_health_recommendations(self, issues: List[str], metrics: AgentMetrics) -> List[str]:
        """生成健康建议"""
        recommendations = []
        
        for issue in issues:
            if issue == "high_cpu_usage":
                recommendations.append("Consider optimizing algorithms or reducing workload")
            elif issue == "high_memory_usage":
                recommendations.append("Review memory usage patterns and implement cleanup procedures")
            elif issue == "slow_response_time":
                recommendations.append("Optimize task processing and reduce blocking operations")
            elif issue == "low_task_success_rate":
                recommendations.append("Review error patterns and improve error handling")
            elif issue == "high_error_rate":
                recommendations.append("Implement better input validation and exception handling")
            elif issue == "cpu_usage_anomaly":
                recommendations.append("Investigate recent changes that may affect CPU usage")
            elif issue == "memory_usage_anomaly":
                recommendations.append("Check for memory leaks or unusual allocation patterns")
            elif issue == "response_time_anomaly":
                recommendations.append("Analyze recent performance degradation causes")
        
        if not issues and metrics.cpu_usage < 0.3 and metrics.memory_usage < 0.3:
            recommendations.append("System resources underutilized - consider taking on more tasks")
        
        return recommendations

    async def _update_agent_status(self, agent_id: str, health_check: HealthCheck):
        """更新智能体状态"""
        current_status = self.monitored_agents[agent_id]["status"]
        new_status = None
        
        if health_check.health_status == HealthStatus.CRITICAL:
            new_status = AgentStatus.ERROR
        elif health_check.health_status == HealthStatus.DEGRADED:
            new_status = AgentStatus.RECOVERING
        elif health_check.overall_score > 0.8:
            # 检查是否忙碌
            recent_metrics = list(self.agent_metrics_history[agent_id])
            if recent_metrics and recent_metrics[-1].cpu_usage > 0.6:
                new_status = AgentStatus.BUSY
            else:
                new_status = AgentStatus.ACTIVE
        else:
            new_status = AgentStatus.IDLE
        
        if new_status and new_status != current_status:
            self.monitored_agents[agent_id]["status"] = new_status
            self.logger.info(f"Agent {agent_id} status changed: {current_status.value} -> {new_status.value}")
            
            # 通知状态变化
            await self._notify_status_change(agent_id, current_status, new_status, health_check)

    async def _notify_status_change(self, agent_id: str, old_status: AgentStatus, new_status: AgentStatus, health_check: HealthCheck):
        """通知状态变化"""
        notification = {
            "agent_id": agent_id,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "health_score": health_check.overall_score,
            "health_status": health_check.health_status.value,
            "timestamp": time.time(),
            "action": "status_change"
        }
        
        await self.message_bus.send_message("system_monitoring", notification)

    async def _alert_monitoring_loop(self):
        """告警监控循环"""
        self.logger.info("Alert monitoring loop started")
        
        try:
            while True:
                alerts_triggered = 0
                
                # 检查所有监控智能体的告警条件
                for agent_id in list(self.monitored_agents.keys()):
                    if self.monitored_agents[agent_id].get("monitoring_enabled", True):
                        try:
                            new_alerts = await self._check_alert_conditions(agent_id)
                            for alert in new_alerts:
                                self.active_alerts[alert.alert_id] = alert
                                alerts_triggered += 1
                                
                                # 触发告警处理
                                await self._handle_alert(alert)
                        except Exception as e:
                            self.logger.error(f"Alert check failed for agent {agent_id}: {e}")
                
                self.monitoring_metrics["alerts_triggered"] += alerts_triggered
                
                if alerts_triggered > 0:
                    self.logger.info(f"Alert monitoring: {alerts_triggered} new alerts triggered")
                
                # 清理过期的告警
                await self._cleanup_expired_alerts()
                
                # 等待下一个检查周期
                await asyncio.sleep(self.monitoring_config["alert_check_interval"])
                
        except asyncio.CancelledError:
            self.logger.info("Alert monitoring loop stopped")
        except Exception as e:
            self.logger.error(f"Alert monitoring loop error: {e}")

    async def _check_alert_conditions(self, agent_id: str) -> List[PerformanceAlert]:
        """检查告警条件"""
        alerts = []
        
        # 获取最近指标
        recent_metrics = list(self.agent_metrics_history[agent_id])
        if not recent_metrics:
            return alerts
        
        latest_metrics = recent_metrics[-1]
        thresholds = self.monitoring_config["performance_thresholds"]
        
        # 检查CPU使用率告警
        if latest_metrics.cpu_usage > thresholds["cpu_usage"]:
            alert = PerformanceAlert(
                alert_id=f"alert_cpu_{agent_id}_{int(time.time())}",
                agent_id=agent_id,
                alert_type="high_cpu_usage",
                severity="warning" if latest_metrics.cpu_usage < 0.9 else "critical",
                description=f"High CPU usage detected: {latest_metrics.cpu_usage:.1%}",
                triggered_value=latest_metrics.cpu_usage,
                threshold=thresholds["cpu_usage"],
                timestamp=time.time()
            )
            alerts.append(alert)
        
        # 检查内存使用率告警
        if latest_metrics.memory_usage > thresholds["memory_usage"]:
            alert = PerformanceAlert(
                alert_id=f"alert_memory_{agent_id}_{int(time.time())}",
                agent_id=agent_id,
                alert_type="high_memory_usage",
                severity="warning" if latest_metrics.memory_usage < 0.9 else "critical",
                description=f"High memory usage detected: {latest_metrics.memory_usage:.1%}",
                triggered_value=latest_metrics.memory_usage,
                threshold=thresholds["memory_usage"],
                timestamp=time.time()
            )
            alerts.append(alert)
        
        # 检查响应时间告警
        if latest_metrics.response_time > thresholds["response_time"]:
            alert = PerformanceAlert(
                alert_id=f"alert_response_{agent_id}_{int(time.time())}",
                agent_id=agent_id,
                alert_type="slow_response_time",
                severity="warning",
                description=f"Slow response time detected: {latest_metrics.response_time:.2f}s",
                triggered_value=latest_metrics.response_time,
                threshold=thresholds["response_time"],
                timestamp=time.time()
            )
            alerts.append(alert)
        
        # 检查错误率告警
        if latest_metrics.error_rate > thresholds["error_rate"]:
            alert = PerformanceAlert(
                alert_id=f"alert_error_{agent_id}_{int(time.time())}",
                agent_id=agent_id,
                alert_type="high_error_rate",
                severity="critical",
                description=f"High error rate detected: {latest_metrics.error_rate:.1%}",
                triggered_value=latest_metrics.error_rate,
                threshold=thresholds["error_rate"],
                timestamp=time.time()
            )
            alerts.append(alert)
        
        # 检查健康状态告警
        health_check = self.health_check_results.get(agent_id)
        if health_check and health_check.health_status == HealthStatus.CRITICAL:
            alert = PerformanceAlert(
                alert_id=f"alert_health_{agent_id}_{int(time.time())}",
                agent_id=agent_id,
                alert_type="critical_health",
                severity="critical",
                description=f"Critical health status detected: score {health_check.overall_score:.2f}",
                triggered_value=health_check.overall_score,
                threshold=self.health_assessment_model["critical_threshold"],
                timestamp=time.time()
            )
            alerts.append(alert)
        
        return alerts

    async def _handle_alert(self, alert: PerformanceAlert):
        """处理告警"""
        self.logger.warning(f"Performance alert triggered: {alert.alert_type} for agent {alert.agent_id} "
                          f"(severity: {alert.severity})")
        
        # 发送告警通知
        alert_notification = {
            "alert_id": alert.alert_id,
            "agent_id": alert.agent_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "description": alert.description,
            "triggered_value": alert.triggered_value,
            "threshold": alert.threshold,
            "timestamp": alert.timestamp,
            "action": "performance_alert"
        }
        
        await self.message_bus.send_message("system_alerts", alert_notification)
        
        # 根据严重程度采取不同措施
        if alert.severity == "critical":
            # 紧急措施：暂停智能体或触发恢复流程
            await self._handle_critical_alert(alert)
        elif alert.severity == "warning":
            # 警告措施：记录并监控
            await self._handle_warning_alert(alert)

    async def _handle_critical_alert(self, alert: PerformanceAlert):
        """处理严重告警"""
        agent_id = alert.agent_id
        
        # 暂停智能体活动
        self.monitored_agents[agent_id]["monitoring_enabled"] = False
        
        # 触发恢复流程
        recovery_notification = {
            "agent_id": agent_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "action": "initiate_recovery"
        }
        
        await self.message_bus.send_message(f"agent_{agent_id}_recovery", recovery_notification)
        
        self.logger.info(f"Recovery initiated for agent {agent_id} due to critical alert")

    async def _handle_warning_alert(self, alert: PerformanceAlert):
        """处理警告告警"""
        # 记录警告并继续监控
        self.logger.info(f"Warning alert recorded for agent {alert.agent_id}: {alert.description}")

    async def _cleanup_expired_alerts(self):
        """清理过期告警"""
        current_time = time.time()
        expired_alerts = []
        
        for alert_id, alert in self.active_alerts.items():
            # 告警保留24小时
            if current_time - alert.timestamp > 86400:
                expired_alerts.append(alert_id)
        
        for alert_id in expired_alerts:
            del self.active_alerts[alert_id]
        
        if expired_alerts:
            self.logger.debug(f"Cleaned up {len(expired_alerts)} expired alerts")

    async def get_agent_health_report(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取智能体健康报告"""
        if agent_id not in self.monitored_agents:
            return None
        
        health_check = self.health_check_results.get(agent_id)
        recent_metrics = list(self.agent_metrics_history[agent_id])
        
        if not health_check or not recent_metrics:
            return None
        
        latest_metrics = recent_metrics[-1]
        
        report = {
            "agent_id": agent_id,
            "current_status": self.monitored_agents[agent_id]["status"].value,
            "health_status": health_check.health_status.value,
            "overall_health_score": health_check.overall_score,
            "last_health_check": health_check.check_timestamp,
            "current_metrics": {
                "cpu_usage": latest_metrics.cpu_usage,
                "memory_usage": latest_metrics.memory_usage,
                "response_time": latest_metrics.response_time,
                "task_success_rate": latest_metrics.task_success_rate,
                "error_rate": latest_metrics.error_rate,
                "communication_volume": latest_metrics.communication_volume
            },
            "issues_detected": health_check.issues_detected,
            "recommendations": health_check.recommendations,
            "active_alerts": [alert.__dict__ for alert in self.active_alerts.values() 
                            if alert.agent_id == agent_id]
        }
        
        return report

    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        status_distribution = defaultdict(int)
        health_distribution = defaultdict(int)
        
        for agent_info in self.monitored_agents.values():
            status_distribution[agent_info["status"].value] += 1
        
        for health_check in self.health_check_results.values():
            health_distribution[health_check.health_status.value] += 1
        
        return {
            **self.monitoring_metrics,
            "status_distribution": dict(status_distribution),
            "health_distribution": dict(health_distribution),
            "active_alerts_count": len(self.active_alerts),
            "alerts_by_severity": {
                "critical": len([a for a in self.active_alerts.values() if a.severity == "critical"]),
                "warning": len([a for a in self.active_alerts.values() if a.severity == "warning"])
            }
        }

    async def set_monitoring_config(self, config_updates: Dict[str, Any]):
        """更新监控配置"""
        self.monitoring_config.update(config_updates)
        self.logger.info("Monitoring configuration updated")

    async def cleanup(self):
        """清理资源"""
        self.logger.info("Cleaning up AgentMonitor...")
        
        await self.stop_monitoring()
        
        # 保存监控历史到记忆系统
        for agent_id, metrics_history in self.agent_metrics_history.items():
            await self.episodic_memory.record_agent_metrics_history(agent_id, list(metrics_history))
        
        for agent_id, health_check in self.health_check_results.items():
            await self.episodic_memory.record_health_check_result(agent_id, health_check)
        
        self.logger.info("AgentMonitor cleanup completed")

