"""
UI自动化：用户界面自动化
"""
import time
import pyautogui
import pygetwindow as gw
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import threading

logger = logging.getLogger(__name__)

class UIElementType(Enum):
    """UI元素类型枚举"""
    BUTTON = "button"
    TEXT_FIELD = "text_field"
    CHECKBOX = "checkbox"
    DROPDOWN = "dropdown"
    MENU_ITEM = "menu_item"
    ICON = "icon"
    LINK = "link"
    IMAGE = "image"

@dataclass
class UIElement:
    """UI元素"""
    name: str
    element_type: UIElementType
    position: Tuple[int, int]  # (x, y)
    size: Tuple[int, int]      # (width, height)
    confidence: float = 1.0
    image_template: Optional[str] = None
    text: Optional[str] = None

class UIAutomation:
    """UI自动化类"""
    
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self.element_templates: Dict[str, UIElement] = {}
        self.ocr_engine = None
        self._setup_logging()
        self._initialize_ui_automation()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _initialize_ui_automation(self):
        """初始化UI自动化"""
        try:
            # 设置pyautogui安全设置
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
            
            # 初始化OCR引擎（如果可用）
            self._initialize_ocr()
            
            logger.info("UI自动化初始化完成")
            
        except Exception as e:
            logger.error(f"UI自动化初始化失败: {str(e)}")
    
    def _initialize_ocr(self):
        """初始化OCR引擎"""
        try:
            # 尝试导入pytesseract
            import pytesseract
            self.ocr_engine = pytesseract
            logger.info("OCR引擎初始化成功")
        except ImportError:
            logger.warning("未找到OCR引擎，文本识别功能不可用")
            self.ocr_engine = None
    
    def find_element_by_image(self, image_path: str, confidence: float = 0.8) -> Optional[UIElement]:
        """通过图像模板查找UI元素"""
        try:
            if not Path(image_path).exists():
                logger.error(f"图像模板不存在: {image_path}")
                return None
            
            # 截取屏幕截图
            screenshot = pyautogui.screenshot()
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # 加载模板图像
            template = cv2.imread(image_path)
            if template is None:
                logger.error(f"无法加载模板图像: {image_path}")
                return None
            
            # 模板匹配
            result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= confidence:
                x, y = max_loc
                h, w = template.shape[:2]
                
                element = UIElement(
                    name=Path(image_path).stem,
                    element_type=UIElementType.BUTTON,
                    position=(x + w//2, y + h//2),  # 中心点坐标
                    size=(w, h),
                    confidence=max_val,
                    image_template=image_path
                )
                
                logger.info(f"找到UI元素: {element.name}, 置信度: {max_val:.2f}")
                return element
            else:
                logger.debug(f"未找到匹配的UI元素，最高置信度: {max_val:.2f}")
                return None
            
        except Exception as e:
            logger.error(f"图像查找UI元素失败: {str(e)}")
            return None
    
    def find_element_by_text(self, text: str, region: Tuple[int, int, int, int] = None) -> Optional[UIElement]:
        """通过文本查找UI元素"""
        try:
            if self.ocr_engine is None:
                logger.warning("OCR引擎未初始化")
                return None
            
            # 截取屏幕区域
            if region:
                x, y, width, height = region
                screenshot = pyautogui.screenshot(region=(x, y, width, height))
            else:
                screenshot = pyautogui.screenshot()
            
            # 使用OCR识别文本
            ocr_result = self.ocr_engine.image_to_data(screenshot, output_type=self.ocr_engine.Output.DICT)
            
            # 查找匹配的文本
            for i, ocr_text in enumerate(ocr_result['text']):
                if text.lower() in ocr_text.lower():
                    x = ocr_result['left'][i]
                    y = ocr_result['top'][i]
                    w = ocr_result['width'][i]
                    h = ocr_result['height'][i]
                    confidence = ocr_result['conf'][i] / 100.0
                    
                    # 调整坐标（如果指定了区域）
                    if region:
                        x += region[0]
                        y += region[1]
                    
                    element = UIElement(
                        name=f"text_{text}",
                        element_type=UIElementType.TEXT_FIELD,
                        position=(x + w//2, y + h//2),
                        size=(w, h),
                        confidence=confidence,
                        text=ocr_text
                    )
                    
                    logger.info(f"找到文本元素: {text}, 置信度: {confidence:.2f}")
                    return element
            
            return None
            
        except Exception as e:
            logger.error(f"文本查找UI元素失败: {str(e)}")
            return None
    
    def click_element(self, element: UIElement, button: str = 'left', clicks: int = 1) -> bool:
        """点击UI元素"""
        try:
            x, y = element.position
            pyautogui.click(x, y, button=button, clicks=clicks)
            
            logger.info(f"点击UI元素: {element.name} 在位置 ({x}, {y})")
            return True
            
        except Exception as e:
            logger.error(f"点击UI元素失败: {str(e)}")
            return False
    
    def double_click_element(self, element: UIElement) -> bool:
        """双击UI元素"""
        return self.click_element(element, clicks=2)
    
    def right_click_element(self, element: UIElement) -> bool:
        """右键点击UI元素"""
        return self.click_element(element, button='right')
    
    def type_text(self, element: UIElement, text: str, interval: float = 0.1) -> bool:
        """在UI元素中输入文本"""
        try:
            # 首先点击元素获取焦点
            self.click_element(element)
            time.sleep(0.5)  # 等待焦点获取
            
            # 输入文本
            pyautogui.write(text, interval=interval)
            
            logger.info(f"在元素 {element.name} 中输入文本: {text}")
            return True
            
        except Exception as e:
            logger.error(f"输入文本失败: {str(e)}")
            return False
    
    def drag_and_drop(self, from_element: UIElement, to_element: UIElement) -> bool:
        """拖放操作"""
        try:
            from_x, from_y = from_element.position
            to_x, to_y = to_element.position
            
            pyautogui.moveTo(from_x, from_y)
            pyautogui.mouseDown()
            pyautogui.moveTo(to_x, to_y, duration=0.5)
            pyautogui.mouseUp()
            
            logger.info(f"拖放操作: {from_element.name} -> {to_element.name}")
            return True
            
        except Exception as e:
            logger.error(f"拖放操作失败: {str(e)}")
            return False
    
    def scroll_element(self, element: UIElement, clicks: int) -> bool:
        """滚动UI元素"""
        try:
            x, y = element.position
            pyautogui.moveTo(x, y)
            pyautogui.scroll(clicks)
            
            logger.info(f"滚动元素 {element.name}: {clicks} 次")
            return True
            
        except Exception as e:
            logger.error(f"滚动元素失败: {str(e)}")
            return False
    
    def get_window_info(self, window_title: str) -> Optional[Dict[str, Any]]:
        """获取窗口信息"""
        try:
            windows = gw.getWindowsWithTitle(window_title)
            if windows:
                window = windows[0]
                return {
                    'title': window.title,
                    'position': (window.left, window.top),
                    'size': (window.width, window.height),
                    'is_minimized': window.isMinimized,
                    'is_maximized': window.isMaximized
                }
            return None
            
        except Exception as e:
            logger.error(f"获取窗口信息失败: {str(e)}")
            return None
    
    def activate_window(self, window_title: str) -> bool:
        """激活窗口"""
        try:
            windows = gw.getWindowsWithTitle(window_title)
            if windows:
                window = windows[0]
                if window.isMinimized:
                    window.restore()
                window.activate()
                
                logger.info(f"激活窗口: {window_title}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"激活窗口失败: {str(e)}")
            return False
    
    def maximize_window(self, window_title: str) -> bool:
        """最大化窗口"""
        try:
            windows = gw.getWindowsWithTitle(window_title)
            if windows:
                window = windows[0]
                window.maximize()
                logger.info(f"最大化窗口: {window_title}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"最大化窗口失败: {str(e)}")
            return False
    
    def minimize_window(self, window_title: str) -> bool:
        """最小化窗口"""
        try:
            windows = gw.getWindowsWithTitle(window_title)
            if windows:
                window = windows[0]
                window.minimize()
                logger.info(f"最小化窗口: {window_title}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"最小化窗口失败: {str(e)}")
            return False
    
    def take_screenshot(self, save_path: str, region: Tuple[int, int, int, int] = None) -> bool:
        """拍摄屏幕截图"""
        try:
            screenshot = pyautogui.screenshot(region=region)
            screenshot.save(save_path)
            logger.info(f"屏幕截图保存到: {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"拍摄屏幕截图失败: {str(e)}")
            return False
    
    def record_ui_interaction(self, duration: float = 10.0) -> List[Dict[str, Any]]:
        """记录UI交互"""
        try:
            from .operation_recorder import get_operation_recorder
            
            recorder = get_operation_recorder()
            if not recorder.start_recording():
                return []
            
            time.sleep(duration)
            recorder.stop_recording()
            
            records = recorder.get_records()
            ui_interactions = []
            
            for record in records:
                interaction = {
                    'type': record.type.value,
                    'timestamp': record.timestamp,
                    'details': record.details
                }
                ui_interactions.append(interaction)
            
            return ui_interactions
            
        except Exception as e:
            logger.error(f"记录UI交互失败: {str(e)}")
            return []
    
    def wait_for_element(self, find_function: Callable, timeout: float = 10.0, 
                        interval: float = 0.5, **kwargs) -> Optional[UIElement]:
        """等待UI元素出现"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            element = find_function(**kwargs)
            if element:
                return element
            time.sleep(interval)
        
        logger.warning(f"等待UI元素超时 ({timeout}秒)")
        return None
    
    def highlight_element(self, element: UIElement, duration: float = 2.0) -> bool:
        """高亮显示UI元素"""
        try:
            # 这个功能需要图形界面支持
            # 这里实现一个简化的版本：在控制台输出信息
            logger.info(f"高亮元素: {element.name} 在位置 {element.position}")
            time.sleep(duration)
            return True
            
        except Exception as e:
            logger.error(f"高亮元素失败: {str(e)}")
            return False
    
    def get_screen_resolution(self) -> Tuple[int, int]:
        """获取屏幕分辨率"""
        return self.screen_width, self.screen_height
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """获取鼠标位置"""
        return pyautogui.position()
    
    def move_mouse_to(self, x: int, y: int, duration: float = 0.0) -> bool:
        """移动鼠标到指定位置"""
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return True
        except Exception as e:
            logger.error(f"移动鼠标失败: {str(e)}")
            return False

# 单例实例
_ui_automation_instance = None

def get_ui_automation() -> UIAutomation:
    """获取UI自动化单例"""
    global _ui_automation_instance
    if _ui_automation_instance is None:
        _ui_automation_instance = UIAutomation()
    return _ui_automation_instance

