"""
操作记录器：记录用户操作序列
"""
import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

class OperationType(Enum):
    """操作类型枚举"""
    MOUSE_CLICK = "mouse_click"
    MOUSE_MOVE = "mouse_move"
    MOUSE_SCROLL = "mouse_scroll"
    KEYBOARD_INPUT = "keyboard_input"
    APPLICATION_LAUNCH = "application_launch"
    APPLICATION_CLOSE = "application_close"
    FILE_OPERATION = "file_operation"
    SYSTEM_COMMAND = "system_command"

@dataclass
class OperationRecord:
    """操作记录"""
    id: str
    type: OperationType
    timestamp: float
    details: Dict[str, Any]
    application: Optional[str] = None
    window_title: Optional[str] = None
    screenshot_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['type'] = self.type.value
        return data

class OperationRecorder:
    """操作记录器"""
    
    def __init__(self):
        self.is_recording = False
        self.records: List[OperationRecord] = []
        self.record_lock = threading.Lock()
        self.hooks = {}
        self._setup_logging()
        self._initialize_hooks()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _initialize_hooks(self):
        """初始化钩子"""
        self.hooks = {
            OperationType.MOUSE_CLICK: self._record_mouse_click,
            OperationType.MOUSE_MOVE: self._record_mouse_move,
            OperationType.KEYBOARD_INPUT: self._record_keyboard_input,
            OperationType.APPLICATION_LAUNCH: self._record_application_launch,
            OperationType.APPLICATION_CLOSE: self._record_application_close
        }
    
    def start_recording(self) -> bool:
        """开始记录操作"""
        if self.is_recording:
            return False
        
        try:
            self.is_recording = True
            self.records.clear()
            
            # 安装钩子
            self._install_hooks()
            
            logger.info("开始记录用户操作")
            return True
            
        except Exception as e:
            logger.error(f"开始记录操作失败: {str(e)}")
            return False
    
    def stop_recording(self) -> bool:
        """停止记录操作"""
        if not self.is_recording:
            return False
        
        try:
            self.is_recording = False
            self._uninstall_hooks()
            
            logger.info(f"停止记录用户操作，共记录 {len(self.records)} 个操作")
            return True
            
        except Exception as e:
            logger.error(f"停止记录操作失败: {str(e)}")
            return False
    
    def _install_hooks(self):
        """安装钩子"""
        try:
            import pyautogui
            import keyboard
            
            # 键盘钩子
            keyboard.hook(self._keyboard_event_handler)
            
            # 鼠标钩子需要额外的库，这里使用轮询方式
            self.mouse_listener_thread = threading.Thread(
                target=self._mouse_listener_loop,
                daemon=True
            )
            self.mouse_listener_thread.start()
            
        except ImportError as e:
            logger.warning(f"无法安装钩子，缺少依赖: {str(e)}")
    
    def _uninstall_hooks(self):
        """卸载钩子"""
        try:
            import keyboard
            keyboard.unhook_all()
        except ImportError:
            pass
    
    def _keyboard_event_handler(self, event):
        """键盘事件处理器"""
        if not self.is_recording:
            return
        
        try:
            if event.event_type == 'down':
                record = OperationRecord(
                    id=str(len(self.records)),
                    type=OperationType.KEYBOARD_INPUT,
                    timestamp=time.time(),
                    details={
                        'key': event.name,
                        'scan_code': event.scan_code,
                        'is_keypad': event.is_keypad
                    }
                )
                
                self._add_record(record)
                
        except Exception as e:
            logger.error(f"处理键盘事件失败: {str(e)}")
    
    def _mouse_listener_loop(self):
        """鼠标监听循环"""
        import pyautogui
        
        last_click_time = 0
        click_debounce = 0.3  # 防抖时间
        
        while self.is_recording:
            try:
                current_time = time.time()
                
                # 检查鼠标点击
                if pyautogui.mouseInfo() != None:  # 简化检查，实际需要更复杂的实现
                    if current_time - last_click_time > click_debounce:
                        # 记录鼠标点击
                        x, y = pyautogui.position()
                        record = OperationRecord(
                            id=str(len(self.records)),
                            type=OperationType.MOUSE_CLICK,
                            timestamp=current_time,
                            details={
                                'x': x,
                                'y': y,
                                'button': 'left'  # 简化，实际需要检测具体按钮
                            }
                        )
                        
                        self._add_record(record)
                        last_click_time = current_time
                
                time.sleep(0.1)  # 降低CPU使用率
                
            except Exception as e:
                logger.error(f"鼠标监听错误: {str(e)}")
                time.sleep(1)
    
    def _add_record(self, record: OperationRecord):
        """添加操作记录"""
        with self.record_lock:
            self.records.append(record)
        
        logger.debug(f"记录操作: {record.type.value}")
    
    def _record_mouse_click(self, x: int, y: int, button: str):
        """记录鼠标点击"""
        record = OperationRecord(
            id=str(len(self.records)),
            type=OperationType.MOUSE_CLICK,
            timestamp=time.time(),
            details={'x': x, 'y': y, 'button': button}
        )
        self._add_record(record)
    
    def _record_mouse_move(self, x: int, y: int):
        """记录鼠标移动"""
        record = OperationRecord(
            id=str(len(self.records)),
            type=OperationType.MOUSE_MOVE,
            timestamp=time.time(),
            details={'x': x, 'y': y}
        )
        self._add_record(record)
    
    def _record_keyboard_input(self, key: str):
        """记录键盘输入"""
        record = OperationRecord(
            id=str(len(self.records)),
            type=OperationType.KEYBOARD_INPUT,
            timestamp=time.time(),
            details={'key': key}
        )
        self._add_record(record)
    
    def _record_application_launch(self, app_name: str):
        """记录应用程序启动"""
        record = OperationRecord(
            id=str(len(self.records)),
            type=OperationType.APPLICATION_LAUNCH,
            timestamp=time.time(),
            details={'application_name': app_name}
        )
        self._add_record(record)
    
    def _record_application_close(self, app_name: str):
        """记录应用程序关闭"""
        record = OperationRecord(
            id=str(len(self.records)),
            type=OperationType.APPLICATION_CLOSE,
            timestamp=time.time(),
            details={'application_name': app_name}
        )
        self._add_record(record)
    
    def get_records(self, start_time: float = None, end_time: float = None) -> List[OperationRecord]:
        """获取操作记录"""
        with self.record_lock:
            if start_time is None and end_time is None:
                return self.records.copy()
            
            filtered_records = []
            for record in self.records:
                if start_time and record.timestamp < start_time:
                    continue
                if end_time and record.timestamp > end_time:
                    continue
                filtered_records.append(record)
            
            return filtered_records
    
    def clear_records(self):
        """清空操作记录"""
        with self.record_lock:
            self.records.clear()
        logger.info("清空操作记录")
    
    def export_records(self, file_path: str, format: str = 'json') -> bool:
        """导出操作记录"""
        try:
            records_data = [record.to_dict() for record in self.records]
            
            if format.lower() == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(records_data, f, indent=2, ensure_ascii=False)
            else:
                return False
            
            logger.info(f"成功导出 {len(records_data)} 条操作记录到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出操作记录失败: {str(e)}")
            return False
    
    def import_records(self, file_path: str) -> bool:
        """导入操作记录"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                records_data = json.load(f)
            
            imported_records = []
            for record_data in records_data:
                record = OperationRecord(
                    id=record_data['id'],
                    type=OperationType(record_data['type']),
                    timestamp=record_data['timestamp'],
                    details=record_data['details'],
                    application=record_data.get('application'),
                    window_title=record_data.get('window_title'),
                    screenshot_path=record_data.get('screenshot_path')
                )
                imported_records.append(record)
            
            with self.record_lock:
                self.records.extend(imported_records)
            
            logger.info(f"成功导入 {len(imported_records)} 条操作记录")
            return True
            
        except Exception as e:
            logger.error(f"导入操作记录失败: {str(e)}")
            return False
    
    def take_screenshot(self, record_id: str) -> bool:
        """为操作记录拍摄截图"""
        try:
            import pyautogui
            
            screenshot = pyautogui.screenshot()
            screenshot_path = f"screenshots/operation_{record_id}_{int(time.time())}.png"
            
            # 确保目录存在
            Path("screenshots").mkdir(exist_ok=True)
            
            screenshot.save(screenshot_path)
            
            # 更新记录
            with self.record_lock:
                for record in self.records:
                    if record.id == record_id:
                        record.screenshot_path = screenshot_path
                        break
            
            return True
            
        except Exception as e:
            logger.error(f"拍摄截图失败: {str(e)}")
            return False
    
    def generate_macro(self) -> List[Dict[str, Any]]:
        """根据操作记录生成宏"""
        macro_actions = []
        
        for record in self.records:
            action = self._convert_record_to_action(record)
            if action:
                macro_actions.append(action)
        
        return macro_actions
    
    def _convert_record_to_action(self, record: OperationRecord) -> Optional[Dict[str, Any]]:
        """将操作记录转换为宏动作"""
        if record.type == OperationType.MOUSE_CLICK:
            return {
                'type': 'mouse_click',
                'params': {
                    'x': record.details.get('x'),
                    'y': record.details.get('y'),
                    'button': record.details.get('button', 'left')
                }
            }
        elif record.type == OperationType.KEYBOARD_INPUT:
            return {
                'type': 'keyboard_input',
                'params': {
                    'text': record.details.get('key')
                }
            }
        elif record.type == OperationType.APPLICATION_LAUNCH:
            return {
                'type': 'launch_application',
                'params': {
                    'application_name': record.details.get('application_name')
                }
            }
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取操作统计信息"""
        with self.record_lock:
            total_records = len(self.records)
            
            type_counts = {}
            for record in self.records:
                type_name = record.type.value
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
            if self.records:
                start_time = min(record.timestamp for record in self.records)
                end_time = max(record.timestamp for record in self.records)
                duration = end_time - start_time
            else:
                duration = 0
            
            return {
                'total_operations': total_records,
                'operation_types': type_counts,
                'duration_seconds': duration,
                'operations_per_minute': total_records / (duration / 60) if duration > 0 else 0
            }

# 单例实例
_operation_recorder_instance = None

def get_operation_recorder() -> OperationRecorder:
    """获取操作记录器单例"""
    global _operation_recorder_instance
    if _operation_recorder_instance is None:
        _operation_recorder_instance = OperationRecorder()
    return _operation_recorder_instance

