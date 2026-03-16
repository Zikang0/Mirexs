"""
Web组件模块 - Mirexs Web界面

提供可复用的Web组件，包括：
1. 组件注册和管理
2. 生命周期管理
3. 属性管理
4. 事件系统
5. 插槽支持
"""

import logging
import uuid
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class ComponentLifecycle(Enum):
    """组件生命周期枚举"""
    CREATED = "created"
    MOUNTED = "mounted"
    UPDATED = "updated"
    DESTROYED = "destroyed"

@dataclass
class Component:
    """Web组件定义"""
    id: str
    name: str
    tag_name: str
    template: str
    style: str = ""
    
    # 属性
    props: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    
    # 事件
    events: Dict[str, List[Callable]] = field(default_factory=dict)
    
    # 生命周期
    created_at: float = field(default_factory=lambda: __import__('time').time())
    mounted_at: Optional[float] = None
    
    # 子组件
    children: List['Component'] = field(default_factory=list)
    
    # 父组件
    parent_id: Optional[str] = None

@dataclass
class ComponentRegistry:
    """组件注册表"""
    components: Dict[str, Component] = field(default_factory=dict)
    by_tag: Dict[str, str] = field(default_factory=dict)  # tag_name -> component_id

class WebComponents:
    """
    Web组件管理器
    
    负责Web组件的注册、创建和管理，包括：
    - 组件定义注册
    - 组件实例创建
    - 生命周期管理
    - 事件处理
    - 属性传递
    """
    
    def __init__(self):
        """初始化Web组件管理器"""
        self.registry = ComponentRegistry()
        
        # 默认组件
        self._register_default_components()
        
        logger.info("WebComponents initialized")
    
    def _register_default_components(self):
        """注册默认组件"""
        # MirexsChat 组件
        self.register_component(
            name="MirexsChat",
            tag_name="mirexs-chat",
            template="""
            <div class="mirexs-chat">
                <div class="messages" ref="messagesContainer">
                    <div v-for="message in messages" 
                         :key="message.id"
                         :class="['message', message.type]">
                        <div class="avatar" v-if="message.type === 'assistant'">
                            <img src="/assets/cat-avatar.png" alt="Mirexs">
                        </div>
                        <div class="content">{{ message.content }}</div>
                    </div>
                </div>
                <div class="input-area">
                    <input type="text" 
                           v-model="inputText" 
                           @keyup.enter="sendMessage"
                           placeholder="输入消息...">
                    <button @click="sendMessage">发送</button>
                </div>
            </div>
            """,
            style="""
            .mirexs-chat {
                display: flex;
                flex-direction: column;
                height: 100%;
                background: var(--background-color);
            }
            .messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
            }
            .message {
                display: flex;
                margin-bottom: 16px;
                animation: fadeIn 0.3s;
            }
            .message.user {
                justify-content: flex-end;
            }
            .message.assistant {
                justify-content: flex-start;
            }
            .avatar {
                width: 40px;
                height: 40px;
                border-radius: 20px;
                margin-right: 12px;
                overflow: hidden;
            }
            .avatar img {
                width: 100%;
                height: 100%;
                object-fit: cover;
            }
            .content {
                max-width: 70%;
                padding: 12px 16px;
                border-radius: 18px;
                background: var(--surface-color);
                color: var(--text-primary);
            }
            .message.user .content {
                background: var(--primary-color);
                color: white;
            }
            .input-area {
                display: flex;
                padding: 16px;
                border-top: 1px solid var(--border-color);
                background: var(--surface-color);
            }
            .input-area input {
                flex: 1;
                height: 40px;
                padding: 0 12px;
                border: 1px solid var(--border-color);
                border-radius: 20px;
                margin-right: 12px;
                font-size: 14px;
            }
            .input-area button {
                height: 40px;
                padding: 0 20px;
                background: var(--primary-color);
                color: white;
                border: none;
                border-radius: 20px;
                cursor: pointer;
                font-size: 14px;
                transition: opacity 0.2s;
            }
            .input-area button:hover {
                opacity: 0.8;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            """
        )
        
        # MirexsAvatar 组件
        self.register_component(
            name="MirexsAvatar",
            tag_name="mirexs-avatar",
            template="""
            <div class="mirexs-avatar" :class="{ 'animated': animated }">
                <canvas ref="canvas" 
                        :width="size" 
                        :height="size"
                        @click="handleClick"></canvas>
                <div class="emotion-badge" v-if="showEmotion">{{ emotion }}</div>
            </div>
            """,
            style="""
            .mirexs-avatar {
                position: relative;
                display: inline-block;
            }
            .mirexs-avatar canvas {
                display: block;
                border-radius: 50%;
                transition: transform 0.3s;
            }
            .mirexs-avatar.animated canvas {
                animation: pulse 2s infinite;
            }
            .emotion-badge {
                position: absolute;
                bottom: 0;
                right: 0;
                width: 24px;
                height: 24px;
                background: var(--surface-color);
                border: 2px solid var(--background-color);
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
            }
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            """
        )
        
        # MirexsTask 组件
        self.register_component(
            name="MirexsTask",
            tag_name="mirexs-task",
            template="""
            <div class="mirexs-task" :class="{ completed }">
                <div class="task-checkbox" @click="toggleComplete">
                    <span v-if="completed">✓</span>
                </div>
                <div class="task-content">
                    <div class="task-title">{{ title }}</div>
                    <div class="task-description" v-if="description">{{ description }}</div>
                    <div class="task-meta">
                        <span class="task-priority" :class="priority">{{ priority }}</span>
                        <span class="task-deadline" v-if="deadline">{{ formatDate(deadline) }}</span>
                    </div>
                </div>
                <button class="task-more" @click="showMenu">⋮</button>
            </div>
            """,
            style="""
            .mirexs-task {
                display: flex;
                align-items: flex-start;
                padding: 16px;
                background: var(--surface-color);
                border-radius: 8px;
                margin-bottom: 8px;
                transition: all 0.3s;
                border: 1px solid var(--border-color);
            }
            .mirexs-task:hover {
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .mirexs-task.completed {
                opacity: 0.6;
            }
            .mirexs-task.completed .task-title {
                text-decoration: line-through;
            }
            .task-checkbox {
                width: 24px;
                height: 24px;
                border: 2px solid var(--border-color);
                border-radius: 4px;
                margin-right: 16px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                color: var(--primary-color);
                font-weight: bold;
            }
            .task-content {
                flex: 1;
            }
            .task-title {
                font-size: 16px;
                font-weight: 500;
                margin-bottom: 4px;
                color: var(--text-primary);
            }
            .task-description {
                font-size: 14px;
                color: var(--text-secondary);
                margin-bottom: 8px;
            }
            .task-meta {
                display: flex;
                gap: 12px;
                font-size: 12px;
            }
            .task-priority {
                padding: 2px 8px;
                border-radius: 4px;
            }
            .task-priority.high {
                background: #ffebee;
                color: #c62828;
            }
            .task-priority.medium {
                background: #fff3e0;
                color: #ef6c00;
            }
            .task-priority.low {
                background: #e8f5e9;
                color: #2e7d32;
            }
            .task-deadline {
                color: var(--text-secondary);
            }
            .task-more {
                background: none;
                border: none;
                font-size: 20px;
                color: var(--text-secondary);
                cursor: pointer;
                padding: 0 8px;
            }
            .task-more:hover {
                color: var(--text-primary);
            }
            """
        )
    
    def register_component(self, name: str, tag_name: str, 
                          template: str, style: str = "") -> str:
        """
        注册组件
        
        Args:
            name: 组件名称
            tag_name: HTML标签名
            template: 组件模板
            style: 组件样式
        
        Returns:
            组件ID
        """
        component_id = str(uuid.uuid4())
        
        component = Component(
            id=component_id,
            name=name,
            tag_name=tag_name,
            template=template,
            style=style
        )
        
        self.registry.components[component_id] = component
        self.registry.by_tag[tag_name] = component_id
        
        logger.info(f"Component registered: {name} ({tag_name})")
        return component_id
    
    def create_component(self, tag_name: str, props: Optional[Dict[str, Any]] = None,
                        parent_id: Optional[str] = None) -> Optional[Component]:
        """
        创建组件实例
        
        Args:
            tag_name: 组件标签名
            props: 组件属性
            parent_id: 父组件ID
        
        Returns:
            组件实例
        """
        if tag_name not in self.registry.by_tag:
            logger.warning(f"Component not found: {tag_name}")
            return None
        
        component_id = self.registry.by_tag[tag_name]
        template = self.registry.components[component_id]
        
        # 创建实例
        instance = Component(
            id=str(uuid.uuid4()),
            name=template.name,
            tag_name=tag_name,
            template=template.template,
            style=template.style,
            props=props or {},
            parent_id=parent_id
        )
        
        # 触发created事件
        self._trigger_lifecycle(instance, ComponentLifecycle.CREATED)
        
        logger.debug(f"Component instance created: {instance.id} ({tag_name})")
        return instance
    
    def mount_component(self, component_id: str, container_id: str):
        """
        挂载组件
        
        Args:
            component_id: 组件ID
            container_id: 容器元素ID
        """
        # 实际实现中会渲染到DOM
        if component_id not in self.registry.components:
            logger.warning(f"Component not found: {component_id}")
            return
        
        component = self.registry.components[component_id]
        component.mounted_at = __import__('time').time()
        
        self._trigger_lifecycle(component, ComponentLifecycle.MOUNTED)
        logger.debug(f"Component mounted: {component_id} to {container_id}")
    
    def update_component(self, component_id: str, props: Dict[str, Any]):
        """
        更新组件属性
        
        Args:
            component_id: 组件ID
            props: 新属性
        """
        if component_id not in self.registry.components:
            logger.warning(f"Component not found: {component_id}")
            return
        
        component = self.registry.components[component_id]
        component.props.update(props)
        
        self._trigger_lifecycle(component, ComponentLifecycle.UPDATED)
        logger.debug(f"Component updated: {component_id}")
    
    def destroy_component(self, component_id: str):
        """
        销毁组件
        
        Args:
            component_id: 组件ID
        """
        if component_id not in self.registry.components:
            return
        
        component = self.registry.components[component_id]
        
        self._trigger_lifecycle(component, ComponentLifecycle.DESTROYED)
        
        # 从注册表中移除
        del self.registry.components[component_id]
        
        logger.debug(f"Component destroyed: {component_id}")
    
    def _trigger_lifecycle(self, component: Component, lifecycle: ComponentLifecycle):
        """触发生命周期事件"""
        # 这里可以调用组件定义的生命周期方法
        pass
    
    def on(self, component_id: str, event_name: str, handler: Callable):
        """
        监听组件事件
        
        Args:
            component_id: 组件ID
            event_name: 事件名称
            handler: 处理函数
        """
        if component_id not in self.registry.components:
            logger.warning(f"Component not found: {component_id}")
            return
        
        component = self.registry.components[component_id]
        
        if event_name not in component.events:
            component.events[event_name] = []
        
        component.events[event_name].append(handler)
        logger.debug(f"Event handler registered: {component_id}.{event_name}")
    
    def emit(self, component_id: str, event_name: str, data: Any = None):
        """
        触发组件事件
        
        Args:
            component_id: 组件ID
            event_name: 事件名称
            data: 事件数据
        """
        if component_id not in self.registry.components:
            return
        
        component = self.registry.components[component_id]
        
        if event_name in component.events:
            for handler in component.events[event_name]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
    
    def get_component(self, component_id: str) -> Optional[Component]:
        """
        获取组件
        
        Args:
            component_id: 组件ID
        
        Returns:
            组件对象
        """
        return self.registry.components.get(component_id)
    
    def find_components_by_tag(self, tag_name: str) -> List[Component]:
        """
        根据标签名查找组件
        
        Args:
            tag_name: 标签名
        
        Returns:
            组件列表
        """
        if tag_name not in self.registry.by_tag:
            return []
        
        template_id = self.registry.by_tag[tag_name]
        return [
            c for c in self.registry.components.values()
            if c.id == template_id or c.tag_name == tag_name
        ]
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取组件管理器状态
        
        Returns:
            状态字典
        """
        return {
            "total_components": len(self.registry.components),
            "registered_tags": len(self.registry.by_tag),
            "components": [
                {
                    "id": c.id,
                    "name": c.name,
                    "tag": c.tag_name,
                    "has_children": len(c.children) > 0,
                    "parent": c.parent_id,
                    "created_at": c.created_at,
                    "mounted_at": c.mounted_at
                }
                for c in self.registry.components.values()
            ]
        }

# 单例模式实现
_web_components_instance: Optional[WebComponents] = None

def get_web_components() -> WebComponents:
    """
    获取Web组件管理器单例
    
    Returns:
        Web组件管理器实例
    """
    global _web_components_instance
    if _web_components_instance is None:
        _web_components_instance = WebComponents()
    return _web_components_instance

