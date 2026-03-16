"""
技能注册模块 - 管理系统技能注册和执行
"""

import logging
import json
import importlib
import inspect
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class SkillCategory(Enum):
    """技能分类枚举"""
    CREATIVE = "creative"
    TECHNICAL = "technical"
    PRODUCTIVITY = "productivity"
    COMMUNICATION = "communication"
    ANALYSIS = "analysis"
    AUTOMATION = "automation"

class SkillStatus(Enum):
    """技能状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"

@dataclass
class SkillParameter:
    """技能参数数据类"""
    name: str
    data_type: str
    description: str
    required: bool
    default_value: Any

@dataclass
class SkillMetadata:
    """技能元数据数据类"""
    author: str
    version: str
    dependencies: List[str]
    tags: List[str]
    execution_timeout: int  # 秒

@dataclass
class RegisteredSkill:
    """注册技能数据类"""
    skill_id: str
    name: str
    description: str
    category: SkillCategory
    status: SkillStatus
    parameters: List[SkillParameter]
    metadata: SkillMetadata
    handler_module: str
    handler_function: str
    created_at: datetime
    updated_at: datetime
    execution_count: int
    success_count: int
    average_execution_time: float

class SkillRegistry:
    """技能注册表管理器"""
    
    def __init__(self, db_integration, config: Dict[str, Any]):
        """
        初始化技能注册表管理器
        
        Args:
            db_integration: 数据库集成实例
            config: 配置字典
        """
        self.db = db_integration
        self.config = config
        self.logger = logger
        
        # 表名配置
        self.skills_table = config.get('skills_table', 'registered_skills')
        self.skill_executions_table = config.get('skill_executions_table', 'skill_executions')
        
        # 运行时技能缓存
        self._skills_cache = {}
        
        # 初始化表结构
        self._initialize_tables()
    
    def _initialize_tables(self):
        """初始化技能注册相关表"""
        try:
            # 技能注册表
            skills_schema = {
                'skill_id': 'VARCHAR(100) PRIMARY KEY',
                'name': 'VARCHAR(255) NOT NULL',
                'description': 'TEXT',
                'category': 'VARCHAR(50) NOT NULL',
                'status': 'VARCHAR(20) DEFAULT "active"',
                'parameters': 'TEXT NOT NULL',  # JSON格式
                'metadata': 'TEXT NOT NULL',  # JSON格式
                'handler_module': 'VARCHAR(255) NOT NULL',
                'handler_function': 'VARCHAR(100) NOT NULL',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'execution_count': 'INTEGER DEFAULT 0',
                'success_count': 'INTEGER DEFAULT 0',
                'average_execution_time': 'FLOAT DEFAULT 0.0'
            }
            
            self.db.create_table(self.skills_table, skills_schema)
            
            # 技能执行记录表
            executions_schema = {
                'execution_id': 'SERIAL PRIMARY KEY',
                'skill_id': 'VARCHAR(100) NOT NULL',
                'parameters': 'TEXT',  # JSON格式
                'result': 'TEXT',  # JSON格式
                'status': 'VARCHAR(20) NOT NULL',  # success, failed, timeout
                'start_time': 'TIMESTAMP NOT NULL',
                'end_time': 'TIMESTAMP',
                'execution_time': 'FLOAT',
                'error_message': 'TEXT',
                'initiated_by': 'VARCHAR(100)'
            }
            
            constraints = [
                'FOREIGN KEY (skill_id) REFERENCES registered_skills(skill_id) ON DELETE CASCADE'
            ]
            
            self.db.create_table(self.skill_executions_table, executions_schema, constraints)
            
            # 创建索引
            self.db.create_index(self.skills_table, 'category')
            self.db.create_index(self.skills_table, 'status')
            self.db.create_index(self.skills_table, 'name')
            self.db.create_index(self.skill_executions_table, 'skill_id')
            self.db.create_index(self.skill_executions_table, 'start_time')
            self.db.create_index(self.skill_executions_table, 'status')
            
            self.logger.info("Skill registry tables initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize skill registry tables: {str(e)}")
            raise
    
    def register_skill(self, skill_data: Dict[str, Any]) -> bool:
        """
        注册新技能
        
        Args:
            skill_data: 技能数据
            
        Returns:
            bool: 注册是否成功
        """
        try:
            # 验证技能数据
            if not self._validate_skill_data(skill_data):
                return False
            
            # 准备数据库数据
            db_data = {
                'skill_id': skill_data['skill_id'],
                'name': skill_data['name'],
                'description': skill_data.get('description', ''),
                'category': skill_data['category'].value,
                'status': skill_data.get('status', SkillStatus.ACTIVE).value,
                'parameters': json.dumps([asdict(param) for param in skill_data['parameters']]),
                'metadata': json.dumps(asdict(skill_data['metadata'])),
                'handler_module': skill_data['handler_module'],
                'handler_function': skill_data['handler_function'],
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # 检查技能是否已存在
            existing = self.get_skill(skill_data['skill_id'])
            if existing:
                self.logger.warning(f"Skill already exists: {skill_data['skill_id']}")
                return False
            
            # 插入数据库
            self.db.execute_insert(self.skills_table, db_data)
            
            # 更新缓存
            self._skills_cache[skill_data['skill_id']] = RegisteredSkill(**skill_data)
            
            self.logger.info(f"Skill registered: {skill_data['skill_id']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register skill: {str(e)}")
            return False
    
    def get_skill(self, skill_id: str) -> Optional[RegisteredSkill]:
        """
        获取技能信息
        
        Args:
            skill_id: 技能ID
            
        Returns:
            RegisteredSkill: 技能信息，如果不存在返回None
        """
        try:
            # 检查缓存
            if skill_id in self._skills_cache:
                return self._skills_cache[skill_id]
            
            query = f"SELECT * FROM {self.skills_table} WHERE skill_id = %s"
            results = self.db.execute_query(query, (skill_id,))
            
            if not results:
                return None
            
            skill_data = results[0]
            
            # 转换为RegisteredSkill对象
            skill = RegisteredSkill(
                skill_id=skill_data['skill_id'],
                name=skill_data['name'],
                description=skill_data['description'],
                category=SkillCategory(skill_data['category']),
                status=SkillStatus(skill_data['status']),
                parameters=[SkillParameter(**param) for param in json.loads(skill_data['parameters'])],
                metadata=SkillMetadata(**json.loads(skill_data['metadata'])),
                handler_module=skill_data['handler_module'],
                handler_function=skill_data['handler_function'],
                created_at=skill_data['created_at'],
                updated_at=skill_data['updated_at'],
                execution_count=skill_data['execution_count'],
                success_count=skill_data['success_count'],
                average_execution_time=skill_data['average_execution_time']
            )
            
            # 更新缓存
            self._skills_cache[skill_id] = skill
            
            return skill
            
        except Exception as e:
            self.logger.error(f"Failed to get skill: {str(e)}")
            return None
    
    def execute_skill(self, skill_id: str, parameters: Dict[str, Any] = None,
                     initiated_by: str = "system") -> Dict[str, Any]:
        """
        执行技能
        
        Args:
            skill_id: 技能ID
            parameters: 执行参数
            initiated_by: 发起者
            
        Returns:
            Dict: 执行结果
        """
        execution_id = None
        start_time = datetime.now()
        
        try:
            # 获取技能信息
            skill = self.get_skill(skill_id)
            if not skill:
                return {
                    'success': False,
                    'error': f"Skill not found: {skill_id}",
                    'execution_time': 0.0
                }
            
            if skill.status != SkillStatus.ACTIVE:
                return {
                    'success': False,
                    'error': f"Skill is not active: {skill.status.value}",
                    'execution_time': 0.0
                }
            
            # 验证参数
            parameters = parameters or {}
            validation_result = self._validate_parameters(skill.parameters, parameters)
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': f"Parameter validation failed: {validation_result['errors']}",
                    'execution_time': 0.0
                }
            
            # 记录执行开始
            execution_id = self._record_execution_start(
                skill_id, parameters, initiated_by, start_time
            )
            
            # 加载并执行技能处理器
            result = self._execute_skill_handler(skill, parameters)
            
            # 计算执行时间
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # 记录执行结果
            self._record_execution_result(
                execution_id, 'success', result, end_time, execution_time
            )
            
            # 更新技能统计
            self._update_skill_stats(skill_id, execution_time, True)
            
            return {
                'success': True,
                'result': result,
                'execution_time': execution_time,
                'execution_id': execution_id
            }
            
        except Exception as e:
            # 记录执行失败
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            if execution_id:
                self._record_execution_result(
                    execution_id, 'failed', None, end_time, execution_time, str(e)
                )
            
            if skill_id:
                self._update_skill_stats(skill_id, execution_time, False)
            
            self.logger.error(f"Skill execution failed: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': execution_time,
                'execution_id': execution_id
            }
    
    def list_skills(self, category: SkillCategory = None, 
                   status: SkillStatus = None) -> List[RegisteredSkill]:
        """
        列出技能
        
        Args:
            category: 技能分类过滤
            status: 技能状态过滤
            
        Returns:
            List[RegisteredSkill]: 技能列表
        """
        try:
            where_conditions = []
            params = []
            
            if category:
                where_conditions.append("category = %s")
                params.append(category.value)
            
            if status:
                where_conditions.append("status = %s")
                params.append(status.value)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            query = f"SELECT * FROM {self.skills_table} WHERE {where_clause} ORDER BY name"
            
            results = self.db.execute_query(query, tuple(params))
            
            skills = []
            for row in results:
                skill = RegisteredSkill(
                    skill_id=row['skill_id'],
                    name=row['name'],
                    description=row['description'],
                    category=SkillCategory(row['category']),
                    status=SkillStatus(row['status']),
                    parameters=[SkillParameter(**param) for param in json.loads(row['parameters'])],
                    metadata=SkillMetadata(**json.loads(row['metadata'])),
                    handler_module=row['handler_module'],
                    handler_function=row['handler_function'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    execution_count=row['execution_count'],
                    success_count=row['success_count'],
                    average_execution_time=row['average_execution_time']
                )
                skills.append(skill)
            
            return skills
            
        except Exception as e:
            self.logger.error(f"Failed to list skills: {str(e)}")
            return []
    
    def update_skill_status(self, skill_id: str, status: SkillStatus) -> bool:
        """
        更新技能状态
        
        Args:
            skill_id: 技能ID
            status: 新状态
            
        Returns:
            bool: 更新是否成功
        """
        try:
            update_data = {
                'status': status.value,
                'updated_at': datetime.now()
            }
            
            affected = self.db.execute_update(
                self.skills_table,
                update_data,
                "skill_id = %s",
                (skill_id,)
            )
            
            if affected > 0:
                # 更新缓存
                if skill_id in self._skills_cache:
                    self._skills_cache[skill_id].status = status
                    self._skills_cache[skill_id].updated_at = datetime.now()
                
                self.logger.info(f"Skill status updated: {skill_id} -> {status.value}")
                return True
            else:
                self.logger.warning(f"Skill not found: {skill_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update skill status: {str(e)}")
            return False
    
    def get_skill_executions(self, skill_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取技能执行记录
        
        Args:
            skill_id: 技能ID（可选）
            limit: 返回记录限制
            
        Returns:
            List[Dict]: 执行记录列表
        """
        try:
            if skill_id:
                query = f"""
                SELECT * FROM {self.skill_executions_table} 
                WHERE skill_id = %s 
                ORDER BY start_time DESC 
                LIMIT %s
                """
                params = (skill_id, limit)
            else:
                query = f"""
                SELECT * FROM {self.skill_executions_table} 
                ORDER BY start_time DESC 
                LIMIT %s
                """
                params = (limit,)
            
            results = self.db.execute_query(query, params)
            
            executions = []
            for row in results:
                execution = {
                    'execution_id': row['execution_id'],
                    'skill_id': row['skill_id'],
                    'parameters': json.loads(row['parameters']) if row['parameters'] else {},
                    'result': json.loads(row['result']) if row['result'] else {},
                    'status': row['status'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'execution_time': row['execution_time'],
                    'error_message': row['error_message'],
                    'initiated_by': row['initiated_by']
                }
                executions.append(execution)
            
            return executions
            
        except Exception as e:
            self.logger.error(f"Failed to get skill executions: {str(e)}")
            return []
    
    def get_skill_statistics(self, skill_id: str) -> Dict[str, Any]:
        """
        获取技能统计信息
        
        Args:
            skill_id: 技能ID
            
        Returns:
            Dict: 技能统计信息
        """
        try:
            skill = self.get_skill(skill_id)
            if not skill:
                return {'error': 'Skill not found'}
            
            # 获取最近执行记录
            recent_executions = self.get_skill_executions(skill_id, limit=50)
            
            stats = {
                'skill_id': skill_id,
                'total_executions': skill.execution_count,
                'success_rate': 0.0,
                'average_execution_time': skill.average_execution_time,
                'recent_success_count': 0,
                'recent_failure_count': 0,
                'execution_trend': []
            }
            
            # 计算成功率
            if skill.execution_count > 0:
                stats['success_rate'] = (skill.success_count / skill.execution_count) * 100
            
            # 分析最近执行
            for execution in recent_executions:
                if execution['status'] == 'success':
                    stats['recent_success_count'] += 1
                else:
                    stats['recent_failure_count'] += 1
            
            # 计算执行趋势（简化）
            if len(recent_executions) >= 2:
                first_time = recent_executions[-1]['start_time']
                last_time = recent_executions[0]['start_time']
                time_span = (last_time - first_time).total_seconds()
                
                if time_span > 0:
                    stats['execution_frequency'] = len(recent_executions) / (time_span / 3600)  # 执行/小时
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get skill statistics: {str(e)}")
            return {'error': str(e)}
    
    def search_skills(self, query: str, category: SkillCategory = None) -> List[RegisteredSkill]:
        """
        搜索技能
        
        Args:
            query: 搜索查询
            category: 技能分类过滤
            
        Returns:
            List[RegisteredSkill]: 匹配的技能列表
        """
        try:
            where_conditions = ["(name ILIKE %s OR description ILIKE %s)"]
            params = [f"%{query}%", f"%{query}%"]
            
            if category:
                where_conditions.append("category = %s")
                params.append(category.value)
            
            where_clause = " AND ".join(where_conditions)
            sql = f"SELECT * FROM {self.skills_table} WHERE {where_clause} ORDER BY name"
            
            results = self.db.execute_query(sql, tuple(params))
            
            skills = []
            for row in results:
                skill = RegisteredSkill(
                    skill_id=row['skill_id'],
                    name=row['name'],
                    description=row['description'],
                    category=SkillCategory(row['category']),
                    status=SkillStatus(row['status']),
                    parameters=[SkillParameter(**param) for param in json.loads(row['parameters'])],
                    metadata=SkillMetadata(**json.loads(row['metadata'])),
                    handler_module=row['handler_module'],
                    handler_function=row['handler_function'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    execution_count=row['execution_count'],
                    success_count=row['success_count'],
                    average_execution_time=row['average_execution_time']
                )
                skills.append(skill)
            
            return skills
            
        except Exception as e:
            self.logger.error(f"Failed to search skills: {str(e)}")
            return []
    
    def _validate_skill_data(self, skill_data: Dict[str, Any]) -> bool:
        """验证技能数据"""
        required_fields = [
            'skill_id', 'name', 'category', 'parameters', 
            'metadata', 'handler_module', 'handler_function'
        ]
        
        for field in required_fields:
            if field not in skill_data:
                self.logger.error(f"Missing required field: {field}")
                return False
        
        # 验证处理器模块和函数是否存在
        try:
            module = importlib.import_module(skill_data['handler_module'])
            if not hasattr(module, skill_data['handler_function']):
                self.logger.error(f"Handler function not found: {skill_data['handler_function']}")
                return False
        except ImportError:
            self.logger.error(f"Handler module not found: {skill_data['handler_module']}")
            return False
        
        return True
    
    def _validate_parameters(self, expected_params: List[SkillParameter], 
                           provided_params: Dict[str, Any]) -> Dict[str, Any]:
        """验证参数"""
        validation_result = {
            'is_valid': True,
            'errors': []
        }
        
        for param in expected_params:
            if param.required and param.name not in provided_params:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Required parameter missing: {param.name}")
        
        return validation_result
    
    def _execute_skill_handler(self, skill: RegisteredSkill, parameters: Dict[str, Any]) -> Any:
        """执行技能处理器"""
        try:
            module = importlib.import_module(skill.handler_module)
            handler_function = getattr(module, skill.handler_function)
            
            # 调用处理器函数
            return handler_function(**parameters)
            
        except Exception as e:
            self.logger.error(f"Skill handler execution failed: {str(e)}")
            raise
    
    def _record_execution_start(self, skill_id: str, parameters: Dict[str, Any],
                              initiated_by: str, start_time: datetime) -> int:
        """记录执行开始"""
        execution_data = {
            'skill_id': skill_id,
            'parameters': json.dumps(parameters),
            'status': 'running',
            'start_time': start_time,
            'initiated_by': initiated_by
        }
        
        return self.db.execute_insert(self.skill_executions_table, execution_data)
    
    def _record_execution_result(self, execution_id: int, status: str, result: Any,
                               end_time: datetime, execution_time: float,
                               error_message: str = None):
        """记录执行结果"""
        update_data = {
            'status': status,
            'result': json.dumps(result) if result else None,
            'end_time': end_time,
            'execution_time': execution_time,
            'error_message': error_message
        }
        
        self.db.execute_update(
            self.skill_executions_table,
            update_data,
            "execution_id = %s",
            (execution_id,)
        )
    
    def _update_skill_stats(self, skill_id: str, execution_time: float, success: bool):
        """更新技能统计"""
        skill = self.get_skill(skill_id)
        if not skill:
            return
        
        # 计算新的平均值
        total_time = skill.average_execution_time * skill.execution_count + execution_time
        new_execution_count = skill.execution_count + 1
        new_average_time = total_time / new_execution_count
        
        # 更新成功计数
        new_success_count = skill.success_count + (1 if success else 0)
        
        update_data = {
            'execution_count': new_execution_count,
            'success_count': new_success_count,
            'average_execution_time': new_average_time,
            'updated_at': datetime.now()
        }
        
        self.db.execute_update(
            self.skills_table,
            update_data,
            "skill_id = %s",
            (skill_id,)
        )
        
        # 更新缓存
        if skill_id in self._skills_cache:
            self._skills_cache[skill_id].execution_count = new_execution_count
            self._skills_cache[skill_id].success_count = new_success_count
            self._skills_cache[skill_id].average_execution_time = new_average_time
            self._skills_cache[skill_id].updated_at = datetime.now()

