"""
布局工具模块

提供UI布局管理的工具函数。
"""

from typing import Dict, List, Optional, Union, Any, Tuple
import tkinter as tk
from tkinter import ttk
import math


class LayoutManager:
    """布局管理器"""
    
    def __init__(self, parent_widget):
        """初始化布局管理器
        
        Args:
            parent_widget: 父容器控件
        """
        self.parent = parent_widget
        self.widgets = []
        self.layout_config = {}
    
    def add_widget(self, widget, row=0, column=0, sticky='nsew', 
                  padx=0, pady=0, rowspan=1, columnspan=1):
        """添加控件到布局
        
        Args:
            widget: 控件对象
            row: 行位置
            column: 列位置
            sticky: 粘性方向 ('n', 's', 'e', 'w', 'nw', 'ne', 'sw', 'se', 'nsew')
            padx: 水平内边距
            pady: 垂直内边距
            rowspan: 跨行数
            columnspan: 跨列数
        """
        layout_info = {
            'widget': widget,
            'row': row,
            'column': column,
            'sticky': sticky,
            'padx': padx,
            'pady': pady,
            'rowspan': rowspan,
            'columnspan': columnspan
        }
        
        self.widgets.append(layout_info)
        return layout_info
    
    def configure_grid(self, rows=None, columns=None):
        """配置网格
        
        Args:
            rows: 行配置字典 {行号: {'weight': 权重, 'minsize': 最小大小}}
            columns: 列配置字典 {列号: {'weight': 权重, 'minsize': 最小大小}}
        """
        if rows:
            for row, config in rows.items():
                self.parent.grid_rowconfigure(row, **config)
        
        if columns:
            for col, config in columns.items():
                self.parent.grid_columnconfigure(col, **config)
    
    def apply_layout(self):
        """应用布局"""
        for layout_info in self.widgets:
            widget = layout_info['widget']
            widget.grid(
                row=layout_info['row'],
                column=layout_info['column'],
                sticky=layout_info['sticky'],
                padx=layout_info['padx'],
                pady=layout_info['pady'],
                rowspan=layout_info['rowspan'],
                columnspan=layout_info['columnspan']
            )
    
    def clear_layout(self):
        """清除布局"""
        for layout_info in self.widgets:
            try:
                layout_info['widget'].grid_forget()
            except tk.TclError:
                pass
        self.widgets.clear()


class GridLayout:
    """网格布局管理器"""
    
    def __init__(self, parent, rows=1, columns=1):
        """初始化网格布局
        
        Args:
            parent: 父容器
            rows: 行数
            columns: 列数
        """
        self.parent = parent
        self.rows = rows
        self.columns = columns
        self.grid_data = [[None for _ in range(columns)] for _ in range(rows)]
        self.cell_configs = {}
    
    def place_widget(self, widget, row, column, rowspan=1, columnspan=1, 
                    sticky='nsew'):
        """放置控件
        
        Args:
            widget: 控件对象
            row: 行位置
            column: 列位置
            rowspan: 跨行数
            columnspan: 跨列数
            sticky: 粘性方向
        """
        # 检查边界
        if row + rowspan > self.rows or column + columnspan > self.columns:
            raise ValueError("控件位置超出网格范围")
        
        # 检查冲突
        for r in range(row, row + rowspan):
            for c in range(column, column + columnspan):
                if self.grid_data[r][c] is not None:
                    raise ValueError(f"位置 ({r}, {c}) 已被占用")
        
        # 放置控件
        widget.grid(
            row=row,
            column=column,
            rowspan=rowspan,
            columnspan=columnspan,
            sticky=sticky
        )
        
        # 记录位置信息
        for r in range(row, row + rowspan):
            for c in range(column, column + columnspan):
                self.grid_data[r][c] = widget
    
    def configure_cell(self, row, column, weight=0, minsize=0):
        """配置单元格
        
        Args:
            row: 行号
            column: 列号
            weight: 权重
            minsize: 最小大小
        """
        self.parent.grid_rowconfigure(row, weight=weight, minsize=minsize)
        self.parent.grid_columnconfigure(column, weight=weight, minsize=minsize)
    
    def get_occupied_cells(self) -> List[Tuple[int, int]]:
        """获取已占用的单元格位置
        
        Returns:
            已占用单元格位置列表
        """
        occupied = []
        for r in range(self.rows):
            for c in range(self.columns):
                if self.grid_data[r][c] is not None:
                    occupied.append((r, c))
        return occupied
    
    def clear_cell(self, row, column):
        """清除单元格
        
        Args:
            row: 行号
            column: 列号
        """
        if 0 <= row < self.rows and 0 <= column < self.columns:
            widget = self.grid_data[row][column]
            if widget:
                try:
                    widget.grid_forget()
                except tk.TclError:
                    pass
                self.grid_data[row][column] = None


class FlexLayout:
    """弹性布局管理器"""
    
    def __init__(self, parent, direction='row', gap=5, padding=5):
        """初始化弹性布局
        
        Args:
            parent: 父容器
            direction: 布局方向 ('row', 'column')
            gap: 控件间距
            padding: 内边距
        """
        self.parent = parent
        self.direction = direction
        self.gap = gap
        self.padding = padding
        self.widgets = []
        self.flex_configs = {}
    
    def add_widget(self, widget, flex=1, min_size=0):
        """添加控件
        
        Args:
            widget: 控件对象
            flex: 弹性系数
            min_size: 最小大小
        """
        self.widgets.append(widget)
        self.flex_configs[widget] = {
            'flex': flex,
            'min_size': min_size
        }
        
        # 根据方向使用不同的布局管理器
        if self.direction == 'row':
            widget.pack(side='left', padx=self.gap//2, pady=self.padding//2, 
                       fill='both', expand=True)
        else:
            widget.pack(side='top', padx=self.padding//2, pady=self.gap//2, 
                       fill='both', expand=True)
    
    def remove_widget(self, widget):
        """移除控件
        
        Args:
            widget: 要移除的控件
        """
        if widget in self.widgets:
            try:
                widget.pack_forget()
            except tk.TclError:
                pass
            self.widgets.remove(widget)
            if widget in self.flex_configs:
                del self.flex_configs[widget]
    
    def update_layout(self):
        """更新布局"""
        # 重新应用布局
        for widget in self.widgets:
            try:
                widget.pack_forget()
            except tk.TclError:
                pass
        
        for widget in self.widgets:
            if self.direction == 'row':
                widget.pack(side='left', padx=self.gap//2, pady=self.padding//2, 
                           fill='both', expand=True)
            else:
                widget.pack(side='top', padx=self.padding//2, pady=self.gap//2, 
                           fill='both', expand=True)


class ResponsiveLayout:
    """响应式布局管理器"""
    
    def __init__(self, parent):
        """初始化响应式布局
        
        Args:
            parent: 父容器
        """
        self.parent = parent
        self.breakpoints = {
            'mobile': 480,
            'tablet': 768,
            'desktop': 1024
        }
        self.layouts = {}
        self.current_layout = 'desktop'
    
    def add_breakpoint(self, name, width):
        """添加断点
        
        Args:
            name: 断点名称
            width: 断点宽度
        """
        self.breakpoints[name] = width
    
    def set_layout(self, breakpoint_name, layout_func):
        """设置断点布局
        
        Args:
            breakpoint_name: 断点名称
            layout_func: 布局函数
        """
        self.layouts[breakpoint_name] = layout_func
    
    def update_responsive_layout(self, width=None):
        """更新响应式布局
        
        Args:
            width: 当前宽度，如果为None则自动获取
        """
        if width is None:
            try:
                width = self.parent.winfo_width()
            except:
                width = 1024  # 默认宽度
        
        # 确定当前断点
        new_layout = 'desktop'
        for breakpoint_name, breakpoint_width in sorted(self.breakpoints.items()):
            if width <= breakpoint_width:
                new_layout = breakpoint_name
                break
        
        # 如果布局发生变化，更新布局
        if new_layout != self.current_layout and new_layout in self.layouts:
            self.current_layout = new_layout
            self.layouts[new_layout]()
    
    def bind_resize(self):
        """绑定窗口大小变化事件"""
        def on_resize(event):
            self.update_responsive_layout()
        
        self.parent.bind('<Configure>', on_resize)


class PanelLayout:
    """面板布局管理器"""
    
    def __init__(self, parent, orientation='horizontal', divider_size=5):
        """初始化面板布局
        
        Args:
            parent: 父容器
            orientation: 方向 ('horizontal', 'vertical')
            divider_size: 分隔条大小
        """
        self.parent = parent
        self.orientation = orientation
        self.divider_size = divider_size
        self.panels = []
        self.sashes = []
        self.ratios = []
    
    def add_panel(self, widget, ratio=1):
        """添加面板
        
        Args:
            widget: 面板控件
            ratio: 比例
        """
        self.panels.append(widget)
        self.ratios.append(ratio)
        
        # 使用PanedWindow管理面板
        if not hasattr(self, 'paned_window'):
            self.paned_window = tk.PanedWindow(
                self.parent, 
                orient='horizontal' if self.orientation == 'horizontal' else 'vertical',
                sashrelief='raised',
                sashwidth=self.divider_size
            )
            self.paned_window.pack(fill='both', expand=True)
        
        self.paned_window.add(widget, stretch='always')
    
    def remove_panel(self, index):
        """移除面板
        
        Args:
            index: 面板索引
        """
        if 0 <= index < len(self.panels):
            widget = self.panels[index]
            try:
                self.paned_window.forget(widget)
            except tk.TclError:
                pass
            self.panels.pop(index)
            self.ratios.pop(index)
    
    def set_panel_ratio(self, index, ratio):
        """设置面板比例
        
        Args:
            index: 面板索引
            ratio: 比例
        """
        if 0 <= index < len(self.ratios):
            self.ratios[index] = ratio
            self._update_ratios()
    
    def _update_ratios(self):
        """更新面板比例"""
        total_ratio = sum(self.ratios)
        if total_ratio > 0:
            for i, widget in enumerate(self.panels):
                try:
                    # 这里需要根据实际需要调整比例
                    pass
                except tk.TclError:
                    pass


class TabLayout:
    """标签页布局管理器"""
    
    def __init__(self, parent):
        """初始化标签页布局
        
        Args:
            parent: 父容器
        """
        self.parent = parent
        self.notebook = ttk.Notebook(parent)
        self.tabs = {}
        self.tab_order = []
    
    def add_tab(self, tab_id, title, widget=None):
        """添加标签页
        
        Args:
            tab_id: 标签页ID
            title: 标签页标题
            widget: 标签页内容控件
        """
        if widget is None:
            widget = ttk.Frame(self.notebook)
        
        self.notebook.add(widget, text=title)
        self.tabs[tab_id] = {
            'widget': widget,
            'title': title,
            'content': None
        }
        self.tab_order.append(tab_id)
    
    def remove_tab(self, tab_id):
        """移除标签页
        
        Args:
            tab_id: 标签页ID
        """
        if tab_id in self.tabs:
            tab_info = self.tabs[tab_id]
            try:
                self.notebook.forget(tab_info['widget'])
            except tk.TclError:
                pass
            del self.tabs[tab_id]
            self.tab_order.remove(tab_id)
    
    def select_tab(self, tab_id):
        """选择标签页
        
        Args:
            tab_id: 标签页ID
        """
        if tab_id in self.tabs:
            try:
                index = self.tab_order.index(tab_id)
                self.notebook.select(index)
            except (ValueError, tk.TclError):
                pass
    
    def get_selected_tab(self):
        """获取当前选中的标签页
        
        Returns:
            当前选中的标签页ID
        """
        try:
            index = self.notebook.index(self.notebook.select())
            if 0 <= index < len(self.tab_order):
                return self.tab_order[index]
        except tk.TclError:
            pass
        return None
    
    def update_tab_title(self, tab_id, title):
        """更新标签页标题
        
        Args:
            tab_id: 标签页ID
            title: 新标题
        """
        if tab_id in self.tabs:
            self.tabs[tab_id]['title'] = title
            # 重新添加标签页以更新标题
            tab_info = self.tabs[tab_id]
            try:
                self.notebook.forget(tab_info['widget'])
                self.notebook.add(tab_info['widget'], text=title)
            except tk.TclError:
                pass


class AlignmentUtils:
    """对齐工具类"""
    
    @staticmethod
    def center_widget(widget, parent=None):
        """居中控件
        
        Args:
            widget: 要居中的控件
            parent: 父容器
        """
        widget.update_idletasks()
        
        width = widget.winfo_width()
        height = widget.winfo_height()
        
        if parent is None:
            parent = widget.master
        
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        x = (parent_width - width) // 2
        y = (parent_height - height) // 2
        
        widget.geometry(f"+{x}+{y}")
    
    @staticmethod
    def align_widgets_horizontally(widgets, spacing=10, align='center'):
        """水平对齐控件
        
        Args:
            widgets: 控件列表
            spacing: 间距
            align: 对齐方式 ('left', 'center', 'right')
        """
        if not widgets:
            return
        
        # 获取控件位置信息
        positions = []
        for widget in widgets:
            widget.update_idletasks()
            positions.append({
                'widget': widget,
                'x': widget.winfo_x(),
                'y': widget.winfo_y(),
                'width': widget.winfo_width(),
                'height': widget.winfo_height()
            })
        
        # 计算对齐位置
        if align == 'center':
            center_y = sum(pos['y'] + pos['height'] // 2 for pos in positions) // len(positions)
            for pos in positions:
                target_y = center_y - pos['height'] // 2
                pos['widget'].place(x=pos['x'], y=target_y)
        
        elif align == 'left':
            min_x = min(pos['x'] for pos in positions)
            for pos in positions:
                pos['widget'].place(x=min_x, y=pos['y'])
        
        elif align == 'right':
            max_x = max(pos['x'] + pos['width'] for pos in positions)
            for pos in positions:
                target_x = max_x - pos['width']
                pos['widget'].place(x=target_x, y=pos['y'])
    
    @staticmethod
    def align_widgets_vertically(widgets, spacing=10, align='center'):
        """垂直对齐控件
        
        Args:
            widgets: 控件列表
            spacing: 间距
            align: 对齐方式 ('top', 'center', 'bottom')
        """
        if not widgets:
            return
        
        # 获取控件位置信息
        positions = []
        for widget in widgets:
            widget.update_idletasks()
            positions.append({
                'widget': widget,
                'x': widget.winfo_x(),
                'y': widget.winfo_y(),
                'width': widget.winfo_width(),
                'height': widget.winfo_height()
            })
        
        # 计算对齐位置
        if align == 'center':
            center_x = sum(pos['x'] + pos['width'] // 2 for pos in positions) // len(positions)
            for pos in positions:
                target_x = center_x - pos['width'] // 2
                pos['widget'].place(x=target_x, y=pos['y'])
        
        elif align == 'top':
            min_y = min(pos['y'] for pos in positions)
            for pos in positions:
                pos['widget'].place(x=pos['x'], y=min_y)
        
        elif align == 'bottom':
            max_y = max(pos['y'] + pos['height'] for pos in positions)
            for pos in positions:
                target_y = max_y - pos['height']
                pos['widget'].place(x=pos['x'], y=target_y)
    
    @staticmethod
    def distribute_widgets_evenly(widgets, direction='horizontal', spacing=10):
        """均匀分布控件
        
        Args:
            widgets: 控件列表
            direction: 分布方向 ('horizontal', 'vertical')
            spacing: 间距
        """
        if not widgets:
            return
        
        if direction == 'horizontal':
            # 计算总宽度
            total_width = sum(widget.winfo_width() for widget in widgets)
            total_spacing = spacing * (len(widgets) - 1)
            available_width = widgets[0].master.winfo_width() - total_spacing
            
            if available_width > total_width:
                # 均匀分布
                x = 0
                for widget in widgets:
                    widget_width = widget.winfo_width()
                    widget.place(x=x, y=widget.winfo_y())
                    x += widget_width + spacing
        else:
            # 垂直分布
            total_height = sum(widget.winfo_height() for widget in widgets)
            total_spacing = spacing * (len(widgets) - 1)
            available_height = widgets[0].master.winfo_height() - total_spacing
            
            if available_height > total_height:
                # 均匀分布
                y = 0
                for widget in widgets:
                    widget_height = widget.winfo_height()
                    widget.place(x=widget.winfo_x(), y=y)
                    y += widget_height + spacing


def create_grid_container(parent, rows, columns, **kwargs):
    """创建网格容器
    
    Args:
        parent: 父容器
        rows: 行数
        columns: 列数
        **kwargs: 其他配置参数
        
    Returns:
        网格容器控件
    """
    container = ttk.Frame(parent)
    
    # 配置行列权重
    for i in range(rows):
        container.grid_rowconfigure(i, weight=kwargs.get('row_weight', 1))
    for j in range(columns):
        container.grid_columnconfigure(j, weight=kwargs.get('col_weight', 1))
    
    return container


def create_flex_container(parent, direction='row', gap=5):
    """创建弹性容器
    
    Args:
        parent: 父容器
        direction: 方向 ('row', 'column')
        gap: 间距
        
    Returns:
        弹性容器控件
    """
    container = ttk.Frame(parent)
    return FlexLayout(container, direction, gap)


def create_responsive_container(parent):
    """创建响应式容器
    
    Args:
        parent: 父容器
        
    Returns:
        响应式容器控件
    """
    container = ttk.Frame(parent)
    return ResponsiveLayout(container)