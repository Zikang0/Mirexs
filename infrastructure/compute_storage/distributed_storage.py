"""
分布式存储：管理分布式文件存储
负责模型文件、用户数据等的分布式存储管理
"""

import os
import shutil
import asyncio
from typing import Dict, List, Optional, BinaryIO, Any
from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path

@dataclass
class StorageNode:
    """存储节点"""
    node_id: str
    address: str
    capacity: int  # 容量(字节)
    used: int      # 已使用(字节)
    is_online: bool = True

@dataclass
class FileMetadata:
    """文件元数据"""
    file_id: str
    filename: str
    size: int
    checksum: str
    storage_nodes: List[str]  # 存储节点列表
    created_time: float
    modified_time: float

class DistributedStorage:
    """分布式存储系统"""
    
    def __init__(self, base_path: str = "data/distributed_storage"):
        self.base_path = base_path
        self.storage_nodes: Dict[str, StorageNode] = {}
        self.file_registry: Dict[str, FileMetadata] = {}
        self.replication_factor = 3  # 复制因子
        self.initialized = False
        
    async def initialize(self):
        """初始化分布式存储"""
        if self.initialized:
            return
            
        logging.info("初始化分布式存储系统...")
        
        # 创建基础目录
        os.makedirs(self.base_path, exist_ok=True)
        
        # 添加本地节点
        await self._add_local_node()
        
        # 加载现有文件索引
        await self._load_file_index()
        
        self.initialized = True
        logging.info("分布式存储系统初始化完成")
    
    async def _add_local_node(self):
        """添加本地存储节点"""
        local_node = StorageNode(
            node_id="local",
            address="localhost",
            capacity=100 * 1024 * 1024 * 1024,  # 100GB
            used=0
        )
        self.storage_nodes["local"] = local_node
        
        # 创建本地节点目录
        local_path = f"{self.base_path}/local"
        os.makedirs(local_path, exist_ok=True)
    
    async def _load_file_index(self):
        """加载文件索引"""
        index_file = f"{self.base_path}/file_index.json"
        if os.path.exists(index_file):
            try:
                import json
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for file_id, meta_data in data.get('files', {}).items():
                    self.file_registry[file_id] = FileMetadata(
                        file_id=file_id,
                        filename=meta_data['filename'],
                        size=meta_data['size'],
                        checksum=meta_data['checksum'],
                        storage_nodes=meta_data['storage_nodes'],
                        created_time=meta_data['created_time'],
                        modified_time=meta_data['modified_time']
                    )
                
                logging.info(f"加载了 {len(self.file_registry)} 个文件索引")
                
            except Exception as e:
                logging.error(f"加载文件索引失败: {e}")
    
    async def store_file(self, file_path: str, filename: str = None) -> str:
        """存储文件"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 计算文件校验和
        checksum = await self._calculate_checksum(file_path)
        file_size = os.path.getsize(file_path)
        
        # 生成文件ID
        file_id = hashlib.md5(f"{filename}_{checksum}".encode()).hexdigest()
        
        # 检查文件是否已存在
        if file_id in self.file_registry:
            logging.info(f"文件已存在: {filename} ({file_id})")
            return file_id
        
        # 选择存储节点
        storage_nodes = await self._select_storage_nodes(file_size)
        
        # 复制文件到存储节点
        for node_id in storage_nodes:
            await self._copy_file_to_node(node_id, file_path, file_id)
        
        # 创建文件元数据
        metadata = FileMetadata(
            file_id=file_id,
            filename=filename or os.path.basename(file_path),
            size=file_size,
            checksum=checksum,
            storage_nodes=storage_nodes,
            created_time=asyncio.get_event_loop().time(),
            modified_time=asyncio.get_event_loop().time()
        )
        
        self.file_registry[file_id] = metadata
        
        # 更新节点使用量
        for node_id in storage_nodes:
            self.storage_nodes[node_id].used += file_size
        
        logging.info(f"文件存储成功: {filename} -> {file_id}")
        return file_id
    
    async def retrieve_file(self, file_id: str, target_path: str) -> bool:
        """检索文件"""
        if file_id not in self.file_registry:
            logging.error(f"文件未找到: {file_id}")
            return False
        
        metadata = self.file_registry[file_id]
        
        # 尝试从存储节点获取文件
        for node_id in metadata.storage_nodes:
            if await self._copy_file_from_node(node_id, file_id, target_path):
                logging.info(f"文件检索成功: {file_id} -> {target_path}")
                return True
        
        logging.error(f"无法从任何节点检索文件: {file_id}")
        return False
    
    async def delete_file(self, file_id: str) -> bool:
        """删除文件"""
        if file_id not in self.file_registry:
            return False
        
        metadata = self.file_registry[file_id]
        
        # 从所有存储节点删除文件
        for node_id in metadata.storage_nodes:
            await self._delete_file_from_node(node_id, file_id)
            
            # 更新节点使用量
            self.storage_nodes[node_id].used -= metadata.size
        
        # 从注册表中删除
        del self.file_registry[file_id]
        
        logging.info(f"文件删除成功: {file_id}")
        return True
    
    async def _select_storage_nodes(self, file_size: int) -> List[str]:
        """选择存储节点"""
        # 简单的选择策略：选择使用率最低的节点
        available_nodes = [
            node for node in self.storage_nodes.values() 
            if node.is_online and (node.capacity - node.used) >= file_size
        ]
        
        if not available_nodes:
            raise RuntimeError("没有可用的存储节点")
        
        # 按使用率排序
        available_nodes.sort(key=lambda x: x.used / x.capacity)
        
        # 选择前N个节点，N为复制因子
        selected_nodes = [node.node_id for node in available_nodes[:self.replication_factor]]
        
        return selected_nodes
    
    async def _copy_file_to_node(self, node_id: str, source_path: str, file_id: str):
        """复制文件到节点"""
        node_path = f"{self.base_path}/{node_id}"
        os.makedirs(node_path, exist_ok=True)
        
        target_path = f"{node_path}/{file_id}"
        shutil.copy2(source_path, target_path)
        
        logging.debug(f"文件复制到节点 {node_id}: {file_id}")
    
    async def _copy_file_from_node(self, node_id: str, file_id: str, target_path: str) -> bool:
        """从节点复制文件"""
        source_path = f"{self.base_path}/{node_id}/{file_id}"
        
        if not os.path.exists(source_path):
            return False
        
        shutil.copy2(source_path, target_path)
        return True
    
    async def _delete_file_from_node(self, node_id: str, file_id: str):
        """从节点删除文件"""
        file_path = f"{self.base_path}/{node_id}/{file_id}"
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.debug(f"从节点 {node_id} 删除文件: {file_id}")
    
    async def _calculate_checksum(self, file_path: str) -> str:
        """计算文件校验和"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    async def save_index(self):
        """保存文件索引"""
        try:
            data = {
                'files': {}
            }
            
            for file_id, metadata in self.file_registry.items():
                data['files'][file_id] = {
                    'filename': metadata.filename,
                    'size': metadata.size,
                    'checksum': metadata.checksum,
                    'storage_nodes': metadata.storage_nodes,
                    'created_time': metadata.created_time,
                    'modified_time': metadata.modified_time
                }
            
            index_file = f"{self.base_path}/file_index.json"
            with open(index_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logging.info("分布式存储索引已保存")
            
        except Exception as e:
            logging.error(f"保存存储索引失败: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        total_capacity = sum(node.capacity for node in self.storage_nodes.values())
        total_used = sum(node.used for node in self.storage_nodes.values())
        
        return {
            "total_nodes": len(self.storage_nodes),
            "online_nodes": sum(1 for node in self.storage_nodes.values() if node.is_online),
            "total_capacity": total_capacity,
            "total_used": total_used,
            "usage_percentage": (total_used / total_capacity * 100) if total_capacity > 0 else 0,
            "total_files": len(self.file_registry),
            "replication_factor": self.replication_factor
        }

# 全局分布式存储实例
distributed_storage = DistributedStorage()
