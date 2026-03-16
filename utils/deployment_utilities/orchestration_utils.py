"""
容器编排工具模块

提供Kubernetes和容器编排相关的工具函数和类。
"""

from typing import Dict, List, Optional, Any, Union, Tuple
import json
import yaml
import subprocess
import time
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class ResourceType(Enum):
    """资源类型枚举"""
    POD = "pod"
    SERVICE = "service"
    DEPLOYMENT = "deployment"
    STATEFULSET = "statefulset"
    DAEMONSET = "daemonset"
    CONFIGMAP = "configmap"
    SECRET = "secret"
    PERSISTENTVOLUME = "persistentvolume"
    PERSISTENTVOLUMECLAIM = "persistentvolumeclaim"
    INGRESS = "ingress"
    NETWORKPOLICY = "networkpolicy"


class PodPhase(Enum):
    """Pod状态枚举"""
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


class ServiceType(Enum):
    """服务类型枚举"""
    CLUSTER_IP = "ClusterIP"
    NODE_PORT = "NodePort"
    LOAD_BALANCER = "LoadBalancer"
    EXTERNAL_NAME = "ExternalName"


@dataclass
class ResourceSpec:
    """资源规范"""
    name: str
    namespace: str = "default"
    labels: Dict[str, str] = None
    annotations: Dict[str, str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if self.annotations is None:
            self.annotations = {}


@dataclass
class ContainerSpec:
    """容器规范"""
    name: str
    image: str
    ports: List[Dict[str, Any]] = None
    env: List[Dict[str, str]] = None
    volume_mounts: List[Dict[str, str]] = None
    resources: Dict[str, Dict[str, str]] = None
    command: List[str] = None
    args: List[str] = None
    
    def __post_init__(self):
        if self.ports is None:
            self.ports = []
        if self.env is None:
            self.env = []
        if self.volume_mounts is None:
            self.volume_mounts = []
        if self.resources is None:
            self.resources = {}


@dataclass
class VolumeSpec:
    """卷规范"""
    name: str
    type: str  # emptyDir, hostPath, persistentVolumeClaim, configMap, secret
    mount_path: str = None
    source: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.source is None:
            self.source = {}


class KubeConfig:
    """Kubernetes配置管理"""
    
    def __init__(self, config_path: str = None, context: str = None):
        """初始化配置
        
        Args:
            config_path: 配置文件路径
            context: 上下文名称
        """
        self.config_path = config_path
        self.context = context
        self._validate_config()
    
    def _validate_config(self) -> None:
        """验证配置"""
        try:
            cmd = ["kubectl", "cluster-info"]
            if self.config_path:
                cmd.extend(["--kubeconfig", self.config_path])
            if self.context:
                cmd.extend(["--context", self.context])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise Exception(f"无法连接到Kubernetes集群: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise Exception("连接Kubernetes集群超时")
        except FileNotFoundError:
            raise Exception("kubectl命令未找到，请确保已安装kubectl")
    
    def get_current_context(self) -> str:
        """获取当前上下文"""
        cmd = ["kubectl", "config", "current-context"]
        if self.config_path:
            cmd.extend(["--kubeconfig", self.config_path])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip()
    
    def list_contexts(self) -> List[str]:
        """列出所有上下文"""
        cmd = ["kubectl", "config", "get-contexts", "-o", "name"]
        if self.config_path:
            cmd.extend(["--kubeconfig", self.config_path])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip().split('\n') if result.stdout.strip() else []
    
    def set_context(self, context: str) -> None:
        """设置当前上下文"""
        cmd = ["kubectl", "config", "use-context", context]
        if self.config_path:
            cmd.extend(["--kubeconfig", self.config_path])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"设置上下文失败: {result.stderr}")
        
        self.context = context


class KubeResource:
    """Kubernetes资源管理基类"""
    
    def __init__(self, config: KubeConfig):
        """初始化资源管理
        
        Args:
            config: Kubernetes配置
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def _run_kubectl(self, args: List[str], timeout: int = 300) -> subprocess.CompletedProcess:
        """执行kubectl命令
        
        Args:
            args: 命令参数
            timeout: 超时时间（秒）
            
        Returns:
            命令执行结果
        """
        cmd = ["kubectl"] + args
        if self.config.config_path:
            cmd.extend(["--kubeconfig", self.config.config_path])
        if self.config.context:
            cmd.extend(["--context", self.config.context])
        
        self.logger.debug(f"执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        
        if result.returncode != 0:
            self.logger.error(f"命令执行失败: {result.stderr}")
            raise Exception(f"kubectl命令执行失败: {result.stderr}")
        
        return result
    
    def get(self, resource_type: ResourceType, name: str, namespace: str = "default") -> Dict[str, Any]:
        """获取资源详情
        
        Args:
            resource_type: 资源类型
            name: 资源名称
            namespace: 命名空间
            
        Returns:
            资源详情
        """
        args = ["get", resource_type.value, name, "-n", namespace, "-o", "json"]
        result = self._run_kubectl(args)
        return json.loads(result.stdout)
    
    def list(self, resource_type: ResourceType, namespace: str = "default", 
             label_selector: str = None, field_selector: str = None) -> List[Dict[str, Any]]:
        """列出资源
        
        Args:
            resource_type: 资源类型
            namespace: 命名空间
            label_selector: 标签选择器
            field_selector: 字段选择器
            
        Returns:
            资源列表
        """
        args = ["get", resource_type.value, "-n", namespace, "-o", "json"]
        
        if label_selector:
            args.extend(["-l", label_selector])
        if field_selector:
            args.extend(["--field-selector", field_selector])
        
        result = self._run_kubectl(args)
        data = json.loads(result.stdout)
        return data.get("items", [])
    
    def create(self, resource_type: ResourceType, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """创建资源
        
        Args:
            resource_type: 资源类型
            manifest: 资源清单
            
        Returns:
            创建的资源详情
        """
        args = ["create", "-f", "-", "-o", "json"]
        
        result = self._run_kubectl(args)
        return json.loads(result.stdout)
    
    def delete(self, resource_type: ResourceType, name: str, namespace: str = "default") -> bool:
        """删除资源
        
        Args:
            resource_type: 资源类型
            name: 资源名称
            namespace: 命名空间
            
        Returns:
            是否删除成功
        """
        args = ["delete", resource_type.value, name, "-n", namespace]
        
        try:
            self._run_kubectl(args)
            return True
        except Exception:
            return False
    
    def apply(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """应用资源清单
        
        Args:
            manifest: 资源清单
            
        Returns:
            应用结果
        """
        args = ["apply", "-f", "-", "-o", "json"]
        
        result = self._run_kubectl(args)
        return json.loads(result.stdout)
    
    def describe(self, resource_type: ResourceType, name: str, namespace: str = "default") -> str:
        """获取资源描述
        
        Args:
            resource_type: 资源类型
            name: 资源名称
            namespace: 命名空间
            
        Returns:
            资源描述信息
        """
        args = ["describe", resource_type.value, name, "-n", namespace]
        
        result = self._run_kubectl(args)
        return result.stdout
    
    def logs(self, pod_name: str, namespace: str = "default", container: str = None, 
             tail_lines: int = None, since: str = None) -> str:
        """获取Pod日志
        
        Args:
            pod_name: Pod名称
            namespace: 命名空间
            container: 容器名称
            tail_lines: 显示最后几行
            since: 时间范围
            
        Returns:
            日志内容
        """
        args = ["logs", pod_name, "-n", namespace]
        
        if container:
            args.extend(["-c", container])
        if tail_lines:
            args.extend(["--tail", str(tail_lines)])
        if since:
            args.extend(["--since", since])
        
        result = self._run_kubectl(args)
        return result.stdout
    
    def exec(self, pod_name: str, command: List[str], namespace: str = "default", 
             container: str = None) -> str:
        """在Pod中执行命令
        
        Args:
            pod_name: Pod名称
            command: 命令列表
            namespace: 命名空间
            container: 容器名称
            
        Returns:
            命令输出
        """
        args = ["exec", pod_name, "-n", namespace, "--"] + command
        
        if container:
            args.insert(3, "-c")
            args.insert(4, container)
        
        result = self._run_kubectl(args)
        return result.stdout


class PodManager(KubeResource):
    """Pod管理器"""
    
    def __init__(self, config: KubeConfig):
        super().__init__(config)
    
    def wait_for_pod(self, pod_name: str, namespace: str = "default", 
                     timeout: int = 300, expected_phase: PodPhase = PodPhase.RUNNING) -> bool:
        """等待Pod就绪
        
        Args:
            pod_name: Pod名称
            namespace: 命名空间
            timeout: 超时时间（秒）
            expected_phase: 期望状态
            
        Returns:
            是否就绪
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                pod = self.get(ResourceType.POD, pod_name, namespace)
                phase = pod.get("status", {}).get("phase")
                
                if phase == expected_phase.value:
                    return True
                elif phase == PodPhase.FAILED.value:
                    self.logger.error(f"Pod {pod_name} 进入Failed状态")
                    return False
                
                time.sleep(5)
            except Exception as e:
                self.logger.warning(f"获取Pod状态失败: {e}")
                time.sleep(5)
        
        self.logger.error(f"等待Pod {pod_name} 就绪超时")
        return False
    
    def get_pod_ip(self, pod_name: str, namespace: str = "default") -> Optional[str]:
        """获取Pod IP地址
        
        Args:
            pod_name: Pod名称
            namespace: 命名空间
            
        Returns:
            Pod IP地址
        """
        try:
            pod = self.get(ResourceType.POD, pod_name, namespace)
            return pod.get("status", {}).get("podIP")
        except Exception:
            return None
    
    def get_pod_events(self, pod_name: str, namespace: str = "default") -> List[Dict[str, Any]]:
        """获取Pod事件
        
        Args:
            pod_name: Pod名称
            namespace: 命名空间
            
        Returns:
            事件列表
        """
        try:
            events = self.list(ResourceType.POD, namespace, 
                             field_selector=f"involvedObject.name={pod_name}")
            return events
        except Exception:
            return []


class DeploymentManager(KubeResource):
    """部署管理器"""
    
    def __init__(self, config: KubeConfig):
        super().__init__(config)
    
    def scale(self, deployment_name: str, replicas: int, namespace: str = "default") -> bool:
        """扩缩容
        
        Args:
            deployment_name: 部署名称
            replicas: 副本数
            namespace: 命名空间
            
        Returns:
            是否成功
        """
        try:
            args = ["scale", ResourceType.DEPLOYMENT.value, deployment_name, 
                   "--replicas", str(replicas), "-n", namespace]
            self._run_kubectl(args)
            return True
        except Exception:
            return False
    
    def rollout_status(self, deployment_name: str, namespace: str = "default") -> str:
        """获取部署状态
        
        Args:
            deployment_name: 部署名称
            namespace: 命名空间
            
        Returns:
            部署状态
        """
        try:
            args = ["rollout", "status", ResourceType.DEPLOYMENT.value, 
                   deployment_name, "-n", namespace]
            result = self._run_kubectl(args)
            return result.stdout.strip()
        except Exception as e:
            return f"获取部署状态失败: {e}"
    
    def rollout_undo(self, deployment_name: str, namespace: str = "default") -> bool:
        """回滚部署
        
        Args:
            deployment_name: 部署名称
            namespace: 命名空间
            
        Returns:
            是否成功
        """
        try:
            args = ["rollout", "undo", ResourceType.DEPLOYMENT.value, 
                   deployment_name, "-n", namespace]
            self._run_kubectl(args)
            return True
        except Exception:
            return False
    
    def get_replicas(self, deployment_name: str, namespace: str = "default") -> Dict[str, int]:
        """获取副本数信息
        
        Args:
            deployment_name: 部署名称
            namespace: 命名空间
            
        Returns:
            副本数信息
        """
        try:
            deployment = self.get(ResourceType.DEPLOYMENT, deployment_name, namespace)
            status = deployment.get("status", {})
            
            return {
                "replicas": status.get("replicas", 0),
                "ready_replicas": status.get("readyReplicas", 0),
                "updated_replicas": status.get("updatedReplicas", 0),
                "available_replicas": status.get("availableReplicas", 0)
            }
        except Exception:
            return {"replicas": 0, "ready_replicas": 0, "updated_replicas": 0, "available_replicas": 0}


class ServiceManager(KubeResource):
    """服务管理器"""
    
    def __init__(self, config: KubeConfig):
        super().__init__(config)
    
    def get_service_endpoints(self, service_name: str, namespace: str = "default") -> List[str]:
        """获取服务端点
        
        Args:
            service_name: 服务名称
            namespace: 命名空间
            
        Returns:
            端点列表
        """
        try:
            service = self.get(ResourceType.SERVICE, service_name, namespace)
            endpoints = []
            
            for subset in service.get("status", {}).get("subsets", []):
                for address in subset.get("addresses", []):
                    endpoints.append(address.get("ip"))
            
            return endpoints
        except Exception:
            return []
    
    def get_service_port(self, service_name: str, namespace: str = "default") -> Optional[int]:
        """获取服务端口
        
        Args:
            service_name: 服务名称
            namespace: 命名空间
            
        Returns:
            服务端口
        """
        try:
            service = self.get(ResourceType.SERVICE, service_name, namespace)
            ports = service.get("spec", {}).get("ports", [])
            return ports[0].get("port") if ports else None
        except Exception:
            return None


class ConfigMapManager(KubeResource):
    """配置映射管理器"""
    
    def __init__(self, config: KubeConfig):
        super().__init__(config)
    
    def create_from_dict(self, name: str, data: Dict[str, str], 
                        namespace: str = "default") -> Dict[str, Any]:
        """从字典创建配置映射
        
        Args:
            name: 配置映射名称
            data: 配置数据
            namespace: 命名空间
            
        Returns:
            创建的配置映射
        """
        manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": name,
                "namespace": namespace
            },
            "data": data
        }
        
        return self.create(ResourceType.CONFIGMAP, manifest)
    
    def get_data(self, name: str, namespace: str = "default") -> Dict[str, str]:
        """获取配置映射数据
        
        Args:
            name: 配置映射名称
            namespace: 命名空间
            
        Returns:
            配置数据
        """
        try:
            configmap = self.get(ResourceType.CONFIGMAP, name, namespace)
            return configmap.get("data", {})
        except Exception:
            return {}


class SecretManager(KubeResource):
    """密钥管理器"""
    
    def __init__(self, config: KubeConfig):
        super().__init__(config)
    
    def create_from_dict(self, name: str, data: Dict[str, str], 
                        namespace: str = "default") -> Dict[str, Any]:
        """从字典创建密钥
        
        Args:
            name: 密钥名称
            data: 密钥数据（base64编码）
            namespace: 命名空间
            
        Returns:
            创建的密钥
        """
        manifest = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": name,
                "namespace": namespace
            },
            "data": data
        }
        
        return self.create(ResourceType.SECRET, manifest)
    
    def get_data(self, name: str, namespace: str = "default") -> Dict[str, str]:
        """获取密钥数据
        
        Args:
            name: 密钥名称
            namespace: 命名空间
            
        Returns:
            密钥数据
        """
        try:
            secret = self.get(ResourceType.SECRET, name, namespace)
            return secret.get("data", {})
        except Exception:
            return {}


class ManifestBuilder:
    """清单构建器"""
    
    @staticmethod
    def create_deployment(name: str, image: str, replicas: int = 1, 
                         namespace: str = "default", labels: Dict[str, str] = None,
                         containers: List[ContainerSpec] = None,
                         volumes: List[VolumeSpec] = None) -> Dict[str, Any]:
        """创建部署清单
        
        Args:
            name: 部署名称
            image: 容器镜像
            replicas: 副本数
            namespace: 命名空间
            labels: 标签
            containers: 容器规范
            volumes: 卷规范
            
        Returns:
            部署清单
        """
        if containers is None:
            containers = [ContainerSpec(name="main", image=image)]
        
        if labels is None:
            labels = {"app": name}
        
        manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": name,
                "namespace": namespace,
                "labels": labels
            },
            "spec": {
                "replicas": replicas,
                "selector": {
                    "matchLabels": labels
                },
                "template": {
                    "metadata": {
                        "labels": labels
                    },
                    "spec": {
                        "containers": []
                    }
                }
            }
        }
        
        # 添加容器
        for container in containers:
            container_spec = {
                "name": container.name,
                "image": container.image,
                "ports": container.ports,
                "env": container.env,
                "resources": container.resources
            }
            
            if container.command:
                container_spec["command"] = container.command
            if container.args:
                container_spec["args"] = container.args
            if container.volume_mounts:
                container_spec["volumeMounts"] = container.volume_mounts
            
            manifest["spec"]["template"]["spec"]["containers"].append(container_spec)
        
        # 添加卷
        if volumes:
            manifest["spec"]["template"]["spec"]["volumes"] = []
            for volume in volumes:
                volume_spec = {"name": volume.name}
                if volume.type == "emptyDir":
                    volume_spec["emptyDir"] = {}
                elif volume.type == "hostPath":
                    volume_spec["hostPath"] = volume.source
                elif volume.type == "configMap":
                    volume_spec["configMap"] = volume.source
                elif volume.type == "secret":
                    volume_spec["secret"] = volume.source
                elif volume.type == "persistentVolumeClaim":
                    volume_spec["persistentVolumeClaim"] = volume.source
                
                manifest["spec"]["template"]["spec"]["volumes"].append(volume_spec)
        
        return manifest
    
    @staticmethod
    def create_service(name: str, service_type: ServiceType = ServiceType.CLUSTER_IP,
                      ports: List[Dict[str, Any]] = None, selector: Dict[str, str] = None,
                      namespace: str = "default") -> Dict[str, Any]:
        """创建服务清单
        
        Args:
            name: 服务名称
            service_type: 服务类型
            ports: 端口配置
            selector: 选择器
            namespace: 命名空间
            
        Returns:
            服务清单
        """
        if ports is None:
            ports = [{"port": 80, "targetPort": 8080}]
        
        if selector is None:
            selector = {"app": name}
        
        manifest = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": name,
                "namespace": namespace
            },
            "spec": {
                "type": service_type.value,
                "selector": selector,
                "ports": ports
            }
        }
        
        return manifest
    
    @staticmethod
    def create_ingress(name: str, host: str, service_name: str, 
                      service_port: int, namespace: str = "default",
                      tls_enabled: bool = False) -> Dict[str, Any]:
        """创建入口清单
        
        Args:
            name: 入口名称
            host: 主机名
            service_name: 服务名称
            service_port: 服务端口
            namespace: 命名空间
            tls_enabled: 是否启用TLS
            
        Returns:
            入口清单
        """
        manifest = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": name,
                "namespace": namespace,
                "annotations": {
                    "nginx.ingress.kubernetes.io/rewrite-target": "/"
                }
            },
            "spec": {
                "rules": [
                    {
                        "host": host,
                        "http": {
                            "paths": [
                                {
                                    "path": "/",
                                    "pathType": "Prefix",
                                    "backend": {
                                        "service": {
                                            "name": service_name,
                                            "port": {
                                                "number": service_port
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        
        if tls_enabled:
            manifest["spec"]["tls"] = [
                {
                    "hosts": [host],
                    "secretName": f"{name}-tls"
                }
            ]
        
        return manifest


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, config: KubeConfig):
        """初始化健康检查器
        
        Args:
            config: Kubernetes配置
        """
        self.config = config
        self.pod_manager = PodManager(config)
        self.deployment_manager = DeploymentManager(config)
        self.service_manager = ServiceManager(config)
    
    def check_pod_health(self, pod_name: str, namespace: str = "default") -> Dict[str, Any]:
        """检查Pod健康状态
        
        Args:
            pod_name: Pod名称
            namespace: 命名空间
            
        Returns:
            健康状态信息
        """
        try:
            pod = self.pod_manager.get(ResourceType.POD, pod_name, namespace)
            status = pod.get("status", {})
            
            # 检查容器状态
            containers = status.get("containerStatuses", [])
            container_statuses = []
            
            for container in containers:
                container_statuses.append({
                    "name": container.get("name"),
                    "ready": container.get("ready", False),
                    "restart_count": container.get("restartCount", 0),
                    "state": container.get("state", {})
                })
            
            # 检查条件
            conditions = status.get("conditions", [])
            pod_conditions = {}
            for condition in conditions:
                pod_conditions[condition.get("type")] = {
                    "status": condition.get("status"),
                    "reason": condition.get("reason"),
                    "message": condition.get("message")
                }
            
            return {
                "phase": status.get("phase"),
                "pod_ip": status.get("podIP"),
                "start_time": status.get("startTime"),
                "container_statuses": container_statuses,
                "conditions": pod_conditions,
                "healthy": status.get("phase") == PodPhase.RUNNING.value
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def check_deployment_health(self, deployment_name: str, namespace: str = "default") -> Dict[str, Any]:
        """检查部署健康状态
        
        Args:
            deployment_name: 部署名称
            namespace: 命名空间
            
        Returns:
            健康状态信息
        """
        try:
            replicas_info = self.deployment_manager.get_replicas(deployment_name, namespace)
            
            return {
                "replicas": replicas_info["replicas"],
                "ready_replicas": replicas_info["ready_replicas"],
                "updated_replicas": replicas_info["updated_replicas"],
                "available_replicas": replicas_info["available_replicas"],
                "healthy": replicas_info["ready_replicas"] == replicas_info["replicas"] and replicas_info["replicas"] > 0
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def check_service_health(self, service_name: str, namespace: str = "default") -> Dict[str, Any]:
        """检查服务健康状态
        
        Args:
            service_name: 服务名称
            namespace: 命名空间
            
        Returns:
            健康状态信息
        """
        try:
            endpoints = self.service_manager.get_service_endpoints(service_name, namespace)
            port = self.service_manager.get_service_port(service_name, namespace)
            
            return {
                "endpoints": endpoints,
                "port": port,
                "endpoint_count": len(endpoints),
                "healthy": len(endpoints) > 0
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def check_namespace_health(self, namespace: str = "default") -> Dict[str, Any]:
        """检查命名空间健康状态
        
        Args:
            namespace: 命名空间
            
        Returns:
            健康状态信息
        """
        try:
            pods = self.pod_manager.list(ResourceType.POD, namespace)
            
            pod_stats = {"total": 0, "running": 0, "failed": 0, "pending": 0}
            
            for pod in pods:
                pod_stats["total"] += 1
                phase = pod.get("status", {}).get("phase")
                if phase == PodPhase.RUNNING.value:
                    pod_stats["running"] += 1
                elif phase == PodPhase.FAILED.value:
                    pod_stats["failed"] += 1
                elif phase == PodPhase.PENDING.value:
                    pod_stats["pending"] += 1
            
            return {
                "pods": pod_stats,
                "healthy": pod_stats["failed"] == 0 and pod_stats["pending"] == 0
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}


class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self, config: KubeConfig):
        """初始化资源监控器
        
        Args:
            config: Kubernetes配置
        """
        self.config = config
        self.pod_manager = PodManager(config)
        self.logger = logging.getLogger(__name__)
    
    def monitor_pod_resources(self, pod_name: str, namespace: str = "default", 
                             duration: int = 60, interval: int = 10) -> List[Dict[str, Any]]:
        """监控Pod资源使用
        
        Args:
            pod_name: Pod名称
            namespace: 命名空间
            duration: 监控持续时间（秒）
            interval: 采样间隔（秒）
            
        Returns:
            资源使用数据列表
        """
        metrics = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                # 获取Pod资源使用情况
                pod = self.pod_manager.get(ResourceType.POD, pod_name, namespace)
                
                # 这里简化处理，实际应该使用metrics-server API
                metric = {
                    "timestamp": datetime.now().isoformat(),
                    "pod_name": pod_name,
                    "namespace": namespace,
                    "phase": pod.get("status", {}).get("phase"),
                    "pod_ip": pod.get("status", {}).get("podIP")
                }
                
                metrics.append(metric)
                
                time.sleep(interval)
            except Exception as e:
                self.logger.warning(f"获取Pod {pod_name} 资源信息失败: {e}")
                time.sleep(interval)
        
        return metrics
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """获取集群信息
        
        Returns:
            集群信息
        """
        try:
            # 获取节点信息
            nodes = self.pod_manager.list(ResourceType.POD, "kube-system", 
                                        field_selector="spec.nodeName")
            
            # 统计Pod分布
            node_pod_count = {}
            for pod in nodes:
                node_name = pod.get("spec", {}).get("nodeName")
                if node_name:
                    node_pod_count[node_name] = node_pod_count.get(node_name, 0) + 1
            
            return {
                "timestamp": datetime.now().isoformat(),
                "node_pod_distribution": node_pod_count,
                "total_monitored_pods": len(nodes)
            }
        except Exception as e:
            return {"error": str(e)}


class DeploymentOrchestrator:
    """部署编排器"""
    
    def __init__(self, config: KubeConfig):
        """初始化部署编排器
        
        Args:
            config: Kubernetes配置
        """
        self.config = config
        self.pod_manager = PodManager(config)
        self.deployment_manager = DeploymentManager(config)
        self.service_manager = ServiceManager(config)
        self.logger = logging.getLogger(__name__)
    
    def deploy_application(self, deployment_config: Dict[str, Any], 
                          service_config: Dict[str, Any] = None,
                          wait_ready: bool = True, timeout: int = 300) -> Dict[str, Any]:
        """部署应用
        
        Args:
            deployment_config: 部署配置
            service_config: 服务配置（可选）
            wait_ready: 是否等待就绪
            timeout: 超时时间（秒）
            
        Returns:
            部署结果
        """
        result = {
            "success": False,
            "deployment_name": deployment_config.get("metadata", {}).get("name"),
            "service_name": service_config.get("metadata", {}).get("name") if service_config else None,
            "errors": []
        }
        
        try:
            # 创建部署
            self.logger.info(f"创建部署: {result['deployment_name']}")
            deployment = self.deployment_manager.apply(deployment_config)
            result["deployment_created"] = True
            
            # 创建服务（如果配置了）
            if service_config:
                self.logger.info(f"创建服务: {result['service_name']}")
                service = self.service_manager.apply(service_config)
                result["service_created"] = True
            
            # 等待就绪
            if wait_ready:
                self.logger.info("等待部署就绪...")
                deployment_name = result["deployment_name"]
                namespace = deployment_config.get("metadata", {}).get("namespace", "default")
                
                start_time = time.time()
                while time.time() - start_time < timeout:
                    replicas_info = self.deployment_manager.get_replicas(deployment_name, namespace)
                    
                    if (replicas_info["ready_replicas"] == replicas_info["replicas"] and 
                        replicas_info["replicas"] > 0):
                        result["ready"] = True
                        break
                    
                    time.sleep(5)
                
                if not result.get("ready"):
                    result["errors"].append("部署就绪超时")
            
            result["success"] = len(result["errors"]) == 0
            
        except Exception as e:
            result["errors"].append(str(e))
            self.logger.error(f"部署失败: {e}")
        
        return result
    
    def rollback_application(self, deployment_name: str, namespace: str = "default") -> bool:
        """回滚应用
        
        Args:
            deployment_name: 部署名称
            namespace: 命名空间
            
        Returns:
            是否成功
        """
        try:
            self.logger.info(f"回滚部署: {deployment_name}")
            success = self.deployment_manager.rollout_undo(deployment_name, namespace)
            
            if success:
                # 等待回滚完成
                time.sleep(10)
                self.logger.info(f"部署 {deployment_name} 回滚完成")
            
            return success
        except Exception as e:
            self.logger.error(f"回滚失败: {e}")
            return False
    
    def scale_application(self, deployment_name: str, replicas: int, 
                         namespace: str = "default") -> bool:
        """扩缩容应用
        
        Args:
            deployment_name: 部署名称
            replicas: 目标副本数
            namespace: 命名空间
            
        Returns:
            是否成功
        """
        try:
            self.logger.info(f"扩缩容部署 {deployment_name} 到 {replicas} 个副本")
            success = self.deployment_manager.scale(deployment_name, replicas, namespace)
            
            if success:
                # 等待扩缩容完成
                time.sleep(5)
                self.logger.info(f"部署 {deployment_name} 扩缩容完成")
            
            return success
        except Exception as e:
            self.logger.error(f"扩缩容失败: {e}")
            return False


class DockerManager:
    """Docker管理器"""
    
    def __init__(self):
        """初始化Docker管理器"""
        self.logger = logging.getLogger(__name__)
    
    def build_image(self, dockerfile_path: str, image_name: str, tag: str = "latest",
                   build_args: Dict[str, str] = None) -> bool:
        """构建Docker镜像
        
        Args:
            dockerfile_path: Dockerfile路径
            image_name: 镜像名称
            tag: 标签
            build_args: 构建参数
            
        Returns:
            是否成功
        """
        try:
            cmd = ["docker", "build", "-t", f"{image_name}:{tag}", "-f", dockerfile_path, "."]
            
            if build_args:
                for key, value in build_args.items():
                    cmd.extend(["--build-arg", f"{key}={value}"])
            
            self.logger.info(f"构建镜像: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"镜像构建成功: {image_name}:{tag}")
                return True
            else:
                self.logger.error(f"镜像构建失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"构建镜像异常: {e}")
            return False
    
    def push_image(self, image_name: str, tag: str = "latest", registry: str = None) -> bool:
        """推送Docker镜像
        
        Args:
            image_name: 镜像名称
            tag: 标签
            registry: 注册表地址
            
        Returns:
            是否成功
        """
        try:
            full_image_name = f"{image_name}:{tag}"
            if registry:
                full_image_name = f"{registry}/{full_image_name}"
            
            cmd = ["docker", "push", full_image_name]
            
            self.logger.info(f"推送镜像: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"镜像推送成功: {full_image_name}")
                return True
            else:
                self.logger.error(f"镜像推送失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"推送镜像异常: {e}")
            return False
    
    def pull_image(self, image_name: str, tag: str = "latest", registry: str = None) -> bool:
        """拉取Docker镜像
        
        Args:
            image_name: 镜像名称
            tag: 标签
            registry: 注册表地址
            
        Returns:
            是否成功
        """
        try:
            full_image_name = f"{image_name}:{tag}"
            if registry:
                full_image_name = f"{registry}/{full_image_name}"
            
            cmd = ["docker", "pull", full_image_name]
            
            self.logger.info(f"拉取镜像: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"镜像拉取成功: {full_image_name}")
                return True
            else:
                self.logger.error(f"镜像拉取失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"拉取镜像异常: {e}")
            return False
    
    def run_container(self, image_name: str, container_name: str = None,
                     ports: Dict[int, int] = None, environment: Dict[str, str] = None,
                     volumes: Dict[str, str] = None, command: List[str] = None,
                     detach: bool = True) -> Optional[str]:
        """运行Docker容器
        
        Args:
            image_name: 镜像名称
            container_name: 容器名称
            ports: 端口映射 {host_port: container_port}
            environment: 环境变量
            volumes: 卷映射 {host_path: container_path}
            command: 运行命令
            detach: 是否后台运行
            
        Returns:
            容器ID
        """
        try:
            cmd = ["docker", "run"]
            
            if container_name:
                cmd.extend(["--name", container_name])
            if detach:
                cmd.append("-d")
            
            # 端口映射
            if ports:
                for host_port, container_port in ports.items():
                    cmd.extend(["-p", f"{host_port}:{container_port}"])
            
            # 环境变量
            if environment:
                for key, value in environment.items():
                    cmd.extend(["-e", f"{key}={value}"])
            
            # 卷映射
            if volumes:
                for host_path, container_path in volumes.items():
                    cmd.extend(["-v", f"{host_path}:{container_path}"])
            
            cmd.append(image_name)
            
            # 命令
            if command:
                cmd.extend(command)
            
            self.logger.info(f"运行容器: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                container_id = result.stdout.strip()
                self.logger.info(f"容器运行成功: {container_id}")
                return container_id
            else:
                self.logger.error(f"容器运行失败: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"运行容器异常: {e}")
            return None
    
    def stop_container(self, container_name: str, timeout: int = 10) -> bool:
        """停止Docker容器
        
        Args:
            container_name: 容器名称或ID
            timeout: 超时时间（秒）
            
        Returns:
            是否成功
        """
        try:
            cmd = ["docker", "stop", "--time", str(timeout), container_name]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"容器停止成功: {container_name}")
                return True
            else:
                self.logger.error(f"容器停止失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"停止容器异常: {e}")
            return False
    
    def remove_container(self, container_name: str, force: bool = False) -> bool:
        """删除Docker容器
        
        Args:
            container_name: 容器名称或ID
            force: 是否强制删除
            
        Returns:
            是否成功
        """
        try:
            cmd = ["docker", "rm"]
            if force:
                cmd.append("-f")
            cmd.append(container_name)
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"容器删除成功: {container_name}")
                return True
            else:
                self.logger.error(f"容器删除失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"删除容器异常: {e}")
            return False


def setup_logging(level: str = "INFO") -> None:
    """设置日志配置
    
    Args:
        level: 日志级别
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('k8s_operations.log')
        ]
    )