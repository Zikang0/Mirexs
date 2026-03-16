"""
日志工具模块

提供日志管理、格式化、轮转、分析等功能
"""

import os
import sys
import logging
import logging.handlers
import json
import time
import gzip
import shutil
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import traceback
import threading
from collections import deque
import re


class LogFormatter(logging.Formatter):
    """日志格式化器"""
    
    def __init__(self, fmt: str = None, datefmt: str = None, 
                 json_format: bool = False, include_metadata: bool = True):
        """初始化日志格式化器
        
        Args:
            fmt: 格式字符串
            datefmt: 日期格式
            json_format: 是否使用JSON格式
            include_metadata: 是否包含元数据
        """
        super().__init__(fmt, datefmt)
        self.json_format = json_format
        self.include_metadata = include_metadata
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        if self.json_format:
            return self._format_json(record)
        return super().format(record)
    
    def _format_json(self, record: logging.LogRecord) -> str:
        """JSON格式"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread
        }
        
        if self.include_metadata:
            if hasattr(record, 'metadata'):
                log_data['metadata'] = record.metadata
            
            if record.exc_info:
                log_data['exception'] = {
                    'type': record.exc_info[0].__name__,
                    'message': str(record.exc_info[1]),
                    'traceback': traceback.format_exception(*record.exc_info)
                }
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'        # 重置
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        log_message = super().format(record)
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        return f"{color}{log_message}{self.COLORS['RESET']}"


class RotatingFileHandler(logging.handlers.RotatingFileHandler):
    """增强的轮转文件处理器"""
    
    def __init__(self, filename: str, mode: str = 'a', max_bytes: int = 0,
                 backup_count: int = 0, encoding: str = None, delay: bool = False,
                 compress: bool = False):
        """初始化轮转文件处理器
        
        Args:
            filename: 日志文件名
            mode: 文件模式
            max_bytes: 最大文件大小
            backup_count: 备份文件数量
            encoding: 编码
            delay: 延迟打开文件
            compress: 是否压缩备份文件
        """
        super().__init__(filename, mode, max_bytes, backup_count, encoding, delay)
        self.compress = compress
    
    def doRollover(self):
        """执行轮转"""
        if self.stream:
            self.stream.close()
            self.stream = None
        
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self.rotation_filename("%s.%d" % (self.baseFilename, i))
                dfn = self.rotation_filename("%s.%d" % (self.baseFilename, i + 1))
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            
            dfn = self.rotation_filename(self.baseFilename + ".1")
            if os.path.exists(dfn):
                os.remove(dfn)
            self.rotate(self.baseFilename, dfn)
            
            # 压缩备份文件
            if self.compress:
                for i in range(1, self.backupCount + 1):
                    backup_file = self.rotation_filename("%s.%d" % (self.baseFilename, i))
                    if os.path.exists(backup_file) and not backup_file.endswith('.gz'):
                        self._compress_file(backup_file)
        
        if not self.delay:
            self.stream = self._open()
    
    def _compress_file(self, filename: str):
        """压缩文件"""
        try:
            with open(filename, 'rb') as f_in:
                with gzip.open(f'{filename}.gz', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(filename)
        except Exception as e:
            print(f"压缩日志文件失败 {filename}: {e}")


class TimeRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """时间轮转文件处理器"""
    
    def __init__(self, filename: str, when: str = 'midnight', interval: int = 1,
                 backup_count: int = 0, encoding: str = None, delay: bool = False,
                 utc: bool = False, at_time: Optional[datetime] = None,
                 compress: bool = False):
        """初始化时间轮转文件处理器"""
        super().__init__(filename, when, interval, backup_count, encoding, delay, utc, at_time)
        self.compress = compress
    
    def doRollover(self):
        """执行轮转"""
        super().doRollover()
        
        if self.compress:
            for i in range(1, self.backupCount + 1):
                backup_file = self.rotation_filename(f"{self.baseFilename}.{self.suffix}" % i)
                if os.path.exists(backup_file) and not backup_file.endswith('.gz'):
                    self._compress_file(backup_file)
    
    def _compress_file(self, filename: str):
        """压缩文件"""
        try:
            with open(filename, 'rb') as f_in:
                with gzip.open(f'{filename}.gz', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(filename)
        except Exception as e:
            print(f"压缩日志文件失败 {filename}: {e}")


class LoggerManager:
    """日志管理器"""
    
    def __init__(self, log_dir: str = 'logs', app_name: str = 'app'):
        """初始化日志管理器
        
        Args:
            log_dir: 日志目录
            app_name: 应用名称
        """
        self.log_dir = log_dir
        self.app_name = app_name
        self.loggers = {}
        self.handlers = []
        self._ensure_log_dir()
    
    def _ensure_log_dir(self):
        """确保日志目录存在"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def get_logger(self, name: str, level: str = 'INFO',
                   use_json: bool = False, use_color: bool = False,
                   propagate: bool = True) -> logging.Logger:
        """获取日志器
        
        Args:
            name: 日志器名称
            level: 日志级别
            use_json: 是否使用JSON格式
            use_color: 是否使用彩色输出
            propagate: 是否传播到父日志器
            
        Returns:
            日志器对象
        """
        if name in self.loggers:
            return self.loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        logger.propagate = propagate
        
        # 清除已有的处理器
        logger.handlers.clear()
        
        # 添加控制台处理器
        console_handler = self._create_console_handler(level, use_json, use_color)
        logger.addHandler(console_handler)
        self.handlers.append(console_handler)
        
        # 添加文件处理器
        file_handler = self._create_file_handler(name, level, use_json)
        logger.addHandler(file_handler)
        self.handlers.append(file_handler)
        
        self.loggers[name] = logger
        return logger
    
    def _create_console_handler(self, level: str, use_json: bool, use_color: bool) -> logging.Handler:
        """创建控制台处理器"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper()))
        
        if use_json:
            formatter = LogFormatter(json_format=True)
        elif use_color:
            formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                '%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = LogFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                '%Y-%m-%d %H:%M:%S'
            )
        
        handler.setFormatter(formatter)
        return handler
    
    def _create_file_handler(self, name: str, level: str, use_json: bool) -> logging.Handler:
        """创建文件处理器"""
        log_file = os.path.join(self.log_dir, f"{name}.log")
        
        handler = RotatingFileHandler(
            log_file,
            max_bytes=10*1024*1024,  # 10MB
            backup_count=5,
            compress=True,
            encoding='utf-8'
        )
        handler.setLevel(getattr(logging, level.upper()))
        
        if use_json:
            formatter = LogFormatter(json_format=True)
        else:
            formatter = LogFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                '%Y-%m-%d %H:%M:%S'
            )
        
        handler.setFormatter(formatter)
        return handler
    
    def add_custom_handler(self, handler: logging.Handler):
        """添加自定义处理器"""
        for logger in self.loggers.values():
            logger.addHandler(handler)
        self.handlers.append(handler)
    
    def set_level(self, level: str):
        """设置所有日志器的级别"""
        for logger in self.loggers.values():
            logger.setLevel(getattr(logging, level.upper()))
    
    def shutdown(self):
        """关闭所有处理器"""
        for handler in self.handlers:
            handler.close()


class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self, log_dir: str = 'logs'):
        """初始化日志分析器
        
        Args:
            log_dir: 日志目录
        """
        self.log_dir = log_dir
        self.log_files = self._find_log_files()
    
    def _find_log_files(self) -> List[str]:
        """查找日志文件"""
        log_files = []
        if os.path.exists(self.log_dir):
            for file in os.listdir(self.log_dir):
                if file.endswith('.log') or file.endswith('.log.gz'):
                    log_files.append(os.path.join(self.log_dir, file))
        return sorted(log_files)
    
    def analyze_logs(self, hours: int = 24) -> Dict[str, Any]:
        """分析日志
        
        Args:
            hours: 分析最近多少小时的日志
            
        Returns:
            分析结果
        """
        cutoff_time = time.time() - hours * 3600
        results = {
            'total_lines': 0,
            'errors': [],
            'warnings': [],
            'level_counts': {},
            'top_errors': [],
            'error_rate': 0,
            'time_range': {
                'start': None,
                'end': None
            }
        }
        
        error_counts = {}
        
        for log_file in self.log_files:
            file_lines = self._analyze_file(log_file, cutoff_time, results, error_counts)
            results['total_lines'] += file_lines
        
        # 统计错误率
        if results['total_lines'] > 0:
            error_count = sum(results['level_counts'].get(level, 0) 
                            for level in ['ERROR', 'CRITICAL'])
            results['error_rate'] = error_count / results['total_lines'] * 100
        
        # 找出最常见的错误
        results['top_errors'] = sorted(
            [{'error': k, 'count': v} for k, v in error_counts.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]
        
        return results
    
    def _analyze_file(self, file_path: str, cutoff_time: float, 
                     results: Dict[str, Any], error_counts: Dict[str, int]) -> int:
        """分析单个日志文件"""
        lines = 0
        
        # 打开文件（支持gzip压缩）
        open_func = gzip.open if file_path.endswith('.gz') else open
        
        try:
            with open_func(file_path, 'rt', encoding='utf-8') as f:
                for line in f:
                    lines += 1
                    
                    # 尝试解析日志
                    log_entry = self._parse_log_line(line)
                    if not log_entry:
                        continue
                    
                    # 检查时间范围
                    if log_entry['timestamp'] < cutoff_time:
                        continue
                    
                    # 更新时间范围
                    if not results['time_range']['start'] or log_entry['timestamp'] < results['time_range']['start']:
                        results['time_range']['start'] = log_entry['timestamp']
                    if not results['time_range']['end'] or log_entry['timestamp'] > results['time_range']['end']:
                        results['time_range']['end'] = log_entry['timestamp']
                    
                    # 统计日志级别
                    level = log_entry['level']
                    results['level_counts'][level] = results['level_counts'].get(level, 0) + 1
                    
                    # 收集错误
                    if level in ['ERROR', 'CRITICAL']:
                        error_counts[log_entry['message']] = error_counts.get(log_entry['message'], 0) + 1
                        
                        results['errors'].append({
                            'timestamp': datetime.fromtimestamp(log_entry['timestamp']).isoformat(),
                            'level': level,
                            'logger': log_entry.get('logger', 'unknown'),
                            'message': log_entry['message']
                        })
                    
                    # 收集警告
                    elif level == 'WARNING':
                        results['warnings'].append({
                            'timestamp': datetime.fromtimestamp(log_entry['timestamp']).isoformat(),
                            'message': log_entry['message']
                        })
        
        except Exception as e:
            print(f"分析日志文件失败 {file_path}: {e}")
        
        return lines
    
    def _parse_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """解析日志行"""
        # 尝试解析JSON格式
        if line.strip().startswith('{') and line.strip().endswith('}'):
            try:
                data = json.loads(line)
                if 'timestamp' in data:
                    data['timestamp'] = datetime.fromisoformat(data['timestamp']).timestamp()
                return data
            except:
                pass
        
        # 尝试解析普通格式
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (\w+) - (\w+) - (.*)'
        match = re.match(pattern, line)
        if match:
            timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S').timestamp()
            return {
                'timestamp': timestamp,
                'logger': match.group(2),
                'level': match.group(3),
                'message': match.group(4)
            }
        
        return None
    
    def get_error_timeline(self, hours: int = 24) -> Dict[str, Any]:
        """获取错误时间线"""
        results = self.analyze_logs(hours)
        
        if not results['time_range']['start']:
            return {}
        
        start_time = results['time_range']['start']
        end_time = results['time_range']['end']
        
        # 按小时分组
        timeline = {}
        current = start_time
        hour_seconds = 3600
        
        while current <= end_time:
            hour_key = datetime.fromtimestamp(current).strftime('%Y-%m-%d %H:00')
            timeline[hour_key] = 0
            current += hour_seconds
        
        # 统计每个小时的错误数
        for error in results['errors']:
            hour_key = datetime.fromtimestamp(error['timestamp']).strftime('%Y-%m-%d %H:00')
            if hour_key in timeline:
                timeline[hour_key] += 1
        
        return {
            'timeline': timeline,
            'total_errors': len(results['errors']),
            'period_hours': hours
        }
    
    def generate_report(self, hours: int = 24) -> str:
        """生成分析报告"""
        results = self.analyze_logs(hours)
        
        report = []
        report.append("=" * 60)
        report.append("日志分析报告")
        report.append("=" * 60)
        report.append(f"分析时间段: {datetime.fromtimestamp(results['time_range']['start'])} - {datetime.fromtimestamp(results['time_range']['end'])}")
        report.append(f"总日志行数: {results['total_lines']}")
        report.append(f"错误率: {results['error_rate']:.2f}%")
        report.append("")
        
        report.append("日志级别统计:")
        for level, count in results['level_counts'].items():
            report.append(f"  {level}: {count}")
        
        if results['top_errors']:
            report.append("")
            report.append("最常见的错误:")
            for i, error in enumerate(results['top_errors'][:5], 1):
                report.append(f"  {i}. {error['error'][:100]}... ({error['count']}次)")
        
        return "\n".join(report)


class LogTail:
    """日志跟踪器"""
    
    def __init__(self, file_path: str, encoding: str = 'utf-8'):
        """初始化日志跟踪器
        
        Args:
            file_path: 日志文件路径
            encoding: 编码
        """
        self.file_path = file_path
        self.encoding = encoding
        self.file = None
        self.position = 0
    
    def start_tailing(self):
        """开始跟踪"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"日志文件不存在: {self.file_path}")
        
        self.file = open(self.file_path, 'r', encoding=self.encoding)
        self.file.seek(0, os.SEEK_END)
        self.position = self.file.tell()
    
    def get_new_lines(self) -> List[str]:
        """获取新增的行"""
        if not self.file:
            return []
        
        lines = self.file.readlines()
        if lines:
            self.position = self.file.tell()
        
        return [line.rstrip('\n') for line in lines]
    
    def follow(self, callback: Optional[callable] = None, interval: float = 0.1):
        """持续跟踪日志
        
        Args:
            callback: 回调函数，处理新行
            interval: 检查间隔
        """
        self.start_tailing()
        
        try:
            while True:
                lines = self.get_new_lines()
                if lines:
                    if callback:
                        for line in lines:
                            callback(line)
                    else:
                        for line in lines:
                            print(line)
                time.sleep(interval)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_tailing()
    
    def stop_tailing(self):
        """停止跟踪"""
        if self.file:
            self.file.close()
            self.file = None


def setup_logging(config: Dict[str, Any]) -> LoggerManager:
    """设置日志系统"""
    manager = LoggerManager(
        log_dir=config.get('log_dir', 'logs'),
        app_name=config.get('app_name', 'app')
    )
    
    # 配置根日志器
    root_logger = manager.get_logger(
        config.get('root_logger', 'root'),
        level=config.get('level', 'INFO'),
        use_json=config.get('use_json', False),
        use_color=config.get('use_color', False)
    )
    
    return manager


def log_function_call(logger: logging.Logger, level: str = 'DEBUG'):
    """函数调用日志装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.log(
                getattr(logging, level.upper()),
                f"调用函数 {func.__name__} - args: {args}, kwargs: {kwargs}"
            )
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.log(
                    getattr(logging, level.upper()),
                    f"函数 {func.__name__} 完成 - 耗时: {elapsed:.3f}s"
                )
                return result
            except Exception as e:
                logger.error(f"函数 {func.__name__} 失败: {e}")
                raise
        return wrapper
    return decorator