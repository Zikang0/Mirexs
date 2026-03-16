"""
安全指标模块 - 安全系统性能指标
收集和报告安全相关的性能指标
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

from ..access_control.access_logger import AccessLogger, get_access_logger
from .threat_detection import ThreatDetection, get_threat_detection
from .vulnerability_scanner import VulnerabilityScanner, get_vulnerability_scanner
from .incident_response import IncidentResponse, get_incident_response
from .compliance_checker import ComplianceChecker, get_compliance_checker
from .risk_assessment import RiskAssessment, get_risk_assessment

logger = logging.getLogger(__name__)


@dataclass
class SecurityMetricPoint:
    """安全指标数据点"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class SecurityMetrics:
    """
    安全指标收集器
    收集和报告安全相关的性能指标
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化安全指标收集器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 指标存储
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        
        # 带标签的计数器
        self.labeled_counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/security/metrics"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.access_logger = get_access_logger()
        
        # 延迟加载其他依赖
        self._threat_detection = None
        self._vulnerability_scanner = None
        self._incident_response = None
        self._compliance_checker = None
        self._risk_assessment = None
        
        logger.info(f"安全指标收集器初始化完成")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/security/metrics",
            "collection_interval_seconds": 60,
            "report_interval_seconds": 300,
            "enable_persistence": True,
            "max_histogram_points": 1000,
            "metrics_definitions": {
                "threats_total": {
                    "type": "counter",
                    "description": "Total number of threats detected"
                },
                "threats_by_level": {
                    "type": "labeled_counter",
                    "description": "Threats by severity level"
                },
                "incidents_total": {
                    "type": "counter",
                    "description": "Total number of security incidents"
                },
                "incidents_by_severity": {
                    "type": "labeled_counter",
                    "description": "Incidents by severity"
                },
                "incidents_by_status": {
                    "type": "labeled_counter",
                    "description": "Incidents by status"
                },
                "vulnerabilities_total": {
                    "type": "counter",
                    "description": "Total number of vulnerabilities"
                },
                "vulnerabilities_by_severity": {
                    "type": "labeled_counter",
                    "description": "Vulnerabilities by severity"
                },
                "vulnerabilities_patched": {
                    "type": "counter",
                    "description": "Number of patched vulnerabilities"
                },
                "mean_time_to_detect": {
                    "type": "gauge",
                    "description": "Mean time to detect incidents (minutes)"
                },
                "mean_time_to_respond": {
                    "type": "gauge",
                    "description": "Mean time to respond to incidents (minutes)"
                },
                "mean_time_to_resolve": {
                    "type": "gauge",
                    "description": "Mean time to resolve incidents (minutes)"
                },
                "compliance_score": {
                    "type": "gauge",
                    "description": "Overall compliance score (0-100)"
                },
                "risk_score": {
                    "type": "gauge",
                    "description": "Overall security risk score"
                },
                "security_coverage": {
                    "type": "gauge",
                    "description": "Security control coverage percentage"
                },
                "false_positive_rate": {
                    "type": "gauge",
                    "description": "False positive rate for detections"
                },
                "security_training_completion": {
                    "type": "gauge",
                    "description": "Security training completion rate"
                }
            }
        }
    
    def _lazy_load_dependencies(self):
        """延迟加载依赖模块"""
        if self._threat_detection is None:
            self._threat_detection = get_threat_detection()
        
        if self._vulnerability_scanner is None:
            self._vulnerability_scanner = get_vulnerability_scanner()
        
        if self._incident_response is None:
            self._incident_response = get_incident_response()
        
        if self._compliance_checker is None:
            self._compliance_checker = get_compliance_checker()
        
        if self._risk_assessment is None:
            self._risk_assessment = get_risk_assessment()
    
    def increment_counter(self, name: str, value: int = 1):
        """增加计数器"""
        self.counters[name] += value
        logger.debug(f"计数器 {name} 增加 {value}，当前值: {self.counters[name]}")
    
    def increment_labeled_counter(self, name: str, label: str, value: int = 1):
        """增加带标签的计数器"""
        self.labeled_counters[name][label] += value
    
    def set_gauge(self, name: str, value: float):
        """设置仪表盘值"""
        self.gauges[name] = value
    
    def observe_histogram(self, name: str, value: float):
        """观察直方图值"""
        hist = self.histograms[name]
        hist.append(value)
        
        # 限制大小
        max_size = self.config["max_histogram_points"]
        if len(hist) > max_size:
            self.histograms[name] = hist[-max_size:]
    
    def record_threat_metrics(self):
        """记录威胁相关指标"""
        self._lazy_load_dependencies()
        
        if self._threat_detection:
            stats = self._threat_detection.get_threat_statistics()
            
            # 按级别统计
            for level, count in stats.get("by_level", {}).items():
                self.increment_labeled_counter("threats_by_level", level, count)
            
            # 总威胁数
            self.set_gauge("threats_total", stats.get("total_threats", 0))
    
    def record_incident_metrics(self):
        """记录事件相关指标"""
        self._lazy_load_dependencies()
        
        if self._incident_response:
            stats = self._incident_response.get_statistics()
            
            # 按严重性统计
            for severity, count in stats.get("by_severity", {}).items():
                self.increment_labeled_counter("incidents_by_severity", severity, count)
            
            # 按状态统计
            for status, count in stats.get("by_status", {}).items():
                self.increment_labeled_counter("incidents_by_status", status, count)
            
            # 总事件数
            self.set_gauge("incidents_total", stats.get("total_incidents", 0))
            
            # MTTR
            if "average_resolution_time" in stats:
                self.set_gauge("mean_time_to_resolve", stats["average_resolution_time"])
    
    def record_vulnerability_metrics(self):
        """记录漏洞相关指标"""
        self._lazy_load_dependencies()
        
        if self._vulnerability_scanner:
            stats = self._vulnerability_scanner.get_statistics()
            
            # 按严重性统计
            for severity, count in stats.get("by_severity", {}).items():
                self.increment_labeled_counter("vulnerabilities_by_severity", severity, count)
            
            # 总漏洞数
            self.set_gauge("vulnerabilities_total", stats.get("total_vulnerabilities", 0))
    
    def record_compliance_metrics(self):
        """记录合规相关指标"""
        self._lazy_load_dependencies()
        
        if self._compliance_checker:
            summary = self._compliance_checker.get_compliance_summary()
            
            # 计算合规分数
            total_controls = summary["overall"]["total_controls"]
            compliant = summary["overall"]["compliant"]
            
            if total_controls > 0:
                compliance_score = (compliant / total_controls) * 100
                self.set_gauge("compliance_score", compliance_score)
    
    def record_risk_metrics(self):
        """记录风险相关指标"""
        self._lazy_load_dependencies()
        
        if self._risk_assessment:
            stats = self._risk_assessment.get_statistics()
            
            # 总风险暴露
            self.set_gauge("risk_score", stats.get("total_risk_exposure", 0))
            
            # 未处理风险
            self.set_gauge("open_risks", stats.get("open_risks", 0))
    
    def collect_all_metrics(self):
        """收集所有指标"""
        self.record_threat_metrics()
        self.record_incident_metrics()
        self.record_vulnerability_metrics()
        self.record_compliance_metrics()
        self.record_risk_metrics()
        
        logger.debug("已收集所有安全指标")
    
    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """获取指标快照"""
        snapshot = {
            "timestamp": time.time(),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "labeled_counters": {k: dict(v) for k, v in self.labeled_counters.items()},
            "histograms": {}
        }
        
        # 计算直方图统计
        for name, values in self.histograms.items():
            if values:
                snapshot["histograms"][name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "p50": self._percentile(values, 50),
                    "p90": self._percentile(values, 90),
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99)
                }
            else:
                snapshot["histograms"][name] = {
                    "count": 0,
                    "min": 0,
                    "max": 0,
                    "avg": 0
                }
        
        return snapshot
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """计算百分位数"""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def save_snapshot(self):
        """保存指标快照"""
        try:
            snapshot = self.get_metrics_snapshot()
            
            filename = f"security_metrics_{int(time.time())}.json"
            filepath = self.storage_path / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"安全指标快照已保存: {filepath}")
            
            # 清理旧文件
            self._cleanup_old_snapshots()
            
        except Exception as e:
            logger.error(f"保存安全指标快照失败: {str(e)}")
    
    def _cleanup_old_snapshots(self, keep_days: int = 7):
        """清理旧快照"""
        try:
            cutoff_time = time.time() - (keep_days * 24 * 3600)
            
            for filepath in self.storage_path.glob("security_metrics_*.json"):
                if filepath.stat().st_mtime < cutoff_time:
                    filepath.unlink()
                    logger.debug(f"删除旧快照: {filepath}")
                    
        except Exception as e:
            logger.error(f"清理旧快照失败: {str(e)}")
    
    def get_report(self) -> Dict[str, Any]:
        """
        获取安全指标报告
        
        Returns:
            报告数据
        """
        self.collect_all_metrics()
        snapshot = self.get_metrics_snapshot()
        
        # 计算安全态势分数
        security_posture = self._calculate_security_posture()
        
        report = {
            "generated_at": time.time(),
            "security_posture": security_posture,
            "metrics": snapshot,
            "summary": {
                "total_threats": self.counters.get("threats_total", 0),
                "total_incidents": self.counters.get("incidents_total", 0),
                "total_vulnerabilities": self.gauges.get("vulnerabilities_total", 0),
                "compliance_score": self.gauges.get("compliance_score", 0),
                "risk_score": self.gauges.get("risk_score", 0)
            }
        }
        
        return report
    
    def _calculate_security_posture(self) -> Dict[str, Any]:
        """计算安全态势"""
        # 获取各维度分数
        compliance = self.gauges.get("compliance_score", 0) / 100  # 0-1
        risk = max(0, 1 - self.gauges.get("risk_score", 0) / 10)  # 归一化
        
        # 漏洞分数
        vuln_count = self.gauges.get("vulnerabilities_total", 0)
        vuln_score = max(0, 1 - vuln_count / 100) if vuln_count > 0 else 1
        
        # 事件分数
        incident_count = self.counters.get("incidents_total", 0)
        incident_score = max(0, 1 - incident_count / 50) if incident_count > 0 else 1
        
        # 综合分数
        overall = (compliance * 0.3 + risk * 0.3 + vuln_score * 0.2 + incident_score * 0.2) * 100
        
        return {
            "overall": overall,
            "compliance": compliance * 100,
            "risk": (1 - risk) * 100,  # 转为风险值
            "vulnerability": (1 - vuln_score) * 100,
            "incident": (1 - incident_score) * 100,
            "level": self._determine_posture_level(overall)
        }
    
    def _determine_posture_level(self, score: float) -> str:
        """确定安全态势级别"""
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 60:
            return "fair"
        elif score >= 40:
            return "poor"
        else:
            return "critical"
    
    def reset_counters(self):
        """重置计数器"""
        self.counters.clear()
        logger.info("所有计数器已重置")
    
    def reset_histograms(self):
        """重置直方图"""
        self.histograms.clear()
        logger.info("所有直方图已重置")


# 单例实例
_security_metrics_instance = None


def get_security_metrics() -> SecurityMetrics:
    """获取安全指标收集器单例实例"""
    global _security_metrics_instance
    if _security_metrics_instance is None:
        _security_metrics_instance = SecurityMetrics()
    return _security_metrics_instance

