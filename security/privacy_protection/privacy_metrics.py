"""
隐私指标模块 - 隐私保护效果指标
收集和报告隐私保护相关的性能指标
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

from ..security_monitoring.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


@dataclass
class PrivacyMetricPoint:
    """隐私指标数据点"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


class PrivacyMetrics:
    """
    隐私指标收集器
    收集和报告隐私保护相关的指标
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化隐私指标收集器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 指标存储
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        
        # 带标签的指标
        self.labeled_counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/privacy/metrics"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.audit_logger = AuditLogger()
        
        # 从其他模块获取依赖（延迟导入避免循环依赖）
        self._consent_manager = None
        self._data_encryption = None
        self._anonymization_engine = None
        self._privacy_auditor = None
        self._gdpr_compliance = None
        
        logger.info(f"隐私指标收集器初始化完成")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/privacy/metrics",
            "collection_interval_seconds": 60,
            "report_interval_seconds": 300,
            "enable_persistence": True,
            "max_histogram_points": 1000,
            "metrics_definitions": {
                "consent_total": {
                    "type": "counter",
                    "description": "Total number of consents"
                },
                "consent_by_purpose": {
                    "type": "labeled_counter",
                    "description": "Consents by purpose"
                },
                "consent_granted_total": {
                    "type": "counter",
                    "description": "Total number of granted consents"
                },
                "consent_revoked_total": {
                    "type": "counter",
                    "description": "Total number of revoked consents"
                },
                "data_encryption_total": {
                    "type": "counter",
                    "description": "Total number of data encryption operations"
                },
                "data_decryption_total": {
                    "type": "counter",
                    "description": "Total number of data decryption operations"
                },
                "anonymization_total": {
                    "type": "counter",
                    "description": "Total number of anonymization operations"
                },
                "anonymization_by_technique": {
                    "type": "labeled_counter",
                    "description": "Anonymizations by technique"
                },
                "privacy_audits_total": {
                    "type": "counter",
                    "description": "Total number of privacy audits"
                },
                "privacy_findings_total": {
                    "type": "counter",
                    "description": "Total number of privacy findings"
                },
                "privacy_findings_by_severity": {
                    "type": "labeled_counter",
                    "description": "Privacy findings by severity"
                },
                "gdpr_requests_total": {
                    "type": "counter",
                    "description": "Total number of GDPR requests"
                },
                "gdpr_requests_by_right": {
                    "type": "labeled_counter",
                    "description": "GDPR requests by right"
                },
                "gdpr_request_processing_time_ms": {
                    "type": "histogram",
                    "description": "GDPR request processing time"
                },
                "data_retention_cleanup_total": {
                    "type": "counter",
                    "description": "Total number of data retention cleanups"
                },
                "data_deleted_total": {
                    "type": "counter",
                    "description": "Total amount of data deleted"
                },
                "privacy_compliance_score": {
                    "type": "gauge",
                    "description": "Privacy compliance score (0-100)"
                }
            }
        }
    
    def _lazy_load_dependencies(self):
        """延迟加载依赖模块"""
        if self._consent_manager is None:
            from .consent_manager import get_consent_manager
            self._consent_manager = get_consent_manager()
        
        if self._data_encryption is None:
            from .data_encryption import get_data_encryption
            self._data_encryption = get_data_encryption()
        
        if self._anonymization_engine is None:
            from .anonymization_engine import get_anonymization_engine
            self._anonymization_engine = get_anonymization_engine()
        
        if self._privacy_auditor is None:
            from .privacy_auditor import get_privacy_auditor
            self._privacy_auditor = get_privacy_auditor()
        
        if self._gdpr_compliance is None:
            from .gdpr_compliance import get_gdpr_compliance
            self._gdpr_compliance = get_gdpr_compliance()
    
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
    
    def record_consent_metrics(self):
        """记录同意相关指标"""
        self._lazy_load_dependencies()
        
        if self._consent_manager:
            stats = self._consent_manager.get_statistics()
            
            self.set_gauge("consent_total", stats["total_consents"])
            
            for purpose, count in stats.get("purpose_distribution", {}).items():
                self.increment_labeled_counter("consent_by_purpose", purpose, count)
    
    def record_encryption_metrics(self):
        """记录加密相关指标"""
        self._lazy_load_dependencies()
        
        if self._data_encryption:
            stats = self._data_encryption.get_encryption_stats()
            
            # 可以记录更多加密相关指标
    
    def record_anonymization_metrics(self):
        """记录匿名化相关指标"""
        self._lazy_load_dependencies()
        
        if self._anonymization_engine:
            stats = self._anonymization_engine.get_statistics()
            
            self.set_gauge("anonymization_rules_total", stats["total_rules"])
            
            for technique in stats.get("techniques_used", []):
                self.increment_labeled_counter("anonymization_by_technique", technique)
    
    def record_audit_metrics(self):
        """记录审计相关指标"""
        self._lazy_load_dependencies()
        
        if self._privacy_auditor:
            stats = self._privacy_auditor.get_statistics()
            
            self.increment_counter("privacy_audits_total")
            self.set_gauge("privacy_findings_total", stats["total_findings"])
            
            # 这里应该根据实际审计结果记录严重性分布
    
    def record_gdpr_metrics(self):
        """记录GDPR相关指标"""
        self._lazy_load_dependencies()
        
        if self._gdpr_compliance:
            # 记录请求统计
            # 这里简化实现
            pass
    
    def collect_all_metrics(self):
        """收集所有指标"""
        self.record_consent_metrics()
        self.record_encryption_metrics()
        self.record_anonymization_metrics()
        self.record_audit_metrics()
        self.record_gdpr_metrics()
        
        logger.debug("已收集所有隐私指标")
    
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
            
            filename = f"privacy_metrics_{int(time.time())}.json"
            filepath = self.storage_path / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"隐私指标快照已保存: {filepath}")
            
            # 清理旧文件
            self._cleanup_old_snapshots()
            
        except Exception as e:
            logger.error(f"保存隐私指标快照失败: {str(e)}")
    
    def _cleanup_old_snapshots(self, keep_days: int = 7):
        """清理旧快照"""
        try:
            cutoff_time = time.time() - (keep_days * 24 * 3600)
            
            for filepath in self.storage_path.glob("privacy_metrics_*.json"):
                if filepath.stat().st_mtime < cutoff_time:
                    filepath.unlink()
                    logger.debug(f"删除旧快照: {filepath}")
                    
        except Exception as e:
            logger.error(f"清理旧快照失败: {str(e)}")
    
    def get_report(self) -> Dict[str, Any]:
        """
        获取隐私指标报告
        
        Returns:
            报告数据
        """
        self.collect_all_metrics()
        snapshot = self.get_metrics_snapshot()
        
        # 计算合规分数
        compliance_score = self._calculate_compliance_score()
        self.set_gauge("privacy_compliance_score", compliance_score)
        
        report = {
            "generated_at": time.time(),
            "compliance_score": compliance_score,
            "metrics": snapshot,
            "summary": {
                "total_consents": self.counters.get("consent_total", 0),
                "total_encryptions": self.counters.get("data_encryption_total", 0),
                "total_anonymizations": self.counters.get("anonymization_total", 0),
                "total_audits": self.counters.get("privacy_audits_total", 0),
                "total_findings": self.counters.get("privacy_findings_total", 0),
                "total_gdpr_requests": self.counters.get("gdpr_requests_total", 0)
            }
        }
        
        return report
    
    def _calculate_compliance_score(self) -> float:
        """计算隐私合规分数（0-100）"""
        score = 100.0
        deductions = 0
        
        # 基于各个指标计算扣分
        # 简化实现
        if self.counters.get("privacy_findings_total", 0) > 0:
            findings = self.counters["privacy_findings_total"]
            deductions += min(findings * 5, 30)  # 每个发现扣5分，最多扣30分
        
        if self.counters.get("gdpr_requests_total", 0) > 0:
            # 检查是否有未处理的请求
            pending = self.counters.get("gdpr_requests_pending", 0)
            deductions += min(pending * 10, 20)
        
        score = max(0, score - deductions)
        return score


# 单例实例
_privacy_metrics_instance = None


def get_privacy_metrics() -> PrivacyMetrics:
    """获取隐私指标收集器单例实例"""
    global _privacy_metrics_instance
    if _privacy_metrics_instance is None:
        _privacy_metrics_instance = PrivacyMetrics()
    return _privacy_metrics_instance

