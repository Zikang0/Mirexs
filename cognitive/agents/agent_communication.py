"""
智能体通信：实现智能体间的通信协议和消息传递机制
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json
import time
import uuid
from collections import defaultdict, deque
import hashlib

from ...infrastructure.communication.message_bus import MessageBus
from ...infrastructure.communication.protocol_adapters import ProtocolAdapter
from ...security.access_control.multi_factor_auth import MultiFactorAuthenticator
from ...security.privacy_protection.data_encryption import DataEncryptor

class MessageType(Enum):
    """消息类型枚举"""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    COORDINATION = "coordination"
    BROADCAST = "broadcast"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    KNOWLEDGE_SHARE = "knowledge_share"

class MessagePriority(Enum):
    """消息优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class AgentMessage:
    """智能体消息结构"""
    message_id: str
    sender_id: str
    receiver_id: str
    message_type: MessageType
    priority: MessagePriority
    payload: Dict[str, Any]
    timestamp: float
    ttl: float = 3600  # 消息存活时间（秒）
    signature: Optional[str] = None

@dataclass
class CommunicationChannel:
    """通信通道信息"""
    channel_id: str
    participants: List[str]
    channel_type: str
    encryption_enabled: bool
    created_time: float
    last_activity: float

class AgentCommunication:
    """
    智能体通信 - 管理智能体间的通信协议和消息传递
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # 核心组件
        self.message_bus = MessageBus(config.get("message_bus", {}))
        self.protocol_adapter = ProtocolAdapter(config.get("protocol", {}))
        self.authenticator = MultiFactorAuthenticator(config.get("auth", {}))
        self.encryptor = DataEncryptor(config.get("encryption", {}))
        
        # 通信状态
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.active_channels: Dict[str, CommunicationChannel] = {}
        self.message_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self.message_history: deque = deque(maxlen=10000)
        
        # 通信协议
        self.protocol_handlers: Dict[str, Callable] = {
            "direct": self._handle_direct_message,
            "broadcast": self._handle_broadcast_message,
            "multicast": self._handle_multicast_message,
            "pubsub": self._handle_pubsub_message
        }
        
        # 性能指标
        self.communication_metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "delivery_success_rate": 0.0,
            "average_latency": 0.0,
            "encryption_usage": 0.0
        }
        
        # 消息处理任务
        self.message_processor_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # 模型加载
        self.communication_model = self._load_communication_model()
        
        self.logger.info("AgentCommunication initialized")

    def _load_communication_model(self):
        """加载通信模型"""
        try:
            self.logger.info("Loading communication model...")
            
            # 模拟通信模型参数
            communication_config = {
                "max_message_size": self.config.get("max_message_size", 1024 * 1024),  # 1MB
                "default_timeout": self.config.get("default_timeout", 30),
                "retry_attempts": self.config.get("retry_attempts", 3),
                "compression_enabled": self.config.get("compression_enabled", True),
                "encryption_required": self.config.get("encryption_required", True)
            }
            
            self.logger.info("Communication model loaded successfully")
            return communication_config
            
        except Exception as e:
            self.logger.error(f"Failed to load communication model: {e}")
            raise

    async def start(self):
        """启动通信系统"""
        self.logger.info("Starting AgentCommunication system...")
        
        # 启动消息处理任务
        self.message_processor_task = asyncio.create_task(self._message_processor())
        
        # 启动心跳任务
        self.heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
        
        # 启动协议适配器
        await self.protocol_adapter.start()
        
        self.logger.info("AgentCommunication system started successfully")

    async def stop(self):
        """停止通信系统"""
        self.logger.info("Stopping AgentCommunication system...")
        
        # 停止任务
        if self.message_processor_task:
            self.message_processor_task.cancel()
            try:
                await self.message_processor_task
            except asyncio.CancelledError:
                pass
        
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # 停止协议适配器
        await self.protocol_adapter.stop()
        
        self.logger.info("AgentCommunication system stopped")

    async def register_agent(self, agent_id: str, agent_info: Dict[str, Any]) -> bool:
        """
        注册智能体
        
        Args:
            agent_id: 智能体ID
            agent_info: 智能体信息
            
        Returns:
            注册是否成功
        """
        try:
            # 验证智能体身份
            if not await self.authenticator.verify_agent_identity(agent_id, agent_info):
                self.logger.warning(f"Agent identity verification failed for {agent_id}")
                return False
            
            # 注册智能体
            self.registered_agents[agent_id] = {
                **agent_info,
                "registration_time": time.time(),
                "last_heartbeat": time.time(),
                "status": "active"
            }
            
            # 创建消息队列
            if agent_id not in self.message_queues:
                self.message_queues[agent_id] = asyncio.Queue()
            
            self.logger.info(f"Agent {agent_id} registered successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    async def unregister_agent(self, agent_id: str):
        """注销智能体"""
        if agent_id in self.registered_agents:
            del self.registered_agents[agent_id]
            
            # 清理消息队列
            if agent_id in self.message_queues:
                del self.message_queues[agent_id]
            
            # 清理相关通道
            channels_to_remove = []
            for channel_id, channel in self.active_channels.items():
                if agent_id in channel.participants:
                    channel.participants.remove(agent_id)
                    if not channel.participants:
                        channels_to_remove.append(channel_id)
            
            for channel_id in channels_to_remove:
                del self.active_channels[channel_id]
            
            self.logger.info(f"Agent {agent_id} unregistered")

    async def send_message(self, 
                         sender_id: str,
                         receiver_id: str,
                         message_type: MessageType,
                         payload: Dict[str, Any],
                         priority: MessagePriority = MessagePriority.NORMAL,
                         timeout: Optional[float] = None) -> str:
        """
        发送消息
        
        Args:
            sender_id: 发送者ID
            receiver_id: 接收者ID
            message_type: 消息类型
            payload: 消息负载
            priority: 消息优先级
            timeout: 超时时间
            
        Returns:
            消息ID
        """
        # 验证发送者
        if sender_id not in self.registered_agents:
            self.logger.error(f"Sender {sender_id} not registered")
            return ""
        
        # 验证接收者
        if receiver_id != "broadcast" and receiver_id not in self.registered_agents:
            self.logger.error(f"Receiver {receiver_id} not registered")
            return ""
        
        try:
            # 创建消息
            message_id = self._generate_message_id()
            message = AgentMessage(
                message_id=message_id,
                sender_id=sender_id,
                receiver_id=receiver_id,
                message_type=message_type,
                priority=priority,
                payload=payload,
                timestamp=time.time(),
                ttl=timeout or self.communication_model["default_timeout"]
            )
            
            # 签名消息
            message.signature = await self._sign_message(message)
            
            # 加密消息（如果需要）
            if self.communication_model["encryption_required"]:
                encrypted_message = await self._encrypt_message(message)
            else:
                encrypted_message = message
            
            # 发送消息
            if receiver_id == "broadcast":
                await self._send_broadcast_message(sender_id, encrypted_message)
            else:
                await self._send_direct_message(encrypted_message)
            
            # 更新指标
            self.communication_metrics["messages_sent"] += 1
            self.communication_metrics["encryption_usage"] = (
                self.communication_metrics["messages_sent"] / 
                (self.communication_metrics["messages_sent"] + self.communication_metrics["messages_received"])
            )
            
            # 记录消息历史
            self.message_history.append({
                "message_id": message_id,
                "sender": sender_id,
                "receiver": receiver_id,
                "type": message_type.value,
                "timestamp": time.time(),
                "size": len(str(payload))
            })
            
            self.logger.debug(f"Message {message_id} sent from {sender_id} to {receiver_id}")
            
            return message_id
            
        except Exception as e:
            self.logger.error(f"Failed to send message from {sender_id} to {receiver_id}: {e}")
            return ""

    async def send_and_wait_response(self,
                                   sender_id: str,
                                   receiver_id: str,
                                   message_type: MessageType,
                                   payload: Dict[str, Any],
                                   timeout: Optional[float] = None,
                                   response_type: Optional[MessageType] = None) -> Optional[AgentMessage]:
        """
        发送消息并等待响应
        
        Args:
            sender_id: 发送者ID
            receiver_id: 接收者ID
            message_type: 消息类型
            payload: 消息负载
            timeout: 超时时间
            response_type: 期望的响应类型
            
        Returns:
            响应消息或None
        """
        message_id = await self.send_message(sender_id, receiver_id, message_type, payload)
        if not message_id:
            return None
        
        response_type = response_type or MessageType.TASK_RESPONSE
        
        try:
            # 等待响应
            start_time = time.time()
            timeout = timeout or self.communication_model["default_timeout"]
            
            while time.time() - start_time < timeout:
                # 检查消息队列中的响应
                if not self.message_queues[sender_id].empty():
                    message = await asyncio.wait_for(
                        self.message_queues[sender_id].get(),
                        timeout=0.1
                    )
                    
                    # 检查是否是期望的响应
                    if (isinstance(message, AgentMessage) and 
                        message.message_type == response_type and
                        message.payload.get("in_response_to") == message_id):
                        
                        # 计算延迟
                        latency = time.time() - start_time
                        self.communication_metrics["average_latency"] = (
                            self.communication_metrics["average_latency"] * 0.9 + latency * 0.1
                        )
                        
                        return message
                
                await asyncio.sleep(0.01)
            
            self.logger.warning(f"Response timeout for message {message_id}")
            return None
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Response timeout for message {message_id}")
            return None
        except Exception as e:
            self.logger.error(f"Error waiting for response to message {message_id}: {e}")
            return None

    async def create_communication_channel(self,
                                         channel_id: str,
                                         participants: List[str],
                                         channel_type: str = "direct",
                                         encryption: bool = True) -> bool:
        """
        创建通信通道
        
        Args:
            channel_id: 通道ID
            participants: 参与者列表
            channel_type: 通道类型
            encryption: 是否加密
            
        Returns:
            创建是否成功
        """
        try:
            # 验证参与者
            for participant in participants:
                if participant not in self.registered_agents:
                    self.logger.error(f"Participant {participant} not registered")
                    return False
            
            # 创建通道
            channel = CommunicationChannel(
                channel_id=channel_id,
                participants=participants,
                channel_type=channel_type,
                encryption_enabled=encryption,
                created_time=time.time(),
                last_activity=time.time()
            )
            
            self.active_channels[channel_id] = channel
            
            # 通知参与者
            for participant in participants:
                notification = {
                    "channel_id": channel_id,
                    "participants": participants,
                    "channel_type": channel_type,
                    "action": "channel_created"
                }
                
                await self.message_queues[participant].put(
                    AgentMessage(
                        message_id=self._generate_message_id(),
                        sender_id="system",
                        receiver_id=participant,
                        message_type=MessageType.COORDINATION,
                        priority=MessagePriority.NORMAL,
                        payload=notification,
                        timestamp=time.time()
                    )
                )
            
            self.logger.info(f"Communication channel {channel_id} created with {len(participants)} participants")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create communication channel {channel_id}: {e}")
            return False

    async def send_channel_message(self,
                                 channel_id: str,
                                 sender_id: str,
                                 message_type: MessageType,
                                 payload: Dict[str, Any]) -> bool:
        """
        发送通道消息
        
        Args:
            channel_id: 通道ID
            sender_id: 发送者ID
            message_type: 消息类型
            payload: 消息负载
            
        Returns:
            发送是否成功
        """
        if channel_id not in self.active_channels:
            self.logger.error(f"Channel {channel_id} not found")
            return False
        
        channel = self.active_channels[channel_id]
        
        if sender_id not in channel.participants:
            self.logger.error(f"Sender {sender_id} not in channel {channel_id}")
            return False
        
        try:
            # 创建消息
            message_id = self._generate_message_id()
            message = AgentMessage(
                message_id=message_id,
                sender_id=sender_id,
                receiver_id=channel_id,  # 使用通道ID作为接收者
                message_type=message_type,
                priority=MessagePriority.NORMAL,
                payload=payload,
                timestamp=time.time()
            )
            
            # 签名和加密
            message.signature = await self._sign_message(message)
            if channel.encryption_enabled:
                encrypted_message = await self._encrypt_message(message)
            else:
                encrypted_message = message
            
            # 发送给所有参与者（除了发送者）
            for participant in channel.participants:
                if participant != sender_id:
                    await self.message_queues[participant].put(encrypted_message)
            
            # 更新通道活动时间
            channel.last_activity = time.time()
            
            self.logger.debug(f"Channel message {message_id} sent in channel {channel_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send channel message in {channel_id}: {e}")
            return False

    async def _message_processor(self):
        """消息处理主循环"""
        self.logger.info("Message processor started")
        
        try:
            while True:
                # 处理所有消息队列
                for agent_id, queue in self.message_queues.items():
                    if not queue.empty():
                        try:
                            message = await asyncio.wait_for(queue.get(), timeout=0.1)
                            await self._process_incoming_message(message)
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            self.logger.error(f"Error processing message for {agent_id}: {e}")
                
                await asyncio.sleep(0.01)  # 防止CPU过度使用
                
        except asyncio.CancelledError:
            self.logger.info("Message processor stopped")
        except Exception as e:
            self.logger.error(f"Message processor error: {e}")

    async def _process_incoming_message(self, message: AgentMessage):
        """处理传入消息"""
        try:
            # 验证消息
            if not await self._validate_message(message):
                self.logger.warning(f"Message validation failed: {message.message_id}")
                return
            
            # 解密消息（如果需要）
            if self.communication_model["encryption_required"]:
                decrypted_message = await self._decrypt_message(message)
            else:
                decrypted_message = message
            
            # 更新指标
            self.communication_metrics["messages_received"] += 1
            
            # 根据消息类型处理
            handler = self.protocol_handlers.get(decrypted_message.receiver_id)
            if handler:
                await handler(decrypted_message)
            else:
                # 默认直接消息处理
                await self._handle_direct_message(decrypted_message)
            
            self.logger.debug(f"Message {message.message_id} processed successfully")
            
        except Exception as e:
            self.logger.error(f"Error processing incoming message {message.message_id}: {e}")
            
            # 发送错误响应
            error_response = AgentMessage(
                message_id=self._generate_message_id(),
                sender_id="system",
                receiver_id=message.sender_id,
                message_type=MessageType.ERROR,
                priority=MessagePriority.HIGH,
                payload={
                    "error": str(e),
                    "original_message_id": message.message_id
                },
                timestamp=time.time()
            )
            
            await self._send_direct_message(error_response)

    async def _handle_direct_message(self, message: AgentMessage):
        """处理直接消息"""
        # 直接传递给目标智能体的消息队列
        if message.receiver_id in self.message_queues:
            await self.message_queues[message.receiver_id].put(message)
        else:
            self.logger.warning(f"Receiver {message.receiver_id} not found for direct message")

    async def _handle_broadcast_message(self, sender_id: str, message: AgentMessage):
        """处理广播消息"""
        # 发送给所有注册的智能体（除了发送者）
        for agent_id in self.registered_agents:
            if agent_id != sender_id:
                broadcast_message = AgentMessage(
                    message_id=message.message_id + f"_to_{agent_id}",
                    sender_id=sender_id,
                    receiver_id=agent_id,
                    message_type=message.message_type,
                    priority=message.priority,
                    payload=message.payload,
                    timestamp=time.time()
                )
                
                await self.message_queues[agent_id].put(broadcast_message)

    async def _handle_multicast_message(self, message: AgentMessage):
        """处理多播消息"""
        # 多播给指定的多个接收者
        receivers = message.payload.get("receivers", [])
        for receiver_id in receivers:
            if receiver_id in self.message_queues:
                multicast_message = AgentMessage(
                    message_id=message.message_id + f"_to_{receiver_id}",
                    sender_id=message.sender_id,
                    receiver_id=receiver_id,
                    message_type=message.message_type,
                    priority=message.priority,
                    payload=message.payload.get("content", {}),
                    timestamp=time.time()
                )
                
                await self.message_queues[receiver_id].put(multicast_message)

    async def _handle_pubsub_message(self, message: AgentMessage):
        """处理发布订阅消息"""
        # 发布订阅模式 - 发送给订阅了特定主题的智能体
        topic = message.payload.get("topic")
        if not topic:
            self.logger.warning("PubSub message missing topic")
            return
        
        # 这里需要实现主题订阅管理
        # 简化实现：发送给所有智能体，由智能体自己过滤
        for agent_id in self.registered_agents:
            if agent_id != message.sender_id:
                pubsub_message = AgentMessage(
                    message_id=message.message_id + f"_pubsub_{agent_id}",
                    sender_id=message.sender_id,
                    receiver_id=agent_id,
                    message_type=message.message_type,
                    priority=message.priority,
                    payload={
                        "topic": topic,
                        "content": message.payload.get("content", {})
                    },
                    timestamp=time.time()
                )
                
                await self.message_queues[agent_id].put(pubsub_message)

    async def _send_direct_message(self, message: AgentMessage):
        """发送直接消息"""
        if message.receiver_id in self.message_queues:
            await self.message_queues[message.receiver_id].put(message)
            
            # 更新投递成功率
            successful_deliveries = self.communication_metrics["messages_sent"] - len([
                m for m in self.message_history 
                if m.get("status") == "failed"
            ])
            
            self.communication_metrics["delivery_success_rate"] = (
                successful_deliveries / self.communication_metrics["messages_sent"]
                if self.communication_metrics["messages_sent"] > 0 else 1.0
            )
        else:
            self.logger.warning(f"Receiver {message.receiver_id} not found for direct message")

    async def _send_broadcast_message(self, sender_id: str, message: AgentMessage):
        """发送广播消息"""
        await self._handle_broadcast_message(sender_id, message)

    async def _validate_message(self, message: AgentMessage) -> bool:
        """验证消息"""
        try:
            # 检查消息存活时间
            if time.time() - message.timestamp > message.ttl:
                self.logger.warning(f"Message {message.message_id} expired")
                return False
            
            # 验证发送者
            if message.sender_id not in self.registered_agents:
                self.logger.warning(f"Unknown sender: {message.sender_id}")
                return False
            
            # 验证签名
            if not await self._verify_message_signature(message):
                self.logger.warning(f"Message signature verification failed: {message.message_id}")
                return False
            
            # 验证消息大小
            message_size = len(str(message.payload))
            if message_size > self.communication_model["max_message_size"]:
                self.logger.warning(f"Message too large: {message_size} bytes")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Message validation error: {e}")
            return False

    async def _sign_message(self, message: AgentMessage) -> str:
        """签名消息"""
        try:
            message_data = f"{message.message_id}{message.sender_id}{message.receiver_id}{message.timestamp}"
            signature = hashlib.sha256(message_data.encode()).hexdigest()
            return signature
        except Exception as e:
            self.logger.error(f"Failed to sign message: {e}")
            return ""

    async def _verify_message_signature(self, message: AgentMessage) -> bool:
        """验证消息签名"""
        if not message.signature:
            return False
        
        try:
            expected_signature = await self._sign_message(message)
            return message.signature == expected_signature
        except Exception:
            return False

    async def _encrypt_message(self, message: AgentMessage) -> AgentMessage:
        """加密消息"""
        try:
            encrypted_payload = await self.encryptor.encrypt_data(message.payload)
            encrypted_message = AgentMessage(
                message_id=message.message_id,
                sender_id=message.sender_id,
                receiver_id=message.receiver_id,
                message_type=message.message_type,
                priority=message.priority,
                payload={"encrypted_data": encrypted_payload},
                timestamp=message.timestamp,
                ttl=message.ttl,
                signature=message.signature
            )
            return encrypted_message
        except Exception as e:
            self.logger.error(f"Failed to encrypt message: {e}")
            return message

    async def _decrypt_message(self, message: AgentMessage) -> AgentMessage:
        """解密消息"""
        try:
            if "encrypted_data" in message.payload:
                decrypted_payload = await self.encryptor.decrypt_data(message.payload["encrypted_data"])
                decrypted_message = AgentMessage(
                    message_id=message.message_id,
                    sender_id=message.sender_id,
                    receiver_id=message.receiver_id,
                    message_type=message.message_type,
                    priority=message.priority,
                    payload=decrypted_payload,
                    timestamp=message.timestamp,
                    ttl=message.ttl,
                    signature=message.signature
                )
                return decrypted_message
            else:
                return message
        except Exception as e:
            self.logger.error(f"Failed to decrypt message: {e}")
            return message

    async def _heartbeat_monitor(self):
        """心跳监控"""
        self.logger.info("Heartbeat monitor started")
        
        try:
            while True:
                current_time = time.time()
                inactive_agents = []
                
                # 检查所有注册的智能体
                for agent_id, agent_info in self.registered_agents.items():
                    last_heartbeat = agent_info.get("last_heartbeat", 0)
                    heartbeat_interval = self.config.get("heartbeat_interval", 60)
                    
                    if current_time - last_heartbeat > heartbeat_interval * 2:  # 允许一次错过
                        self.logger.warning(f"Agent {agent_id} heartbeat missed")
                        agent_info["status"] = "inactive"
                        inactive_agents.append(agent_id)
                    
                    # 发送心跳请求
                    heartbeat_message = AgentMessage(
                        message_id=self._generate_message_id(),
                        sender_id="system",
                        receiver_id=agent_id,
                        message_type=MessageType.HEARTBEAT,
                        priority=MessagePriority.LOW,
                        payload={"timestamp": current_time},
                        timestamp=current_time
                    )
                    
                    await self.message_queues[agent_id].put(heartbeat_message)
                
                # 清理不活跃的智能体
                for agent_id in inactive_agents:
                    await self.unregister_agent(agent_id)
                
                await asyncio.sleep(self.config.get("heartbeat_interval", 60))
                
        except asyncio.CancelledError:
            self.logger.info("Heartbeat monitor stopped")
        except Exception as e:
            self.logger.error(f"Heartbeat monitor error: {e}")

    def _generate_message_id(self) -> str:
        """生成消息ID"""
        return f"msg_{uuid.uuid4().hex}"

    def get_communication_statistics(self) -> Dict[str, Any]:
        """获取通信统计信息"""
        return {
            **self.communication_metrics,
            "registered_agents": len(self.registered_agents),
            "active_channels": len(self.active_channels),
            "message_history_size": len(self.message_history),
            "queue_sizes": {agent_id: queue.qsize() for agent_id, queue in self.message_queues.items()}
        }

    async def process_heartbeat_response(self, agent_id: str, response: AgentMessage):
        """处理心跳响应"""
        if agent_id in self.registered_agents:
            self.registered_agents[agent_id]["last_heartbeat"] = time.time()
            self.registered_agents[agent_id]["status"] = "active"
            self.logger.debug(f"Heartbeat response received from {agent_id}")

    async def cleanup(self):
        """清理资源"""
        self.logger.info("Cleaning up AgentCommunication...")
        
        await self.stop()
        
        # 清理消息队列
        self.message_queues.clear()
        
        # 清理注册信息
        self.registered_agents.clear()
        
        # 清理通道
        self.active_channels.clear()
        
        self.logger.info("AgentCommunication cleanup completed")

