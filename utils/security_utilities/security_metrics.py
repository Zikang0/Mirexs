"""
安全指标模块

提供安全相关的指标计算、监控和报告功能
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics
from collections import defaultdict, Counter

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecurityEventType(Enum):
    """安全事件类型枚举"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PERMISSION_CHANGE = "permission_change"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKE = "token_revoke"
    API_ACCESS = "api_access"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_VIOLATION = "security_violation"


class SecurityLevel(Enum):
    """安全级别枚举"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """安全事件数据类"""
    event_type: SecurityEventType
    timestamp: datetime
    user_id: Optional[str]
    ip_address: Optional[str]
    details: Dict[str, Any]
    level: SecurityLevel
    source: str


@dataclass
class SecurityMetrics:
    """安全指标数据类"""
    total_events: int
    events_by_type: Dict[str, int]
    events_by_level: Dict[str, int]
    unique_users: int
    failed_logins: int
    successful_logins: int
    suspicious_activities: int
    rate_limit_exceeded: int
    average_response_time: float
    security_score: float


class SecurityMetricsCollector:
    """安全指标收集器"""
    
    def __init__(self):
        """初始化安全指标收集器"""
        self.events: List[SecurityEvent] = []
        self.start_time = datetime.now()
        self.metrics_history: Dict[str, List[float]] = defaultdict(list)
        self.user_activity: Dict[str, List[datetime]] = defaultdict(list)
        self.ip_activity: Dict[str, List[datetime]] = defaultdict(list)
        
    def record_event(self, event_type: SecurityEventType, 
                    user_id: Optional[str] = None,
                    ip_address: Optional[str] = None,
                    details: Optional[Dict[str, Any]] = None,
                    level: SecurityLevel = SecurityLevel.INFO,
                    source: str = "system") -> None:
        """记录安全事件
        
        Args:
            event_type: 事件类型
            user_id: 用户ID
            ip_address: IP地址
            details: 详细信息
            level: 安全级别
            source: 事件来源
        """
        event = SecurityEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            user_id=user_id,
            ip_address=ip_address,
            details=details or {},
            level=level,
            source=source
        )
        
        self.events.append(event)
        
        # 记录用户活动
        if user_id:
            self.user_activity[user_id].append(event.timestamp)
            
        # 记录IP活动
        if ip_address:
            self.ip_activity[ip_address].append(event.timestamp)
            
        # 记录指标
        self.metrics_history[event_type.value].append(1)
        
        # 日志记录
        log_level = {
            SecurityLevel.INFO: logging.INFO,
            SecurityLevel.LOW: logging.INFO,
            SecurityLevel.MEDIUM: logging.WARNING,
            SecurityLevel.HIGH: logging.ERROR,
            SecurityLevel.CRITICAL: logging.CRITICAL
        }.get(level, logging.INFO)
        
        logger.log(log_level, 
                   f"安全事件: {event_type.value}, 用户: {user_id}, IP: {ip_address}, 级别: {level.value}")
        
    def get_metrics(self, hours: int = 24) -> SecurityMetrics:
        """获取安全指标
        
        Args:
            hours: 时间范围（小时）
            
        Returns:
            SecurityMetrics: 安全指标
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_events = [e for e in self.events if e.timestamp >= cutoff_time]
        
        # 计算各类型事件数量
        events_by_type = Counter(e.event_type.value for e in recent_events)
        
        # 计算各级别事件数量
        events_by_level = Counter(e.level.value for e in recent_events)
        
        # 计算登录统计
        failed_logins = sum(1 for e in recent_events 
                           if e.event_type == SecurityEventType.LOGIN_FAILURE)
        successful_logins = sum(1 for e in recent_events 
                               if e.event_type == SecurityEventType.LOGIN_SUCCESS)
        
        # 计算可疑活动
        suspicious = sum(1 for e in recent_events 
                        if e.event_type == SecurityEventType.SUSPICIOUS_ACTIVITY)
        
        # 计算限流超限
        rate_limit = sum(1 for e in recent_events 
                        if e.event_type == SecurityEventType.RATE_LIMIT_EXCEEDED)
        
        # 计算唯一用户
        unique_users = len(set(e.user_id for e in recent_events if e.user_id))
        
        # 计算平均响应时间（如果有API访问事件）
        api_events = [e for e in recent_events 
                     if e.event_type == SecurityEventType.API_ACCESS]
        response_times = [e.details.get('response_time', 0) for e in api_events]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        # 计算安全分数
        security_score = self._calculate_security_score(recent_events)
        
        return SecurityMetrics(
            total_events=len(recent_events),
            events_by_type=dict(events_by_type),
            events_by_level=dict(events_by_level),
            unique_users=unique_users,
            failed_logins=failed_logins,
            successful_logins=successful_logins,
            suspicious_activities=suspicious,
            rate_limit_exceeded=rate_limit,
            average_response_time=avg_response_time,
            security_score=security_score
        )
        
    def _calculate_security_score(self, events: List[SecurityEvent]) -> float:
        """计算安全分数
        
        Args:
            events: 安全事件列表
            
        Returns:
            float: 安全分数（0-100）
        """
        if not events:
            return 100.0
            
        score = 100.0
        
        # 根据事件级别扣分
        level_weights = {
            SecurityLevel.INFO: 0,
            SecurityLevel.LOW: 1,
            SecurityLevel.MEDIUM: 5,
            SecurityLevel.HIGH: 10,
            SecurityLevel.CRITICAL: 20
        }
        
        for event in events:
            score -= level_weights.get(event.level, 0)
            
        # 登录失败扣分
        failed_logins = sum(1 for e in events 
                           if e.event_type == SecurityEventType.LOGIN_FAILURE)
        score -= failed_logins * 0.5
        
        # 可疑活动扣分
        suspicious = sum(1 for e in events 
                        if e.event_type == SecurityEventType.SUSPICIOUS_ACTIVITY)
        score -= suspicious * 3
        
        return max(0, min(100, score))
        
    def get_user_risk_score(self, user_id: str, hours: int = 24) -> float:
        """获取用户风险分数
        
        Args:
            user_id: 用户ID
            hours: 时间范围（小时）
            
        Returns:
            float: 风险分数（0-100，越高越危险）
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        user_events = [e for e in self.events 
                      if e.user_id == user_id and e.timestamp >= cutoff_time]
        
        if not user_events:
            return 0.0
            
        risk_score = 0.0
        
        for event in user_events:
            if event.event_type == SecurityEventType.LOGIN_FAILURE:
                risk_score += 5
            elif event.event_type == SecurityEventType.SUSPICIOUS_ACTIVITY:
                risk_score += 10
            elif event.event_type == SecurityEventType.SECURITY_VIOLATION:
                risk_score += 20
            elif event.event_type == SecurityEventType.RATE_LIMIT_EXCEEDED:
                risk_score += 3
                
        return min(100, risk_score)
        
    def get_ip_risk_score(self, ip_address: str, hours: int = 24) -> float:
        """获取IP风险分数
        
        Args:
            ip_address: IP地址
            hours: 时间范围（小时）
            
        Returns:
            float: 风险分数（0-100，越高越危险）
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        ip_events = [e for e in self.events 
                    if e.ip_address == ip_address and e.timestamp >= cutoff_time]
        
        if not ip_events:
            return 0.0
            
        risk_score = 0.0
        
        for event in ip_events:
            if event.event_type == SecurityEventType.LOGIN_FAILURE:
                risk_score += 5
            elif event.event_type == SecurityEventType.SUSPICIOUS_ACTIVITY:
                risk_score += 10
            elif event.event_type == SecurityEventType.SECURITY_VIOLATION:
                risk_score += 20
            elif event.event_type == SecurityEventType.RATE_LIMIT_EXCEEDED:
                risk_score += 3
                
        return min(100, risk_score)
        
    def get_anomaly_detection(self) -> Dict[str, Any]:
        """异常检测
        
        Returns:
            Dict[str, Any]: 异常检测结果
        """
        anomalies = []
        
        # 检测异常登录频率
        for user_id, activities in self.user_activity.items():
            recent = [a for a in activities if a > datetime.now() - timedelta(minutes=5)]
            if len(recent) > 10:
                anomalies.append({
                    'type': 'high_login_frequency',
                    'user_id': user_id,
                    'count': len(recent),
                    'timeframe': '5 minutes'
                })
                
        # 检测IP异常行为
        for ip, activities in self.ip_activity.items():
            recent = [a for a in activities if a > datetime.now() - timedelta(minutes=5)]
            if len(recent) > 20:
                anomalies.append({
                    'type': 'high_request_frequency',
                    'ip': ip,
                    'count': len(recent),
                    'timeframe': '5 minutes'
                })
                
        # 检测失败登录模式
        failed_events = [e for e in self.events 
                        if e.event_type == SecurityEventType.LOGIN_FAILURE
                        and e.timestamp > datetime.now() - timedelta(minutes=10)]
        
        if len(failed_events) > 5:
            anomalies.append({
                'type': 'multiple_failed_logins',
                'count': len(failed_events),
                'timeframe': '10 minutes'
            })
            
        return {
            'anomalies': anomalies,
            'anomaly_count': len(anomalies),
            'timestamp': datetime.now().isoformat()
        }
        
    def generate_report(self, hours: int = 24) -> Dict[str, Any]:
        """生成安全报告
        
        Args:
            hours: 时间范围（小时）
            
        Returns:
            Dict[str, Any]: 安全报告
        """
        metrics = self.get_metrics(hours)
        anomalies = self.get_anomaly_detection()
        
        # 获取高风险用户
        high_risk_users = []
        for user_id in self.user_activity.keys():
            risk_score = self.get_user_risk_score(user_id, hours)
            if risk_score > 50:
                high_risk_users.append({
                    'user_id': user_id,
                    'risk_score': risk_score
                })
                
        # 获取高风险IP
        high_risk_ips = []
        for ip in self.ip_activity.keys():
            risk_score = self.get_ip_risk_score(ip, hours)
            if risk_score > 50:
                high_risk_ips.append({
                    'ip': ip,
                    'risk_score': risk_score
                })
                
        return {
            'report_time': datetime.now().isoformat(),
            'time_range_hours': hours,
            'metrics': {
                'total_events': metrics.total_events,
                'events_by_type': metrics.events_by_type,
                'events_by_level': metrics.events_by_level,
                'unique_users': metrics.unique_users,
                'failed_logins': metrics.failed_logins,
                'successful_logins': metrics.successful_logins,
                'suspicious_activities': metrics.suspicious_activities,
                'rate_limit_exceeded': metrics.rate_limit_exceeded,
                'security_score': metrics.security_score
            },
            'anomalies': anomalies,
            'high_risk_users': sorted(high_risk_users, 
                                     key=lambda x: x['risk_score'], 
                                     reverse=True)[:10],
            'high_risk_ips': sorted(high_risk_ips, 
                                   key=lambda x: x['risk_score'], 
                                   reverse=True)[:10]
        }


class SecurityDashboard:
    """安全仪表板"""
    
    def __init__(self, collector: SecurityMetricsCollector):
        """初始化安全仪表板
        
        Args:
            collector: 安全指标收集器
        """
        self.collector = collector
        
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据
        
        Returns:
            Dict[str, Any]: 仪表板数据
        """
        # 获取不同时间范围的指标
        hourly = self.collector.get_metrics(1)
        daily = self.collector.get_metrics(24)
        weekly = self.collector.get_metrics(168)
        
        # 获取异常检测结果
        anomalies = self.collector.get_anomaly_detection()
        
        # 获取趋势数据
        trend_data = self._get_trend_data()
        
        return {
            'current': {
                'security_score': daily.security_score,
                'active_events': hourly.total_events,
                'suspicious_activities': hourly.suspicious_activities,
                'failed_logins': hourly.failed_logins
            },
            'hourly': {
                'total_events': hourly.total_events,
                'failed_logins': hourly.failed_logins,
                'security_score': hourly.security_score
            },
            'daily': {
                'total_events': daily.total_events,
                'failed_logins': daily.failed_logins,
                'security_score': daily.security_score
            },
            'weekly': {
                'total_events': weekly.total_events,
                'failed_logins': weekly.failed_logins,
                'security_score': weekly.security_score
            },
            'anomalies': anomalies,
            'trends': trend_data,
            'timestamp': datetime.now().isoformat()
        }
        
    def _get_trend_data(self) -> Dict[str, List[Any]]:
        """获取趋势数据
        
        Returns:
            Dict[str, List[Any]]: 趋势数据
        """
        # 按小时分组
        hourly_data = defaultdict(lambda: {'events': 0, 'failed_logins': 0})
        
        for event in self.collector.events:
            hour_key = event.timestamp.strftime('%Y-%m-%d %H:00')
            hourly_data[hour_key]['events'] += 1
            if event.event_type == SecurityEventType.LOGIN_FAILURE:
                hourly_data[hour_key]['failed_logins'] += 1
                
        # 转换为列表
        hours = sorted(hourly_data.keys())[-24:]  # 最近24小时
        
        return {
            'hours': hours,
            'events': [hourly_data[h]['events'] for h in hours],
            'failed_logins': [hourly_data[h]['failed_logins'] for h in hours]
        }


# 全局安全指标收集器实例
security_collector = SecurityMetricsCollector()


def record_security_event(event_type: SecurityEventType,
                         user_id: Optional[str] = None,
                         ip_address: Optional[str] = None,
                         details: Optional[Dict[str, Any]] = None,
                         level: SecurityLevel = SecurityLevel.INFO,
                         source: str = "system") -> None:
    """记录安全事件便捷函数"""
    security_collector.record_event(event_type, user_id, ip_address, details, level, source)


def get_security_metrics(hours: int = 24) -> SecurityMetrics:
    """获取安全指标便捷函数"""
    return security_collector.get_metrics(hours)


def get_user_risk_score(user_id: str, hours: int = 24) -> float:
    """获取用户风险分数便捷函数"""
    return security_collector.get_user_risk_score(user_id, hours)


def get_ip_risk_score(ip_address: str, hours: int = 24) -> float:
    """获取IP风险分数便捷函数"""
    return security_collector.get_ip_risk_score(ip_address, hours)


def generate_security_report(hours: int = 24) -> Dict[str, Any]:
    """生成安全报告便捷函数"""
    return security_collector.generate_report(hours)


def get_security_dashboard() -> Dict[str, Any]:
    """获取安全仪表板数据便捷函数"""
    dashboard = SecurityDashboard(security_collector)
    return dashboard.get_dashboard_data()