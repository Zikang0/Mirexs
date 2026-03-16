"""
Web指标模块 - Mirexs Web界面

收集和报告Web应用的性能指标，包括：
1. 核心Web指标 (Core Web Vitals)
2. 页面加载性能
3. 资源加载
4. 交互性能
5. 错误追踪
6. 用户行为分析
"""

import logging
import time
import json
import platform
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import deque
import uuid

logger = logging.getLogger(__name__)

class WebVital(Enum):
    """核心Web指标枚举"""
    LCP = "largest_contentful_paint"  # 最大内容绘制
    FID = "first_input_delay"  # 首次输入延迟
    CLS = "cumulative_layout_shift"  # 累积布局偏移
    FCP = "first_contentful_paint"  # 首次内容绘制
    TTFB = "time_to_first_byte"  # 首字节时间
    INP = "interaction_to_next_paint"  # 交互到下一次绘制
    TTI = "time_to_interactive"  # 可交互时间

class ResourceType(Enum):
    """资源类型枚举"""
    DOCUMENT = "document"
    SCRIPT = "script"
    STYLESHEET = "stylesheet"
    IMAGE = "image"
    FONT = "font"
    FETCH = "fetch"
    XHR = "xhr"
    WEBSOCKET = "websocket"
    OTHER = "other"

class NavigationType(Enum):
    """导航类型枚举"""
    NAVIGATE = "navigate"
    RELOAD = "reload"
    BACK_FORWARD = "back_forward"
    PRERENDER = "prerender"

@dataclass
class MetricValue:
    """指标值"""
    name: str
    value: float
    unit: str  # ms, score, bytes
    rating: str  # good, needs_improvement, poor
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ResourceMetric:
    """资源指标"""
    url: str
    type: ResourceType
    duration: float
    size: int
    success: bool
    status_code: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    initiator: Optional[str] = None
    cache_hit: bool = False

@dataclass
class ErrorMetric:
    """错误指标"""
    message: str
    filename: Optional[str] = None
    lineno: Optional[int] = None
    colno: Optional[int] = None
    stack: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    url: Optional[str] = None
    user_agent: Optional[str] = None

@dataclass
class UserTimingMetric:
    """用户计时指标"""
    name: str
    start_time: float
    duration: float
    detail: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class WebVitalsScore:
    """Web指标评分"""
    lcp: Dict[str, Any]
    fid: Dict[str, Any]
    cls: Dict[str, Any]
    fcp: Dict[str, Any]
    ttfb: Dict[str, Any]
    inp: Dict[str, Any]
    overall_score: float  # 0-100

@dataclass
class WebMetricsConfig:
    """Web指标收集器配置"""
    # 收集配置
    collect_core_vitals: bool = True
    collect_resources: bool = True
    collect_errors: bool = True
    collect_user_timing: bool = True
    collect_navigation_timing: bool = True
    
    # 采样率 (0-1)
    sample_rate: float = 1.0
    
    # 上报配置
    auto_report: bool = True
    report_interval: int = 60  # 秒
    report_url: Optional[str] = None
    report_batch_size: int = 50
    
    # 历史记录
    max_history: int = 1000
    max_resource_history: int = 500
    max_error_history: int = 200
    
    # 阈值配置
    lcp_threshold_good: float = 2500  # 毫秒
    lcp_threshold_poor: float = 4000  # 毫秒
    fid_threshold_good: float = 100  # 毫秒
    fid_threshold_poor: float = 300  # 毫秒
    cls_threshold_good: float = 0.1  # 分数
    cls_threshold_poor: float = 0.25  # 分数
    fcp_threshold_good: float = 1800  # 毫秒
    fcp_threshold_poor: float = 3000  # 毫秒
    inp_threshold_good: float = 200  # 毫秒
    inp_threshold_poor: float = 500  # 毫秒
    
    # 文件路径
    data_dir: str = "data/web_metrics/"

@dataclass
class WebPerformanceReport:
    """Web性能报告"""
    summary: Dict[str, Any]
    vitals: Dict[str, Any]
    resources: Dict[str, Any]
    errors: Dict[str, Any]
    recommendations: List[str]
    generated_at: float = field(default_factory=time.time)

class WebMetrics:
    """
    Web指标收集器
    
    负责收集Web应用的性能指标，包括：
    - 核心Web指标
    - 资源加载性能
    - JavaScript错误
    - 用户交互延迟
    - 自定义性能标记
    - 页面导航性能
    """
    
    def __init__(self, config: Optional[WebMetricsConfig] = None):
        """
        初始化Web指标收集器
        
        Args:
            config: 指标收集器配置
        """
        self.config = config or WebMetricsConfig()
        
        # 指标存储
        self.vitals: Dict[str, List[MetricValue]] = {
            "lcp": [],
            "fid": [],
            "cls": [],
            "fcp": [],
            "ttfb": [],
            "inp": [],
            "tti": []
        }
        
        self.resources: List[ResourceMetric] = []
        self.errors: List[ErrorMetric] = []
        self.user_timings: List[UserTimingMetric] = []
        
        # 自定义标记
        self.custom_marks: Dict[str, float] = {}
        self.custom_measures: List[Dict[str, Any]] = []
        
        # 页面信息
        self.page_url: Optional[str] = None
        self.page_title: Optional[str] = None
        self.navigation_type: NavigationType = NavigationType.NAVIGATE
        self.user_agent: str = self._get_user_agent()
        self.session_id: str = str(uuid.uuid4())
        
        # 累积CLS
        self._cumulative_cls: float = 0.0
        self._cls_sources: List[Dict[str, Any]] = []
        
        # 布局偏移记录
        self._layout_shifts: List[Dict[str, Any]] = []
        
        # 首次输入时间
        self._first_input_time: Optional[float] = None
        self._first_input_delay: Optional[float] = None
        
        # 交互记录
        self._interactions: List[Dict[str, Any]] = []
        
        # 上报线程
        self._report_thread: Optional[threading.Thread] = None
        self._stop_report = threading.Event()
        self._report_queue: deque = deque(maxlen=self.config.report_batch_size * 10)
        
        # 监听器
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        
        # 创建数据目录
        self._ensure_data_directory()
        
        # 启动自动上报
        if self.config.auto_report and self.config.report_url:
            self._start_auto_report()
        
        logger.info(f"WebMetrics initialized (session: {self.session_id})")
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        import os
        os.makedirs(self.config.data_dir, exist_ok=True)
    
    def _get_user_agent(self) -> str:
        """获取用户代理字符串"""
        # 实际实现中从浏览器获取
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    def _start_auto_report(self):
        """启动自动上报"""
        def report_loop():
            while not self._stop_report.is_set():
                try:
                    if self._report_queue:
                        # 批量上报
                        batch = []
                        while len(batch) < self.config.report_batch_size and self._report_queue:
                            batch.append(self._report_queue.popleft())
                        
                        if batch:
                            self._send_report_batch(batch)
                    
                    self._stop_report.wait(self.config.report_interval)
                    
                except Exception as e:
                    logger.error(f"Auto report error: {e}")
        
        self._report_thread = threading.Thread(target=report_loop, daemon=True)
        self._report_thread.start()
        logger.debug("Auto report started")
    
    def _send_report_batch(self, batch: List[Dict[str, Any]]):
        """发送批量报告"""
        # 实际实现中会发送到服务器
        logger.debug(f"Sending report batch: {len(batch)} items")
    
    def _queue_report(self, data: Dict[str, Any]):
        """加入上报队列"""
        if self.config.auto_report:
            self._report_queue.append(data)
    
    def _get_rating(self, metric: str, value: float) -> str:
        """获取指标评级"""
        if metric == "lcp":
            if value <= self.config.lcp_threshold_good:
                return "good"
            elif value <= self.config.lcp_threshold_poor:
                return "needs_improvement"
            else:
                return "poor"
        elif metric == "fid":
            if value <= self.config.fid_threshold_good:
                return "good"
            elif value <= self.config.fid_threshold_poor:
                return "needs_improvement"
            else:
                return "poor"
        elif metric == "cls":
            if value <= self.config.cls_threshold_good:
                return "good"
            elif value <= self.config.cls_threshold_poor:
                return "needs_improvement"
            else:
                return "poor"
        elif metric == "fcp":
            if value <= self.config.fcp_threshold_good:
                return "good"
            elif value <= self.config.fcp_threshold_poor:
                return "needs_improvement"
            else:
                return "poor"
        elif metric == "inp":
            if value <= self.config.inp_threshold_good:
                return "good"
            elif value <= self.config.inp_threshold_poor:
                return "needs_improvement"
            else:
                return "poor"
        return "unknown"
    
    def record_lcp(self, value: float, element: Optional[str] = None):
        """
        记录最大内容绘制时间
        
        Args:
            value: 时间（毫秒）
            element: 元素描述
        """
        if not self.config.collect_core_vitals:
            return
        
        metric = MetricValue(
            name="lcp",
            value=value,
            unit="ms",
            rating=self._get_rating("lcp", value),
            metadata={"element": element} if element else {}
        )
        
        self.vitals["lcp"].append(metric)
        
        # 限制历史
        if len(self.vitals["lcp"]) > self.config.max_history:
            self.vitals["lcp"] = self.vitals["lcp"][-self.config.max_history:]
        
        logger.debug(f"LCP recorded: {value}ms ({metric.rating})")
        
        self._queue_report({
            "type": "vital",
            "name": "lcp",
            "value": value,
            "rating": metric.rating,
            "timestamp": metric.timestamp
        })
    
    def record_fid(self, delay: float, input_type: Optional[str] = None):
        """
        记录首次输入延迟
        
        Args:
            delay: 延迟时间（毫秒）
            input_type: 输入类型
        """
        if not self.config.collect_core_vitals:
            return
        
        metric = MetricValue(
            name="fid",
            value=delay,
            unit="ms",
            rating=self._get_rating("fid", delay),
            metadata={"input_type": input_type} if input_type else {}
        )
        
        self.vitals["fid"].append(metric)
        self._first_input_delay = delay
        self._first_input_time = time.time()
        
        # 限制历史
        if len(self.vitals["fid"]) > self.config.max_history:
            self.vitals["fid"] = self.vitals["fid"][-self.config.max_history:]
        
        logger.debug(f"FID recorded: {delay}ms ({metric.rating})")
        
        self._queue_report({
            "type": "vital",
            "name": "fid",
            "value": delay,
            "rating": metric.rating,
            "timestamp": metric.timestamp
        })
    
    def record_cls(self, value: float, sources: Optional[List[Dict[str, Any]]] = None):
        """
        记录累积布局偏移
        
        Args:
            value: CLS分数
            sources: 偏移来源
        """
        if not self.config.collect_core_vitals:
            return
        
        self._cumulative_cls = value
        
        metric = MetricValue(
            name="cls",
            value=value,
            unit="score",
            rating=self._get_rating("cls", value),
            metadata={"sources": sources} if sources else {}
        )
        
        self.vitals["cls"].append(metric)
        
        if sources:
            self._cls_sources.extend(sources)
        
        # 限制历史
        if len(self.vitals["cls"]) > self.config.max_history:
            self.vitals["cls"] = self.vitals["cls"][-self.config.max_history:]
        
        logger.debug(f"CLS recorded: {value} ({metric.rating})")
        
        self._queue_report({
            "type": "vital",
            "name": "cls",
            "value": value,
            "rating": metric.rating,
            "timestamp": metric.timestamp
        })
    
    def record_fcp(self, value: float):
        """
        记录首次内容绘制时间
        
        Args:
            value: 时间（毫秒）
        """
        if not self.config.collect_core_vitals:
            return
        
        metric = MetricValue(
            name="fcp",
            value=value,
            unit="ms",
            rating=self._get_rating("fcp", value)
        )
        
        self.vitals["fcp"].append(metric)
        
        # 限制历史
        if len(self.vitals["fcp"]) > self.config.max_history:
            self.vitals["fcp"] = self.vitals["fcp"][-self.config.max_history:]
        
        logger.debug(f"FCP recorded: {value}ms ({metric.rating})")
        
        self._queue_report({
            "type": "vital",
            "name": "fcp",
            "value": value,
            "rating": metric.rating,
            "timestamp": metric.timestamp
        })
    
    def record_ttfb(self, value: float):
        """
        记录首字节时间
        
        Args:
            value: 时间（毫秒）
        """
        if not self.config.collect_navigation_timing:
            return
        
        metric = MetricValue(
            name="ttfb",
            value=value,
            unit="ms",
            rating=self._get_rating("ttfb", value)
        )
        
        self.vitals["ttfb"].append(metric)
        
        # 限制历史
        if len(self.vitals["ttfb"]) > self.config.max_history:
            self.vitals["ttfb"] = self.vitals["ttfb"][-self.config.max_history:]
        
        logger.debug(f"TTFB recorded: {value}ms ({metric.rating})")
        
        self._queue_report({
            "type": "vital",
            "name": "ttfb",
            "value": value,
            "rating": metric.rating,
            "timestamp": metric.timestamp
        })
    
    def record_inp(self, value: float, interaction_type: Optional[str] = None):
        """
        记录交互到下一次绘制时间
        
        Args:
            value: 时间（毫秒）
            interaction_type: 交互类型
        """
        if not self.config.collect_core_vitals:
            return
        
        metric = MetricValue(
            name="inp",
            value=value,
            unit="ms",
            rating=self._get_rating("inp", value),
            metadata={"interaction_type": interaction_type} if interaction_type else {}
        )
        
        self.vitals["inp"].append(metric)
        
        # 记录交互
        self._interactions.append({
            "type": interaction_type,
            "duration": value,
            "timestamp": time.time()
        })
        
        # 限制历史
        if len(self.vitals["inp"]) > self.config.max_history:
            self.vitals["inp"] = self.vitals["inp"][-self.config.max_history:]
        
        if len(self._interactions) > self.config.max_history:
            self._interactions = self._interactions[-self.config.max_history:]
        
        logger.debug(f"INP recorded: {value}ms ({metric.rating})")
        
        self._queue_report({
            "type": "vital",
            "name": "inp",
            "value": value,
            "rating": metric.rating,
            "timestamp": metric.timestamp
        })
    
    def record_resource(self, url: str, resource_type: ResourceType, duration: float,
                       size: int, success: bool, status_code: Optional[int] = None,
                       cache_hit: bool = False, initiator: Optional[str] = None):
        """
        记录资源加载
        
        Args:
            url: 资源URL
            resource_type: 资源类型
            duration: 加载时间（毫秒）
            size: 大小（字节）
            success: 是否成功
            status_code: HTTP状态码
            cache_hit: 是否命中缓存
            initiator: 发起者
        """
        if not self.config.collect_resources:
            return
        
        resource = ResourceMetric(
            url=url,
            type=resource_type,
            duration=duration,
            size=size,
            success=success,
            status_code=status_code,
            cache_hit=cache_hit,
            initiator=initiator
        )
        
        self.resources.append(resource)
        
        # 限制历史
        if len(self.resources) > self.config.max_resource_history:
            self.resources = self.resources[-self.config.max_resource_history:]
        
        logger.debug(f"Resource recorded: {url} ({duration}ms, {size} bytes)")
        
        self._queue_report({
            "type": "resource",
            "url": url,
            "resource_type": resource_type.value,
            "duration": duration,
            "size": size,
            "success": success,
            "status_code": status_code,
            "cache_hit": cache_hit,
            "timestamp": resource.timestamp
        })
    
    def record_error(self, message: str, filename: Optional[str] = None,
                    lineno: Optional[int] = None, colno: Optional[int] = None,
                    stack: Optional[str] = None):
        """
        记录错误
        
        Args:
            message: 错误消息
            filename: 文件名
            lineno: 行号
            colno: 列号
            stack: 堆栈
        """
        if not self.config.collect_errors:
            return
        
        error = ErrorMetric(
            message=message,
            filename=filename,
            lineno=lineno,
            colno=colno,
            stack=stack,
            url=self.page_url,
            user_agent=self.user_agent
        )
        
        self.errors.append(error)
        
        # 限制历史
        if len(self.errors) > self.config.max_error_history:
            self.errors = self.errors[-self.config.max_error_history:]
        
        logger.error(f"Error recorded: {message} at {filename}:{lineno}")
        
        self._queue_report({
            "type": "error",
            "message": message,
            "filename": filename,
            "lineno": lineno,
            "colno": colno,
            "stack": stack,
            "url": self.page_url,
            "timestamp": error.timestamp
        })
    
    def mark(self, name: str):
        """
        记录自定义标记
        
        Args:
            name: 标记名称
        """
        if not self.config.collect_user_timing:
            return
        
        self.custom_marks[name] = time.time() * 1000  # 转换为毫秒
        logger.debug(f"Mark recorded: {name}")
    
    def measure(self, name: str, start_mark: str, end_mark: Optional[str] = None):
        """
        测量两个标记之间的时间
        
        Args:
            name: 测量名称
            start_mark: 起始标记
            end_mark: 结束标记（可选，默认为当前时间）
        """
        if not self.config.collect_user_timing:
            return
        
        if start_mark not in self.custom_marks:
            logger.warning(f"Start mark not found: {start_mark}")
            return
        
        start_time = self.custom_marks[start_mark]
        
        if end_mark:
            if end_mark not in self.custom_marks:
                logger.warning(f"End mark not found: {end_mark}")
                return
            end_time = self.custom_marks[end_mark]
        else:
            end_time = time.time() * 1000
        
        duration = end_time - start_time
        
        measure = {
            "name": name,
            "start_mark": start_mark,
            "end_mark": end_mark,
            "duration": duration,
            "timestamp": time.time()
        }
        
        self.custom_measures.append(measure)
        
        logger.debug(f"Measure recorded: {name} = {duration}ms")
        
        self._queue_report({
            "type": "user_timing",
            "name": name,
            "duration": duration,
            "start_mark": start_mark,
            "end_mark": end_mark,
            "timestamp": measure["timestamp"]
        })
    
    def set_page_info(self, url: str, title: Optional[str] = None,
                     navigation_type: NavigationType = NavigationType.NAVIGATE):
        """
        设置页面信息
        
        Args:
            url: 页面URL
            title: 页面标题
            navigation_type: 导航类型
        """
        self.page_url = url
        self.page_title = title
        self.navigation_type = navigation_type
        logger.debug(f"Page info set: {url}")
    
    def record_layout_shift(self, value: float, sources: List[Dict[str, Any]]):
        """
        记录布局偏移
        
        Args:
            value: 偏移值
            sources: 偏移来源
        """
        self._layout_shifts.append({
            "value": value,
            "sources": sources,
            "timestamp": time.time()
        })
        
        # 更新累积CLS
        self._cumulative_cls += value
        
        # 限制历史
        if len(self._layout_shifts) > self.config.max_history:
            self._layout_shifts = self._layout_shifts[-self.config.max_history:]
    
    def get_current_vitals(self) -> Dict[str, Any]:
        """
        获取当前核心Web指标
        
        Returns:
            指标字典
        """
        vitals = {}
        
        for name, values in self.vitals.items():
            if values:
                latest = values[-1]
                vitals[name] = {
                    "value": latest.value,
                    "unit": latest.unit,
                    "rating": latest.rating,
                    "timestamp": latest.timestamp
                }
        
        return vitals
    
    def get_vitals_score(self) -> WebVitalsScore:
        """
        获取Web指标评分
        
        Returns:
            评分对象
        """
        vitals = self.get_current_vitals()
        
        # 计算各项评分
        lcp_score = self._calculate_vital_score("lcp", vitals.get("lcp", {}).get("value"))
        fid_score = self._calculate_vital_score("fid", vitals.get("fid", {}).get("value"))
        cls_score = self._calculate_vital_score("cls", vitals.get("cls", {}).get("value"))
        fcp_score = self._calculate_vital_score("fcp", vitals.get("fcp", {}).get("value"))
        ttfb_score = self._calculate_vital_score("ttfb", vitals.get("ttfb", {}).get("value"))
        inp_score = self._calculate_vital_score("inp", vitals.get("inp", {}).get("value"))
        
        # 计算总体评分（加权平均）
        weights = {
            "lcp": 0.25,
            "fid": 0.25,
            "cls": 0.25,
            "fcp": 0.15,
            "inp": 0.10
        }
        
        overall = (
            lcp_score * weights["lcp"] +
            fid_score * weights["fid"] +
            cls_score * weights["cls"] +
            fcp_score * weights["fcp"] +
            inp_score * weights["inp"]
        )
        
        return WebVitalsScore(
            lcp={"value": vitals.get("lcp"), "score": lcp_score},
            fid={"value": vitals.get("fid"), "score": fid_score},
            cls={"value": vitals.get("cls"), "score": cls_score},
            fcp={"value": vitals.get("fcp"), "score": fcp_score},
            ttfb={"value": vitals.get("ttfb"), "score": ttfb_score},
            inp={"value": vitals.get("inp"), "score": inp_score},
            overall_score=overall
        )
    
    def _calculate_vital_score(self, vital: str, value: Optional[float]) -> float:
        """计算单个指标评分（0-100）"""
        if value is None:
            return 0
        
        if vital == "lcp":
            if value <= self.config.lcp_threshold_good:
                return 100
            elif value <= self.config.lcp_threshold_poor:
                # 线性插值 100 -> 50
                return 100 - 50 * (value - self.config.lcp_threshold_good) / (self.config.lcp_threshold_poor - self.config.lcp_threshold_good)
            else:
                # 超过poor阈值，线性下降到0
                max_poor = self.config.lcp_threshold_poor * 2
                if value >= max_poor:
                    return 0
                return 50 - 50 * (value - self.config.lcp_threshold_poor) / (max_poor - self.config.lcp_threshold_poor)
        
        elif vital == "fid":
            if value <= self.config.fid_threshold_good:
                return 100
            elif value <= self.config.fid_threshold_poor:
                return 100 - 50 * (value - self.config.fid_threshold_good) / (self.config.fid_threshold_poor - self.config.fid_threshold_good)
            else:
                max_poor = self.config.fid_threshold_poor * 2
                if value >= max_poor:
                    return 0
                return 50 - 50 * (value - self.config.fid_threshold_poor) / (max_poor - self.config.fid_threshold_poor)
        
        elif vital == "cls":
            if value <= self.config.cls_threshold_good:
                return 100
            elif value <= self.config.cls_threshold_poor:
                return 100 - 50 * (value - self.config.cls_threshold_good) / (self.config.cls_threshold_poor - self.config.cls_threshold_good)
            else:
                max_poor = self.config.cls_threshold_poor * 2
                if value >= max_poor:
                    return 0
                return 50 - 50 * (value - self.config.cls_threshold_poor) / (max_poor - self.config.cls_threshold_poor)
        
        return 50
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """
        获取资源统计
        
        Returns:
            资源统计字典
        """
        stats = {
            "total": len(self.resources),
            "by_type": {},
            "avg_duration": 0,
            "total_size": 0,
            "success_rate": 0,
            "cache_hit_rate": 0
        }
        
        if not self.resources:
            return stats
        
        total_duration = 0
        success_count = 0
        cache_hit_count = 0
        
        for resource in self.resources:
            # 按类型统计
            type_name = resource.type.value
            if type_name not in stats["by_type"]:
                stats["by_type"][type_name] = {
                    "count": 0,
                    "total_size": 0,
                    "avg_duration": 0
                }
            
            stats["by_type"][type_name]["count"] += 1
            stats["by_type"][type_name]["total_size"] += resource.size
            
            total_duration += resource.duration
            stats["total_size"] += resource.size
            
            if resource.success:
                success_count += 1
            
            if resource.cache_hit:
                cache_hit_count += 1
        
        # 计算平均值
        stats["avg_duration"] = total_duration / len(self.resources)
        stats["success_rate"] = (success_count / len(self.resources)) * 100
        stats["cache_hit_rate"] = (cache_hit_count / len(self.resources)) * 100
        
        # 计算各类型的平均时长
        for type_name in stats["by_type"]:
            count = stats["by_type"][type_name]["count"]
            total_size = stats["by_type"][type_name]["total_size"]
            stats["by_type"][type_name]["avg_size"] = total_size / count if count > 0 else 0
        
        return stats
    
    def get_error_stats(self) -> Dict[str, Any]:
        """
        获取错误统计
        
        Returns:
            错误统计字典
        """
        stats = {
            "total": len(self.errors),
            "by_message": {},
            "recent": []
        }
        
        for error in self.errors[-10:]:  # 最近10条
            stats["recent"].append({
                "message": error.message[:100],
                "filename": error.filename,
                "timestamp": error.timestamp
            })
        
        for error in self.errors:
            if error.message not in stats["by_message"]:
                stats["by_message"][error.message] = 0
            stats["by_message"][error.message] += 1
        
        return stats
    
    def generate_report(self) -> WebPerformanceReport:
        """
        生成性能报告
        
        Returns:
            性能报告
        """
        vitals = self.get_current_vitals()
        score = self.get_vitals_score()
        resource_stats = self.get_resource_stats()
        error_stats = self.get_error_stats()
        
        summary = {
            "url": self.page_url,
            "session_id": self.session_id,
            "user_agent": self.user_agent,
            "overall_score": score.overall_score,
            "page_load_time": vitals.get("lcp", {}).get("value"),
            "resources_loaded": resource_stats["total"],
            "errors_count": error_stats["total"]
        }
        
        recommendations = self._generate_recommendations(vitals, resource_stats, error_stats)
        
        return WebPerformanceReport(
            summary=summary,
            vitals=vitals,
            resources=resource_stats,
            errors=error_stats,
            recommendations=recommendations,
            generated_at=time.time()
        )
    
    def _generate_recommendations(self, vitals: Dict[str, Any],
                                  resource_stats: Dict[str, Any],
                                  error_stats: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # LCP建议
        lcp = vitals.get("lcp", {})
        if lcp and lcp.get("rating") == "poor":
            recommendations.append("最大内容绘制(LCP)时间过长，建议优化图片加载、减少渲染阻塞资源")
        elif lcp and lcp.get("rating") == "needs_improvement":
            recommendations.append("最大内容绘制(LCP)需要改进，考虑优化服务器响应时间")
        
        # FID建议
        fid = vitals.get("fid", {})
        if fid and fid.get("rating") == "poor":
            recommendations.append("首次输入延迟(FID)过高，建议减少长任务、优化JavaScript执行")
        
        # CLS建议
        cls = vitals.get("cls", {})
        if cls and cls.get("rating") == "poor":
            recommendations.append("累积布局偏移(CLS)过高，建议为图片和广告预留空间")
        
        # 资源建议
        if resource_stats["total"] > 100:
            recommendations.append(f"页面加载了{resource_stats['total']}个资源，考虑合并或延迟加载非关键资源")
        
        if resource_stats["cache_hit_rate"] < 50:
            recommendations.append("缓存命中率较低，建议优化缓存策略")
        
        # 错误建议
        if error_stats["total"] > 10:
            recommendations.append(f"检测到{error_stats['total']}个JavaScript错误，建议修复")
        
        if not recommendations:
            recommendations.append("性能表现良好，继续保持！")
        
        return recommendations
    
    def add_listener(self, listener: Callable[[Dict[str, Any]], None]):
        """
        添加指标监听器
        
        Args:
            listener: 监听函数
        """
        self._listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[Dict[str, Any]], None]):
        """
        移除指标监听器
        
        Args:
            listener: 监听函数
        """
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def export_to_json(self, file_path: Optional[str] = None) -> str:
        """
        导出指标到JSON
        
        Args:
            file_path: 文件路径
        
        Returns:
            JSON字符串
        """
        import json
        
        data = {
            "session_id": self.session_id,
            "page_url": self.page_url,
            "user_agent": self.user_agent,
            "vitals": {
                name: [
                    {
                        "value": m.value,
                        "unit": m.unit,
                        "rating": m.rating,
                        "timestamp": m.timestamp
                    }
                    for m in values
                ]
                for name, values in self.vitals.items()
            },
            "resources": [
                {
                    "url": r.url,
                    "type": r.type.value,
                    "duration": r.duration,
                    "size": r.size,
                    "success": r.success,
                    "cache_hit": r.cache_hit,
                    "timestamp": r.timestamp
                }
                for r in self.resources[-100:]  # 最近100条
            ],
            "errors": [
                {
                    "message": e.message,
                    "filename": e.filename,
                    "lineno": e.lineno,
                    "timestamp": e.timestamp
                }
                for e in self.errors[-50:]  # 最近50条
            ],
            "report_generated": time.time()
        }
        
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            logger.info(f"Metrics exported to {file_path}")
        
        return json_str
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取指标收集器状态
        
        Returns:
            状态字典
        """
        return {
            "session_id": self.session_id,
            "page_url": self.page_url,
            "collecting": {
                "core_vitals": self.config.collect_core_vitals,
                "resources": self.config.collect_resources,
                "errors": self.config.collect_errors
            },
            "stats": {
                "vitals": {k: len(v) for k, v in self.vitals.items()},
                "resources": len(self.resources),
                "errors": len(self.errors),
                "user_timings": len(self.user_timings)
            },
            "current_vitals": self.get_current_vitals(),
            "resource_stats": self.get_resource_stats(),
            "error_stats": self.get_error_stats(),
            "queue_size": len(self._report_queue)
        }
    
    def shutdown(self):
        """关闭指标收集器"""
        logger.info("Shutting down WebMetrics...")
        
        # 停止自动上报
        self._stop_report.set()
        if self._report_thread and self._report_thread.is_alive():
            self._report_thread.join(timeout=2)
        
        # 清空队列
        self._report_queue.clear()
        
        # 清空数据
        self.vitals.clear()
        self.resources.clear()
        self.errors.clear()
        self.custom_marks.clear()
        self.custom_measures.clear()
        self._listeners.clear()
        
        logger.info("WebMetrics shutdown completed")

# 单例模式实现
_web_metrics_instance: Optional[WebMetrics] = None

def get_web_metrics(config: Optional[WebMetricsConfig] = None) -> WebMetrics:
    """
    获取Web指标收集器单例
    
    Args:
        config: 指标收集器配置
    
    Returns:
        Web指标收集器实例
    """
    global _web_metrics_instance
    if _web_metrics_instance is None:
        _web_metrics_instance = WebMetrics(config)
    return _web_metrics_instance

