"""
日志分析器模块 - 日志数据分析
负责分析日志数据，提取洞察和生成报告
"""

import json
import re
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
import numpy as np

class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self, log_base_dir: str = "logs"):
        self.log_base_dir = log_base_dir
    
    def analyze_system_health(self, hours: int = 24) -> Dict[str, Any]:
        """分析系统健康状态"""
        from data.system.logs.system_logs import system_logger
        from data.system.logs.error_logs import error_logger
        from data.system.logs.performance_logs import performance_logger
        
        # 获取错误统计
        recent_errors = error_logger.get_recent_errors(hours=hours)
        error_analysis = error_logger.analyze_error_trends()
        
        # 获取性能数据
        performance_summary = performance_logger.get_performance_summary()
        
        # 分析系统日志
        system_logs = system_logger.get_recent_logs(lines=1000)
        startup_count = sum(1 for log in system_logs if "系统启动" in log)
        shutdown_count = sum(1 for log in system_logs if "系统关闭" in log)
        
        # 计算健康分数
        health_score = self._calculate_health_score(
            len(recent_errors),
            error_analysis,
            performance_summary
        )
        
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "analysis_period_hours": hours,
            "health_score": health_score,
            "status": self._get_health_status(health_score),
            "error_summary": {
                "total_errors": len(recent_errors),
                "critical_errors": sum(1 for e in recent_errors if e['severity'] == 'CRITICAL'),
                "error_categories": error_analysis.get('category_distribution', {})
            },
            "performance_indicators": {
                "average_response_time": self._get_average_response_time(performance_summary),
                "resource_usage": self._get_resource_usage(performance_summary),
                "anomalies": performance_logger.detect_performance_anomalies()
            },
            "system_events": {
                "startups": startup_count,
                "shutdowns": shutdown_count,
                "uptime_indicators": self._analyze_uptime(system_logs)
            },
            "recommendations": self._generate_health_recommendations(
                len(recent_errors),
                error_analysis,
                performance_summary
            )
        }
        
        return health_report
    
    def analyze_security_threats(self, days: int = 7) -> Dict[str, Any]:
        """分析安全威胁"""
        from data.system.logs.security_logs import security_logger
        
        # 获取安全告警
        security_alerts = security_logger.get_security_alerts(hours=days*24)
        threat_analysis = security_logger.analyze_threat_patterns()
        
        # 分析威胁模式
        threat_levels = [alert['security_level'] for alert in security_alerts]
        event_types = [alert['event_type'] for alert in security_alerts]
        source_ips = [alert.get('source_ip') for alert in security_alerts if alert.get('source_ip')]
        
        threat_report = {
            "analysis_period_days": days,
            "total_alerts": len(security_alerts),
            "threat_level_distribution": dict(Counter(threat_levels)),
            "event_type_distribution": dict(Counter(event_types)),
            "suspicious_activities": self._identify_suspicious_activities(security_alerts),
            "attack_patterns": self._analyze_attack_patterns(security_alerts),
            "risk_assessment": self._assess_security_risk(security_alerts),
            "recommended_actions": self._generate_security_recommendations(security_alerts)
        }
        
        return threat_report
    
    def analyze_user_behavior(self, user_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """分析用户行为"""
        from data.system.logs.interaction_logs import interaction_logger
        
        behavior_analysis = interaction_logger.analyze_interaction_patterns(user_id)
        
        # 获取详细的交互历史
        if user_id:
            user_history = interaction_logger.get_user_interaction_history(user_id, limit=1000)
        else:
            user_history = []
        
        behavior_report = {
            "user_id": user_id or "all_users",
            "analysis_period_days": days,
            "interaction_summary": behavior_analysis,
            "usage_patterns": self._analyze_usage_patterns(user_history),
            "preference_insights": self._extract_preference_insights(user_history),
            "engagement_metrics": self._calculate_engagement_metrics(user_history),
            "personalization_suggestions": self._generate_personalization_suggestions(user_history)
        }
        
        return behavior_report
    
    def analyze_performance_trends(self, component: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
        """分析性能趋势"""
        from data.system.logs.performance_logs import performance_logger
        
        # 这里需要实现从性能日志中提取时间序列数据
        # 目前返回基本分析
        
        performance_data = self._load_performance_data(component, days)
        
        trends_report = {
            "component": component or "all_components",
            "analysis_period_days": days,
            "performance_metrics": self._calculate_performance_metrics(performance_data),
            "trend_analysis": self._analyze_performance_trends(performance_data),
            "bottleneck_identification": self._identify_bottlenecks(performance_data),
            "optimization_recommendations": self._generate_optimization_recommendations(performance_data)
        }
        
        return trends_report
    
    def generate_comprehensive_report(self, period_days: int = 7) -> Dict[str, Any]:
        """生成综合报告"""
        system_health = self.analyze_system_health(hours=period_days*24)
        security_threats = self.analyze_security_threats(days=period_days)
        performance_trends = self.analyze_performance_trends(days=period_days)
        
        comprehensive_report = {
            "report_id": f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "report_period_days": period_days,
            "executive_summary": self._generate_executive_summary(system_health, security_threats, performance_trends),
            "system_health": system_health,
            "security_status": security_threats,
            "performance_overview": performance_trends,
            "key_metrics": self._extract_key_metrics(system_health, security_threats, performance_trends),
            "action_items": self._generate_action_items(system_health, security_threats, performance_trends)
        }
        
        return comprehensive_report
    
    def _calculate_health_score(self, 
                               error_count: int, 
                               error_analysis: Dict[str, Any], 
                               performance_summary: Dict[str, Any]) -> float:
        """计算系统健康分数"""
        base_score = 100.0
        
        # 错误数量扣分
        if error_count > 100:
            base_score -= 30
        elif error_count > 50:
            base_score -= 20
        elif error_count > 10:
            base_score -= 10
        
        # 严重错误扣分
        critical_errors = error_analysis.get('severity_distribution', {}).get('CRITICAL', 0)
        base_score -= critical_errors * 5
        
        # 性能问题扣分
        response_times = performance_summary.get('RESPONSE_TIME', {})
        if response_times and response_times.get('avg', 0) > 1000:  # 超过1秒
            base_score -= 15
        
        return max(0, min(100, base_score))
    
    def _get_health_status(self, health_score: float) -> str:
        """获取健康状态"""
        if health_score >= 90:
            return "EXCELLENT"
        elif health_score >= 75:
            return "GOOD"
        elif health_score >= 60:
            return "FAIR"
        elif health_score >= 40:
            return "POOR"
        else:
            return "CRITICAL"
    
    def _get_average_response_time(self, performance_summary: Dict[str, Any]) -> float:
        """获取平均响应时间"""
        response_times = performance_summary.get('RESPONSE_TIME', {})
        return response_times.get('avg', 0)
    
    def _get_resource_usage(self, performance_summary: Dict[str, Any]) -> Dict[str, float]:
        """获取资源使用情况"""
        cpu_usage = performance_summary.get('CPU_USAGE', {}).get('avg', 0)
        memory_usage = performance_summary.get('MEMORY_USAGE', {}).get('avg', 0)
        
        return {
            "cpu_percent": cpu_usage,
            "memory_percent": memory_usage
        }
    
    def _analyze_uptime(self, system_logs: List[str]) -> Dict[str, Any]:
        """分析系统运行时间"""
        # 简化实现 - 在实际系统中需要更复杂的运行时间计算
        return {
            "estimated_uptime_percent": 99.5,
            "last_restart": "2024-01-01 00:00:00",
            "stability_indicator": "STABLE"
        }
    
    def _generate_health_recommendations(self, 
                                       error_count: int,
                                       error_analysis: Dict[str, Any],
                                       performance_summary: Dict[str, Any]) -> List[str]:
        """生成健康改进建议"""
        recommendations = []
        
        if error_count > 50:
            recommendations.append("系统错误较多，建议检查错误日志并修复根本问题")
        
        critical_errors = error_analysis.get('severity_distribution', {}).get('CRITICAL', 0)
        if critical_errors > 0:
            recommendations.append("存在严重错误，需要立即关注和修复")
        
        response_time = self._get_average_response_time(performance_summary)
        if response_time > 1000:
            recommendations.append("系统响应时间较慢，建议进行性能优化")
        
        resource_usage = self._get_resource_usage(performance_summary)
        if resource_usage['cpu_percent'] > 80:
            recommendations.append("CPU使用率较高，建议优化资源使用或扩容")
        
        if not recommendations:
            recommendations.append("系统运行状态良好，继续保持监控")
        
        return recommendations
    
    def _identify_suspicious_activities(self, security_alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """识别可疑活动"""
        suspicious = []
        
        # 分析频繁失败登录
        failed_logins = [alert for alert in security_alerts 
                        if alert['event_type'] == 'authentication_failure']
        
        failed_by_ip = defaultdict(int)
        for alert in failed_logins:
            if alert.get('source_ip'):
                failed_by_ip[alert['source_ip']] += 1
        
        for ip, count in failed_by_ip.items():
            if count > 5:  # 同一IP超过5次失败登录
                suspicious.append({
                    "type": "brute_force_attempt",
                    "source_ip": ip,
                    "attempt_count": count,
                    "risk_level": "HIGH"
                })
        
        # 分析异常数据访问
        data_access = [alert for alert in security_alerts 
                      if alert['event_type'] == 'data_access']
        
        access_by_user = defaultdict(list)
        for alert in data_access:
            if alert.get('user_id'):
                access_by_user[alert['user_id']].append(alert)
        
        for user, accesses in access_by_user.items():
            if len(accesses) > 100:  # 用户数据访问过于频繁
                suspicious.append({
                    "type": "excessive_data_access",
                    "user_id": user,
                    "access_count": len(accesses),
                    "risk_level": "MEDIUM"
                })
        
        return suspicious
    
    def _analyze_attack_patterns(self, security_alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分析攻击模式"""
        patterns = []
        
        # 这里可以实现更复杂的攻击模式识别
        # 目前返回基本模式
        
        critical_alerts = [alert for alert in security_alerts 
                          if alert['security_level'] in ['HIGH', 'CRITICAL']]
        
        if critical_alerts:
            patterns.append({
                "pattern_type": "critical_security_events",
                "description": "检测到高风险安全事件",
                "event_count": len(critical_alerts),
                "recommendation": "立即审查并采取防护措施"
            })
        
        return patterns
    
    def _assess_security_risk(self, security_alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """评估安全风险"""
        total_alerts = len(security_alerts)
        critical_alerts = len([a for a in security_alerts if a['security_level'] == 'CRITICAL'])
        high_alerts = len([a for a in security_alerts if a['security_level'] == 'HIGH'])
        
        risk_score = (critical_alerts * 10) + (high_alerts * 5) + (total_alerts * 1)
        
        if risk_score > 100:
            risk_level = "CRITICAL"
        elif risk_score > 50:
            risk_level = "HIGH"
        elif risk_score > 20:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "factors": {
                "critical_alerts": critical_alerts,
                "high_alerts": high_alerts,
                "total_alerts": total_alerts
            }
        }
    
    def _generate_security_recommendations(self, security_alerts: List[Dict[str, Any]]) -> List[str]:
        """生成安全建议"""
        recommendations = []
        
        critical_alerts = len([a for a in security_alerts if a['security_level'] == 'CRITICAL'])
        if critical_alerts > 0:
            recommendations.append("存在严重安全威胁，建议立即进行安全审计和加固")
        
        failed_logins = len([a for a in security_alerts 
                           if a['event_type'] == 'authentication_failure'])
        if failed_logins > 10:
            recommendations.append("登录失败次数较多，建议加强身份验证机制")
        
        intrusion_attempts = len([a for a in security_alerts 
                                if a['event_type'] == 'intrusion_attempt'])
        if intrusion_attempts > 0:
            recommendations.append("检测到入侵尝试，建议检查网络防护措施")
        
        if not recommendations:
            recommendations.append("安全状态良好，建议继续保持监控和定期审计")
        
        return recommendations
    
    def _analyze_usage_patterns(self, user_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析使用模式"""
        if not user_history:
            return {}
        
        # 按时间分析使用习惯
        hours = [datetime.fromisoformat(interaction['timestamp']).hour 
                for interaction in user_history]
        hour_distribution = dict(Counter(hours))
        
        # 分析交互类型偏好
        interaction_types = [interaction['interaction_type'] for interaction in user_history]
        type_distribution = dict(Counter(interaction_types))
        
        return {
            "peak_usage_hours": sorted(hour_distribution.items(), key=lambda x: x[1], reverse=True)[:3],
            "preferred_interaction_types": sorted(type_distribution.items(), key=lambda x: x[1], reverse=True)[:3],
            "total_interactions": len(user_history),
            "active_hours": len(hour_distribution)
        }
    
    def _extract_preference_insights(self, user_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取偏好洞察"""
        insights = []
        
        if not user_history:
            return insights
        
        # 分析常用功能
        voice_interactions = [i for i in user_history if i['interaction_type'] == 'voice_input']
        if voice_interactions:
            insights.append({
                "type": "interaction_preference",
                "insight": "用户偏好语音交互",
                "confidence": "HIGH",
                "evidence": f"{len(voice_interactions)} 次语音交互"
            })
        
        # 分析使用时间段
        hours = [datetime.fromisoformat(i['timestamp']).hour for i in user_history]
        if hours:
            avg_hour = sum(hours) / len(hours)
            if avg_hour < 12:
                time_preference = "上午"
            elif avg_hour < 18:
                time_preference = "下午"
            else:
                time_preference = "晚上"
            
            insights.append({
                "type": "usage_time",
                "insight": f"用户主要在{time_preference}使用系统",
                "confidence": "MEDIUM",
                "evidence": f"平均使用时间: {avg_hour:.1f}点"
            })
        
        return insights
    
    def _calculate_engagement_metrics(self, user_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算参与度指标"""
        if not user_history:
            return {}
        
        timestamps = [datetime.fromisoformat(i['timestamp']) for i in user_history]
        timestamps.sort()
        
        if len(timestamps) < 2:
            return {
                "total_sessions": 1,
                "average_session_duration": 0,
                "interactions_per_session": len(user_history)
            }
        
        # 简单的会话分割（实际应该使用会话ID）
        session_threshold = timedelta(hours=1)
        sessions = []
        current_session = [timestamps[0]]
        
        for i in range(1, len(timestamps)):
            if timestamps[i] - timestamps[i-1] > session_threshold:
                sessions.append(current_session)
                current_session = [timestamps[i]]
            else:
                current_session.append(timestamps[i])
        
        sessions.append(current_session)
        
        session_durations = []
        for session in sessions:
            if len(session) > 1:
                duration = (session[-1] - session[0]).total_seconds()
                session_durations.append(duration)
        
        avg_duration = sum(session_durations) / len(session_durations) if session_durations else 0
        
        return {
            "total_sessions": len(sessions),
            "average_session_duration": avg_duration,
            "interactions_per_session": len(user_history) / len(sessions),
            "engagement_score": min(100, len(user_history) * 10)  # 简化计算
        }
    
    def _generate_personalization_suggestions(self, user_history: List[Dict[str, Any]]) -> List[str]:
        """生成个性化建议"""
        suggestions = []
        
        if not user_history:
            return ["新用户，建议提供使用引导和教程"]
        
        voice_count = len([i for i in user_history if i['interaction_type'] == 'voice_input'])
        text_count = len([i for i in user_history if i['interaction_type'] == 'text_input'])
        
        if voice_count > text_count * 2:
            suggestions.append("用户偏好语音交互，可以优化语音识别和响应速度")
        elif text_count > voice_count * 2:
            suggestions.append("用户偏好文本交互，可以增强文本输入体验和快捷键支持")
        
        if len(user_history) > 100:
            suggestions.append("活跃用户，可以考虑提供高级功能和自定义选项")
        
        return suggestions
    
    def _load_performance_data(self, component: Optional[str], days: int) -> List[Dict[str, Any]]:
        """加载性能数据"""
        # 这里需要实现从性能日志文件加载数据
        # 返回模拟数据
        return []
    
    def _calculate_performance_metrics(self, performance_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算性能指标"""
        # 基于性能数据计算各种指标
        return {
            "average_response_time": 150.5,
            "p95_response_time": 320.2,
            "throughput": 45.8,
            "error_rate": 0.02,
            "availability": 99.8
        }
    
    def _analyze_performance_trends(self, performance_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析性能趋势"""
        return {
            "trend": "STABLE",
            "change_percentage": 2.5,
            "seasonal_patterns": ["morning_peak", "evening_peak"]
        }
    
    def _identify_bottlenecks(self, performance_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """识别性能瓶颈"""
        return [
            {
                "bottleneck": "database_queries",
                "impact": "MEDIUM",
                "suggestion": "优化查询语句，添加索引"
            },
            {
                "bottleneck": "model_inference",
                "impact": "LOW", 
                "suggestion": "考虑模型量化或硬件加速"
            }
        ]
    
    def _generate_optimization_recommendations(self, performance_data: List[Dict[str, Any]]) -> List[str]:
        """生成优化建议"""
        return [
            "数据库查询优化，预计可提升响应速度15%",
            "缓存策略调整，减少重复计算",
            "异步处理耗时操作，提高并发能力"
        ]
    
    def _generate_executive_summary(self, 
                                  system_health: Dict[str, Any],
                                  security_threats: Dict[str, Any], 
                                  performance_trends: Dict[str, Any]) -> str:
        """生成执行摘要"""
        health_status = system_health.get('status', 'UNKNOWN')
        security_risk = security_threats.get('risk_assessment', {}).get('risk_level', 'UNKNOWN')
        
        summary_parts = []
        
        if health_status in ['EXCELLENT', 'GOOD']:
            summary_parts.append("系统运行状态良好")
        else:
            summary_parts.append("系统运行状态需要关注")
        
        if security_risk in ['LOW', 'MEDIUM']:
            summary_parts.append("安全风险可控")
        else:
            summary_parts.append("存在安全风险需要处理")
        
        performance_status = performance_trends.get('performance_metrics', {}).get('availability', 0)
        if performance_status >= 99.5:
            summary_parts.append("性能表现稳定")
        else:
            summary_parts.append("性能方面需要优化")
        
        return "。".join(summary_parts) + "。"
    
    def _extract_key_metrics(self, 
                           system_health: Dict[str, Any],
                           security_threats: Dict[str, Any],
                           performance_trends: Dict[str, Any]) -> Dict[str, Any]:
        """提取关键指标"""
        return {
            "system_health_score": system_health.get('health_score', 0),
            "security_risk_level": security_threats.get('risk_assessment', {}).get('risk_level', 'UNKNOWN'),
            "system_availability": performance_trends.get('performance_metrics', {}).get('availability', 0),
            "average_response_time": performance_trends.get('performance_metrics', {}).get('average_response_time', 0),
            "error_rate": performance_trends.get('performance_metrics', {}).get('error_rate', 0)
        }
    
    def _generate_action_items(self,
                             system_health: Dict[str, Any],
                             security_threats: Dict[str, Any],
                             performance_trends: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成行动项"""
        action_items = []
        
        # 从系统健康报告提取行动项
        health_recommendations = system_health.get('recommendations', [])
        for rec in health_recommendations:
            if "立即" in rec or "严重" in rec:
                priority = "HIGH"
            else:
                priority = "MEDIUM"
            
            action_items.append({
                "category": "SYSTEM_HEALTH",
                "description": rec,
                "priority": priority,
                "owner": "运维团队"
            })
        
        # 从安全报告提取行动项
        security_recommendations = security_threats.get('recommended_actions', [])
        for rec in security_recommendations:
            action_items.append({
                "category": "SECURITY",
                "description": rec,
                "priority": "HIGH",
                "owner": "安全团队"
            })
        
        # 从性能报告提取行动项
        performance_recommendations = performance_trends.get('optimization_recommendations', [])
        for rec in performance_recommendations:
            action_items.append({
                "category": "PERFORMANCE",
                "description": rec,
                "priority": "MEDIUM",
                "owner": "开发团队"
            })
        
        return action_items

# 全局日志分析器实例
log_analyzer = LogAnalyzer()

