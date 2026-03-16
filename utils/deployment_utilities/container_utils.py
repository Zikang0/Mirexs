"""
容器工具模块

提供Docker容器管理和编排工具。
"""

import os
import json
import subprocess
import time
from typing import Dict, List, Optional, Any, Union
import yaml
from pathlib import Path


class DockerManager:
    """Docker管理器"""
    
    def __init__(self):
        """初始化Docker管理器"""
        self.docker_cmd = 'docker'
        self.docker_compose_cmd = 'docker-compose'
    
    def _run_command(self, command: List[str], capture_output: bool = True) -> Dict[str, Any]:
        """运行Docker命令
        
        Args:
            command: 命令列表
            capture_output: 是否捕获输出
            
        Returns:
            命令执行结果
        """
        try:
            if capture_output:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return {
                    'success': True,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                }
            else:
                result = subprocess.run(command, check=True)
                return {
                    'success': True,
                    'returncode': result.returncode
                }
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'stdout': e.stdout if hasattr(e, 'stdout') else '',
                'stderr': e.stderr if hasattr(e, 'stderr') else '',
                'returncode': e.returncode,
                'error': str(e)
            }
    
    def is_docker_available(self) -> bool:
        """检查Docker是否可用
        
        Returns:
            Docker是否可用
        """
        result = self._run_command([self.docker_cmd, '--version'])
        return result['success']
    
    def get_docker_info(self) -> Dict[str, Any]:
        """获取Docker信息
        
        Returns:
            Docker信息字典
        """
        result = self._run_command([self.docker_cmd, 'info', '--format', '{{json .}}'])
        if result['success']:
            try:
                return json.loads(result['stdout'])
            except json.JSONDecodeError:
                return {}
        return {}
    
    def list_containers(self, all_containers: bool = False) -> List[Dict[str, Any]]:
        """列出容器
        
        Args:
            all_containers: 是否显示所有容器（包括已停止的）
            
        Returns:
            容器列表
        """
        command = [self.docker_cmd, 'ps', '--format', '{{json .}}']
        if all_containers:
            command.append('-a')
        
        result = self._run_command(command)
        if result['success']:
            containers = []
            for line in result['stdout'].strip().split('\n'):
                if line:
                    try:
                        containers.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return containers
        return []
    
    def get_container_info(self, container_id: str) -> Dict[str, Any]:
        """获取容器详细信息
        
        Args:
            container_id: 容器ID
            
        Returns:
            容器信息字典
        """
        result = self._run_command([
            self.docker_cmd, 'inspect', '--format', '{{json .}}', container_id
        ])
        if result['success']:
            try:
                info = json.loads(result['stdout'])
                return info[0] if isinstance(info, list) else info
            except (json.JSONDecodeError, IndexError):
                return {}
        return {}
    
    def start_container(self, container_id: str) -> bool:
        """启动容器
        
        Args:
            container_id: 容器ID
            
        Returns:
            是否启动成功
        """
        result = self._run_command([self.docker_cmd, 'start', container_id])
        return result['success']
    
    def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        """停止容器
        
        Args:
            container_id: 容器ID
            timeout: 超时时间（秒）
            
        Returns:
            是否停止成功
        """
        result = self._run_command([
            self.docker_cmd, 'stop', '-t', str(timeout), container_id
        ])
        return result['success']
    
    def restart_container(self, container_id: str) -> bool:
        """重启容器
        
        Args:
            container_id: 容器ID
            
        Returns:
            是否重启成功
        """
        result = self._run_command([self.docker_cmd, 'restart', container_id])
        return result['success']
    
    def remove_container(self, container_id: str, force: bool = False) -> bool:
        """删除容器
        
        Args:
            container_id: 容器ID
            force: 是否强制删除
            
        Returns:
            是否删除成功
        """
        command = [self.docker_cmd, 'rm']
        if force:
            command.append('-f')
        command.append(container_id)
        
        result = self._run_command(command)
        return result['success']
    
    def get_container_logs(self, container_id: str, tail: int = 100) -> str:
        """获取容器日志
        
        Args:
            container_id: 容器ID
            tail: 显示最后多少行
            
        Returns:
            日志内容
        """
        result = self._run_command([
            self.docker_cmd, 'logs', '--tail', str(tail), container_id
        ])
        return result['stdout'] if result['success'] else ''
    
    def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """获取容器资源使用统计
        
        Args:
            container_id: 容器ID
            
        Returns:
            资源使用统计
        """
        result = self._run_command([
            self.docker_cmd, 'stats', '--no-stream', '--format', '{{json .}}', container_id
        ])
        if result['success']:
            try:
                return json.loads(result['stdout'])
            except json.JSONDecodeError:
                return {}
        return {}
    
    def execute_command(self, container_id: str, command: Union[str, List[str]]) -> Dict[str, Any]:
        """在容器中执行命令
        
        Args:
            container_id: 容器ID
            command: 要执行的命令
            
        Returns:
            命令执行结果
        """
        if isinstance(command, str):
            command = command.split()
        
        cmd = [self.docker_cmd, 'exec', container_id] + command
        result = self._run_command(cmd)
        return result
    
    def get_container_ip(self, container_id: str) -> str:
        """获取容器IP地址
        
        Args:
            container_id: 容器ID
            
        Returns:
            容器IP地址
        """
        result = self._run_command([
            self.docker_cmd, 'inspect', '--format', '{{.NetworkSettings.IPAddress}}', container_id
        ])
        return result['stdout'].strip() if result['success'] else ''


class DockerImageManager:
    """Docker镜像管理器"""
    
    def __init__(self):
        """初始化Docker镜像管理器"""
        self.docker_cmd = 'docker'
    
    def _run_command(self, command: List[str]) -> Dict[str, Any]:
        """运行Docker命令"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return {
                'success': True,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'stdout': e.stdout if hasattr(e, 'stdout') else '',
                'stderr': e.stderr if hasattr(e, 'stderr') else '',
                'returncode': e.returncode,
                'error': str(e)
            }
    
    def list_images(self, all_images: bool = False) -> List[Dict[str, Any]]:
        """列出镜像
        
        Args:
            all_images: 是否显示所有镜像（包括中间层）
            
        Returns:
            镜像列表
        """
        command = [self.docker_cmd, 'images', '--format', '{{json .}}']
        if all_images:
            command.append('-a')
        
        result = self._run_command(command)
        if result['success']:
            images = []
            for line in result['stdout'].strip().split('\n'):
                if line:
                    try:
                        images.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return images
        return []
    
    def pull_image(self, image_name: str, tag: str = 'latest') -> bool:
        """拉取镜像
        
        Args:
            image_name: 镜像名称
            tag: 镜像标签
            
        Returns:
            是否拉取成功
        """
        full_image_name = f"{image_name}:{tag}"
        result = self._run_command([self.docker_cmd, 'pull', full_image_name])
        return result['success']
    
    def build_image(self, dockerfile_path: str, image_name: str, 
                   build_args: Dict[str, str] = None, tag: str = 'latest') -> bool:
        """构建镜像
        
        Args:
            dockerfile_path: Dockerfile路径
            image_name: 镜像名称
            build_args: 构建参数
            tag: 镜像标签
            
        Returns:
            是否构建成功
        """
        command = [self.docker_cmd, 'build', '-t', f"{image_name}:{tag}"]
        
        if build_args:
            for key, value in build_args.items():
                command.extend(['--build-arg', f"{key}={value}"])
        
        command.append('-f')
        command.append(dockerfile_path)
        command.append('.')
        
        result = self._run_command(command)
        return result['success']
    
    def remove_image(self, image_name: str, force: bool = False) -> bool:
        """删除镜像
        
        Args:
            image_name: 镜像名称
            force: 是否强制删除
            
        Returns:
            是否删除成功
        """
        command = [self.docker_cmd, 'rmi']
        if force:
            command.append('-f')
        command.append(image_name)
        
        result = self._run_command(command)
        return result['success']
    
    def get_image_info(self, image_name: str) -> Dict[str, Any]:
        """获取镜像详细信息
        
        Args:
            image_name: 镜像名称
            
        Returns:
            镜像信息字典
        """
        result = self._run_command([
            self.docker_cmd, 'inspect', '--format', '{{json .}}', image_name
        ])
        if result['success']:
            try:
                info = json.loads(result['stdout'])
                return info[0] if isinstance(info, list) else info
            except (json.JSONDecodeError, IndexError):
                return {}
        return {}
    
    def get_image_size(self, image_name: str) -> str:
        """获取镜像大小
        
        Args:
            image_name: 镜像名称
            
        Returns:
            镜像大小字符串
        """
        result = self._run_command([
            self.docker_cmd, 'images', '--format', '{{.Size}}', image_name
        ])
        return result['stdout'].strip() if result['success'] else ''


class DockerComposeManager:
    """Docker Compose管理器"""
    
    def __init__(self, compose_file: str = 'docker-compose.yml'):
        """初始化Docker Compose管理器
        
        Args:
            compose_file: Docker Compose文件路径
        """
        self.compose_file = compose_file
        self.compose_cmd = 'docker-compose'
    
    def _run_command(self, command: List[str]) -> Dict[str, Any]:
        """运行Docker Compose命令"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return {
                'success': True,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'stdout': e.stdout if hasattr(e, 'stdout') else '',
                'stderr': e.stderr if hasattr(e, 'stderr') else '',
                'returncode': e.returncode,
                'error': str(e)
            }
    
    def up(self, detached: bool = True, rebuild: bool = False) -> bool:
        """启动服务
        
        Args:
            detached: 是否后台运行
            rebuild: 是否重新构建镜像
            
        Returns:
            是否启动成功
        """
        command = [self.compose_cmd, '-f', self.compose_file, 'up']
        
        if detached:
            command.append('-d')
        if rebuild:
            command.append('--build')
        
        result = self._run_command(command)
        return result['success']
    
    def down(self, remove_volumes: bool = False) -> bool:
        """停止并删除服务
        
        Args:
            remove_volumes: 是否删除数据卷
            
        Returns:
            是否停止成功
        """
        command = [self.compose_cmd, '-f', self.compose_file, 'down']
        if remove_volumes:
            command.append('-v')
        
        result = self._run_command(command)
        return result['success']
    
    def restart(self, service_name: str = None) -> bool:
        """重启服务
        
        Args:
            service_name: 服务名称，如果为None则重启所有服务
            
        Returns:
            是否重启成功
        """
        command = [self.compose_cmd, '-f', self.compose_file, 'restart']
        if service_name:
            command.append(service_name)
        
        result = self._run_command(command)
        return result['success']
    
    def ps(self) -> List[Dict[str, Any]]:
        """查看服务状态
        
        Returns:
            服务状态列表
        """
        result = self._run_command([
            self.compose_cmd, '-f', self.compose_file, 'ps', '--format', '{{json .}}'
        ])
        if result['success']:
            services = []
            for line in result['stdout'].strip().split('\n'):
                if line:
                    try:
                        services.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return services
        return []
    
    def logs(self, service_name: str = None, tail: int = 100) -> str:
        """查看服务日志
        
        Args:
            service_name: 服务名称
            tail: 显示最后多少行
            
        Returns:
            日志内容
        """
        command = [self.compose_cmd, '-f', self.compose_file, 'logs', '--tail', str(tail)]
        if service_name:
            command.append(service_name)
        
        result = self._run_command(command)
        return result['stdout'] if result['success'] else ''
    
    def exec_command(self, service_name: str, command: Union[str, List[str]]) -> Dict[str, Any]:
        """在服务中执行命令
        
        Args:
            service_name: 服务名称
            command: 要执行的命令
            
        Returns:
            命令执行结果
        """
        if isinstance(command, str):
            command = command.split()
        
        cmd = [self.compose_cmd, '-f', self.compose_file, 'exec', service_name] + command
        return self._run_command(cmd)
    
    def scale(self, service_name: str, replicas: int) -> bool:
        """扩缩容服务
        
        Args:
            service_name: 服务名称
            replicas: 副本数量
            
        Returns:
            是否扩缩容成功
        """
        result = self._run_command([
            self.compose_cmd, '-f', self.compose_file, 'up', 
            '--scale', f"{service_name}={replicas}", '-d'
        ])
        return result['success']


class ContainerOrchestrator:
    """容器编排器"""
    
    def __init__(self):
        """初始化容器编排器"""
        self.docker_manager = DockerManager()
        self.compose_manager = None
    
    def deploy_application(self, compose_file: str, 
                          environment: str = 'production') -> Dict[str, Any]:
        """部署应用程序
        
        Args:
            compose_file: Docker Compose文件路径
            environment: 部署环境
            
        Returns:
            部署结果
        """
        try:
            # 设置环境变量
            os.environ['COMPOSE_PROJECT_NAME'] = environment
            
            # 创建Compose管理器
            self.compose_manager = DockerComposeManager(compose_file)
            
            # 启动服务
            success = self.compose_manager.up(detached=True, rebuild=True)
            
            if success:
                # 等待服务启动
                time.sleep(10)
                
                # 检查服务状态
                services = self.compose_manager.ps()
                running_services = [s for s in services if s.get('State') == 'running']
                
                return {
                    'success': True,
                    'services': len(services),
                    'running_services': len(running_services),
                    'message': '应用程序部署成功'
                }
            else:
                return {
                    'success': False,
                    'message': '应用程序部署失败'
                }
        
        except Exception as e:
            return {
                'success': False,
                'message': f'部署过程中发生错误: {str(e)}'
            }
    
    def scale_service(self, service_name: str, replicas: int) -> bool:
        """扩缩容服务
        
        Args:
            service_name: 服务名称
            replicas: 副本数量
            
        Returns:
            是否扩缩容成功
        """
        if self.compose_manager:
            return self.compose_manager.scale(service_name, replicas)
        return False
    
    def update_service(self, service_name: str, image_tag: str) -> bool:
        """更新服务镜像
        
        Args:
            service_name: 服务名称
            image_tag: 新的镜像标签
            
        Returns:
            是否更新成功
        """
        # 这里需要实现镜像更新逻辑
        # 可以通过修改Compose文件或使用Docker命令来实现
        return True
    
    def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """获取服务健康状态
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务健康状态
        """
        if self.compose_manager:
            services = self.compose_manager.ps()
            for service in services:
                if service.get('Name') == service_name:
                    return {
                        'name': service_name,
                        'state': service.get('State'),
                        'ports': service.get('Ports', ''),
                        'command': service.get('Command', '')
                    }
        return {'name': service_name, 'state': 'unknown'}
    
    def rollback_service(self, service_name: str) -> bool:
        """回滚服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            是否回滚成功
        """
        # 这里需要实现回滚逻辑
        # 可以通过使用之前的镜像版本来实现
        return True
    
    def cleanup_unused_resources(self) -> Dict[str, Any]:
        """清理未使用的资源
        
        Returns:
            清理结果
        """
        results = {
            'removed_containers': 0,
            'removed_images': 0,
            'removed_volumes': 0,
            'removed_networks': 0
        }
        
        # 清理未使用的容器
        containers = self.docker_manager.list_containers(all_containers=True)
        for container in containers:
            if container.get('State') == 'exited':
                if self.docker_manager.remove_container(container.get('ID', ''), force=True):
                    results['removed_containers'] += 1
        
        # 清理未使用的镜像
        images = self.docker_manager.list_images(all_images=True)
        for image in images:
            if not image.get('Repository'):  # 中间层镜像
                if self.docker_manager.remove_image(image.get('ID', ''), force=True):
                    results['removed_images'] += 1
        
        return results


class ContainerMonitor:
    """容器监控器"""
    
    def __init__(self):
        """初始化容器监控器"""
        self.docker_manager = DockerManager()
    
    def get_container_metrics(self, container_id: str = None) -> Dict[str, Any]:
        """获取容器指标
        
        Args:
            container_id: 容器ID，如果为None则获取所有容器
            
        Returns:
            容器指标字典
        """
        if container_id:
            containers = [container_id]
        else:
            running_containers = self.docker_manager.list_containers()
            containers = [c.get('ID') for c in running_containers if c.get('ID')]
        
        metrics = {}
        for container_id in containers:
            try:
                stats = self.docker_manager.get_container_stats(container_id)
                info = self.docker_manager.get_container_info(container_id)
                
                metrics[container_id] = {
                    'name': info.get('Name', '').lstrip('/'),
                    'image': info.get('Config', {}).get('Image', ''),
                    'state': info.get('State', {}).get('Status', ''),
                    'cpu_percent': stats.get('CPUPerc', '0%'),
                    'memory_usage': stats.get('MEM_USAGE', '0B'),
                    'memory_limit': stats.get('MEM_LIMIT', '0B'),
                    'memory_percent': stats.get('MEM_PERC', '0%'),
                    'network_io': {
                        'rx': stats.get('NET_IO', '0B').split('/')[0],
                        'tx': stats.get('NET_IO', '0B').split('/')[1] if '/' in stats.get('NET_IO', '') else '0B'
                    },
                    'block_io': {
                        'read': stats.get('BLOCK_IO', '0B').split('/')[0],
                        'write': stats.get('BLOCK_IO', '0B').split('/')[1] if '/' in stats.get('BLOCK_IO', '') else '0B'
                    }
                }
            except Exception:
                continue
        
        return metrics
    
    def get_system_resources(self) -> Dict[str, Any]:
        """获取系统资源使用情况
        
        Returns:
            系统资源使用情况
        """
        docker_info = self.docker_manager.get_docker_info()
        
        return {
            'containers': {
                'total': docker_info.get('Containers', 0),
                'running': docker_info.get('ContainersRunning', 0),
                'paused': docker_info.get('ContainersPaused', 0),
                'stopped': docker_info.get('ContainersStopped', 0)
            },
            'images': docker_info.get('Images', 0),
            'memory': {
                'total': docker_info.get('MemTotal', 0),
                'used': docker_info.get('MemUsage', {}).get('Used', 0),
                'free': docker_info.get('MemUsage', {}).get('Cache', 0)
            },
            'cpu': {
                'count': docker_info.get('NCPU', 0),
                'load_average': docker_info.get('Load', [])
            }
        }


def create_dockerfile(project_name: str, base_image: str = 'python:3.9-slim',
                     workdir: str = '/app') -> str:
    """生成Dockerfile模板
    
    Args:
        project_name: 项目名称
        base_image: 基础镜像
        workdir: 工作目录
        
    Returns:
        Dockerfile内容
    """
    dockerfile_content = f"""# {project_name} Dockerfile
FROM {base_image}

# 设置工作目录
WORKDIR {workdir}

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "main.py"]
"""
    return dockerfile_content


def create_docker_compose(services: Dict[str, Dict[str, Any]]) -> str:
    """生成Docker Compose配置
    
    Args:
        services: 服务配置字典
        
    Returns:
        Docker Compose配置内容
    """
    compose_config = {
        'version': '3.8',
        'services': services
    }
    
    return yaml.dump(compose_config, default_flow_style=False, indent=2)


def create_kubernetes_deployment(service_name: str, image: str, 
                                replicas: int = 1, port: int = 80) -> Dict[str, Any]:
    """生成Kubernetes部署配置
    
    Args:
        service_name: 服务名称
        image: 容器镜像
        replicas: 副本数
        port: 服务端口
        
    Returns:
        Kubernetes部署配置字典
    """
    return {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': {
            'name': service_name,
            'labels': {
                'app': service_name
            }
        },
        'spec': {
            'replicas': replicas,
            'selector': {
                'matchLabels': {
                    'app': service_name
                }
            },
            'template': {
                'metadata': {
                    'labels': {
                        'app': service_name
                    }
                },
                'spec': {
                    'containers': [{
                        'name': service_name,
                        'image': image,
                        'ports': [{
                            'containerPort': port
                        }]
                    }]
                }
            }
        }
    }