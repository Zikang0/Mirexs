"""
学习数据管理模块 - 管理用户学习进度、知识掌握和技能发展数据
"""

import logging
import json
import uuid
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import numpy as np
from scipy import stats
import pandas as pd

logger = logging.getLogger(__name__)

class LearningDomain(Enum):
    """学习领域枚举"""
    TECHNOLOGY = "technology"
    SCIENCE = "science"
    ARTS = "arts"
    BUSINESS = "business"
    LANGUAGES = "languages"
    PERSONAL_DEVELOPMENT = "personal_development"
    PROFESSIONAL_SKILLS = "professional_skills"
    CREATIVE_ARTS = "creative_arts"

class ProficiencyLevel(Enum):
    """熟练程度枚举"""
    BEGINNER = "beginner"  # 0-30%
    INTERMEDIATE = "intermediate"  # 30-70%
    ADVANCED = "advanced"  # 70-90%
    EXPERT = "expert"  # 90-100%

class LearningStyle(Enum):
    """学习风格枚举"""
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"
    READING_WRITING = "reading_writing"

@dataclass
class KnowledgeComponent:
    """知识组件数据类"""
    component_id: str
    name: str
    description: str
    domain: LearningDomain
    prerequisites: List[str]  # 先决条件组件ID列表
    difficulty_level: int  # 1-10
    estimated_study_time: int  # 分钟
    tags: List[str]
    learning_objectives: List[str]
    assessment_criteria: Dict[str, Any]

@dataclass
class LearningProgress:
    """学习进度数据类"""
    component_id: str
    user_id: str
    start_time: datetime
    last_studied: datetime
    study_duration: int  # 总学习时长（分钟）
    completion_percentage: float  # 0-100
    confidence_score: float  # 0-1
    mastery_level: ProficiencyLevel
    quiz_scores: List[float]  # 历史测验分数
    practice_attempts: int
    successful_attempts: int
    learning_velocity: float  # 学习速度指标
    retention_score: float  # 记忆保持分数
    next_review_date: datetime
    metadata: Dict[str, Any]

@dataclass
class LearningSession:
    """学习会话数据类"""
    session_id: str
    user_id: str
    component_ids: List[str]
    start_time: datetime
    end_time: datetime
    duration: int  # 分钟
    focus_score: float  # 0-1
    comprehension_score: float  # 0-1
    resources_used: List[str]
    interaction_log: List[Dict[str, Any]]
    achievements: List[str]
    challenges_faced: List[str]
    session_rating: int  # 1-5
    notes: str
    metadata: Dict[str, Any]

@dataclass
class LearningPath:
    """学习路径数据类"""
    path_id: str
    user_id: str
    name: str
    description: str
    domain: LearningDomain
    target_proficiency: ProficiencyLevel
    components: List[str]  # 知识组件ID列表
    estimated_total_time: int  # 分钟
    current_progress: float  # 0-100
    start_date: datetime
    target_completion_date: datetime
    priority: int  # 1-10
    adaptive_adjustments: Dict[str, Any]
    milestones: List[Dict[str, Any]]
    metadata: Dict[str, Any]

@dataclass
class SkillAssessment:
    """技能评估数据类"""
    assessment_id: str
    user_id: str
    skill_name: str
    domain: LearningDomain
    assessment_date: datetime
    theoretical_score: float  # 0-100
    practical_score: float  # 0-100
    confidence_level: float  # 0-1
    evaluator: str  # 'system' 或 'user'
    assessment_method: str
    feedback: str
    improvement_suggestions: List[str]
    next_assessment_date: datetime
    metadata: Dict[str, Any]

class LearningDataManager:
    """学习数据管理器"""
    
    def __init__(self, db_integration, cognitive_engine, config: Dict[str, Any]):
        """
        初始化学习数据管理器
        
        Args:
            db_integration: 数据库集成实例
            cognitive_engine: 认知引擎实例（用于个性化推荐）
            config: 配置字典
        """
        self.db = db_integration
        self.cognitive_engine = cognitive_engine
        self.config = config
        self.logger = logger
        
        # 表名配置
        self.knowledge_components_table = config.get('knowledge_components_table', 'knowledge_components')
        self.learning_progress_table = config.get('learning_progress_table', 'learning_progress')
        self.learning_sessions_table = config.get('learning_sessions_table', 'learning_sessions')
        self.learning_paths_table = config.get('learning_paths_table', 'learning_paths')
        self.skill_assessments_table = config.get('skill_assessments_table', 'skill_assessments')
        
        # 学习参数配置
        self.mastery_threshold = config.get('mastery_threshold', 0.8)  # 掌握阈值
        self.retention_decay_rate = config.get('retention_decay_rate', 0.1)  # 记忆衰减率
        self.min_review_interval = config.get('min_review_interval', 24)  # 最小复习间隔（小时）
        
        # 初始化表结构
        self._initialize_tables()
    
    def _initialize_tables(self):
        """初始化学习数据相关表"""
        try:
            # 知识组件表
            components_schema = {
                'component_id': 'VARCHAR(100) PRIMARY KEY',
                'name': 'VARCHAR(200) NOT NULL',
                'description': 'TEXT NOT NULL',
                'domain': 'VARCHAR(50) NOT NULL',
                'prerequisites': 'TEXT NOT NULL',  # JSON格式
                'difficulty_level': 'INTEGER NOT NULL',
                'estimated_study_time': 'INTEGER NOT NULL',
                'tags': 'TEXT NOT NULL',  # JSON格式
                'learning_objectives': 'TEXT NOT NULL',  # JSON格式
                'assessment_criteria': 'TEXT NOT NULL'  # JSON格式
            }
            
            self.db.create_table(self.knowledge_components_table, components_schema)
            
            # 学习进度表
            progress_schema = {
                'progress_id': 'SERIAL PRIMARY KEY',
                'component_id': 'VARCHAR(100) NOT NULL',
                'user_id': 'VARCHAR(100) NOT NULL',
                'start_time': 'TIMESTAMP NOT NULL',
                'last_studied': 'TIMESTAMP NOT NULL',
                'study_duration': 'INTEGER DEFAULT 0',
                'completion_percentage': 'FLOAT DEFAULT 0.0',
                'confidence_score': 'FLOAT DEFAULT 0.0',
                'mastery_level': 'VARCHAR(20) DEFAULT "beginner"',
                'quiz_scores': 'TEXT NOT NULL',  # JSON格式
                'practice_attempts': 'INTEGER DEFAULT 0',
                'successful_attempts': 'INTEGER DEFAULT 0',
                'learning_velocity': 'FLOAT DEFAULT 0.0',
                'retention_score': 'FLOAT DEFAULT 1.0',
                'next_review_date': 'TIMESTAMP',
                'metadata': 'TEXT'  # JSON格式
            }
            
            constraints = [
                'FOREIGN KEY (component_id) REFERENCES knowledge_components(component_id) ON DELETE CASCADE',
                'UNIQUE (component_id, user_id)'
            ]
            
            self.db.create_table(self.learning_progress_table, progress_schema, constraints)
            
            # 学习会话表
            sessions_schema = {
                'session_id': 'VARCHAR(100) PRIMARY KEY',
                'user_id': 'VARCHAR(100) NOT NULL',
                'component_ids': 'TEXT NOT NULL',  # JSON格式
                'start_time': 'TIMESTAMP NOT NULL',
                'end_time': 'TIMESTAMP NOT NULL',
                'duration': 'INTEGER NOT NULL',
                'focus_score': 'FLOAT DEFAULT 0.0',
                'comprehension_score': 'FLOAT DEFAULT 0.0',
                'resources_used': 'TEXT NOT NULL',  # JSON格式
                'interaction_log': 'TEXT NOT NULL',  # JSON格式
                'achievements': 'TEXT NOT NULL',  # JSON格式
                'challenges_faced': 'TEXT NOT NULL',  # JSON格式
                'session_rating': 'INTEGER DEFAULT 3',
                'notes': 'TEXT',
                'metadata': 'TEXT'  # JSON格式
            }
            
            self.db.create_table(self.learning_sessions_table, sessions_schema)
            
            # 学习路径表
            paths_schema = {
                'path_id': 'VARCHAR(100) PRIMARY KEY',
                'user_id': 'VARCHAR(100) NOT NULL',
                'name': 'VARCHAR(200) NOT NULL',
                'description': 'TEXT NOT NULL',
                'domain': 'VARCHAR(50) NOT NULL',
                'target_proficiency': 'VARCHAR(20) NOT NULL',
                'components': 'TEXT NOT NULL',  # JSON格式
                'estimated_total_time': 'INTEGER NOT NULL',
                'current_progress': 'FLOAT DEFAULT 0.0',
                'start_date': 'TIMESTAMP NOT NULL',
                'target_completion_date': 'TIMESTAMP',
                'priority': 'INTEGER DEFAULT 5',
                'adaptive_adjustments': 'TEXT NOT NULL',  # JSON格式
                'milestones': 'TEXT NOT NULL',  # JSON格式
                'metadata': 'TEXT'  # JSON格式
            }
            
            self.db.create_table(self.learning_paths_table, paths_schema)
            
            # 技能评估表
            assessments_schema = {
                'assessment_id': 'VARCHAR(100) PRIMARY KEY',
                'user_id': 'VARCHAR(100) NOT NULL',
                'skill_name': 'VARCHAR(200) NOT NULL',
                'domain': 'VARCHAR(50) NOT NULL',
                'assessment_date': 'TIMESTAMP NOT NULL',
                'theoretical_score': 'FLOAT DEFAULT 0.0',
                'practical_score': 'FLOAT DEFAULT 0.0',
                'confidence_level': 'FLOAT DEFAULT 0.0',
                'evaluator': 'VARCHAR(20) NOT NULL',
                'assessment_method': 'VARCHAR(100) NOT NULL',
                'feedback': 'TEXT',
                'improvement_suggestions': 'TEXT NOT NULL',  # JSON格式
                'next_assessment_date': 'TIMESTAMP',
                'metadata': 'TEXT'  # JSON格式
            }
            
            self.db.create_table(self.skill_assessments_table, assessments_schema)
            
            # 创建索引
            self.db.create_index(self.knowledge_components_table, 'domain')
            self.db.create_index(self.knowledge_components_table, 'difficulty_level')
            self.db.create_index(self.learning_progress_table, 'user_id')
            self.db.create_index(self.learning_progress_table, 'component_id')
            self.db.create_index(self.learning_progress_table, 'mastery_level')
            self.db.create_index(self.learning_sessions_table, 'user_id')
            self.db.create_index(self.learning_sessions_table, 'start_time')
            self.db.create_index(self.learning_paths_table, 'user_id')
            self.db.create_index(self.learning_paths_table, 'domain')
            self.db.create_index(self.skill_assessments_table, 'user_id')
            self.db.create_index(self.skill_assessments_table, 'skill_name')
            self.db.create_index(self.skill_assessments_table, 'assessment_date')
            
            self.logger.info("Learning data tables initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize learning data tables: {str(e)}")
            raise
    
    def create_knowledge_component(self, component_data: Dict[str, Any]) -> str:
        """
        创建知识组件
        
        Args:
            component_data: 组件数据
            
        Returns:
            str: 组件ID
        """
        try:
            component_id = component_data.get('component_id') or str(uuid.uuid4())
            
            component = KnowledgeComponent(
                component_id=component_id,
                name=component_data['name'],
                description=component_data['description'],
                domain=LearningDomain(component_data['domain']),
                prerequisites=component_data.get('prerequisites', []),
                difficulty_level=component_data['difficulty_level'],
                estimated_study_time=component_data['estimated_study_time'],
                tags=component_data.get('tags', []),
                learning_objectives=component_data.get('learning_objectives', []),
                assessment_criteria=component_data.get('assessment_criteria', {})
            )
            
            # 准备数据库数据
            db_data = {
                'component_id': component.component_id,
                'name': component.name,
                'description': component.description,
                'domain': component.domain.value,
                'prerequisites': json.dumps(component.prerequisites),
                'difficulty_level': component.difficulty_level,
                'estimated_study_time': component.estimated_study_time,
                'tags': json.dumps(component.tags),
                'learning_objectives': json.dumps(component.learning_objectives),
                'assessment_criteria': json.dumps(component.assessment_criteria)
            }
            
            # 插入数据库
            self.db.execute_insert(self.knowledge_components_table, db_data)
            
            self.logger.info(f"Knowledge component created: {component_id} - {component.name}")
            return component_id
            
        except Exception as e:
            self.logger.error(f"Failed to create knowledge component: {str(e)}")
            raise
    
    def get_knowledge_component(self, component_id: str) -> Optional[KnowledgeComponent]:
        """
        获取知识组件
        
        Args:
            component_id: 组件ID
            
        Returns:
            KnowledgeComponent: 知识组件，如果不存在返回None
        """
        try:
            query = f"SELECT * FROM {self.knowledge_components_table} WHERE component_id = %s"
            results = self.db.execute_query(query, (component_id,))
            
            if not results:
                return None
            
            comp_data = results[0]
            
            return KnowledgeComponent(
                component_id=comp_data['component_id'],
                name=comp_data['name'],
                description=comp_data['description'],
                domain=LearningDomain(comp_data['domain']),
                prerequisites=json.loads(comp_data['prerequisites']),
                difficulty_level=comp_data['difficulty_level'],
                estimated_study_time=comp_data['estimated_study_time'],
                tags=json.loads(comp_data['tags']),
                learning_objectives=json.loads(comp_data['learning_objectives']),
                assessment_criteria=json.loads(comp_data['assessment_criteria'])
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get knowledge component: {str(e)}")
            return None
    
    def initialize_learning_progress(self, user_id: str, component_id: str) -> bool:
        """
        初始化学习进度
        
        Args:
            user_id: 用户ID
            component_id: 组件ID
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 检查是否已存在进度记录
            query = f"""
            SELECT COUNT(*) as count FROM {self.learning_progress_table} 
            WHERE user_id = %s AND component_id = %s
            """
            results = self.db.execute_query(query, (user_id, component_id))
            
            if results and results[0]['count'] > 0:
                self.logger.debug(f"Learning progress already exists for user {user_id}, component {component_id}")
                return True
            
            current_time = datetime.now()
            
            # 创建初始进度记录
            progress_data = {
                'component_id': component_id,
                'user_id': user_id,
                'start_time': current_time,
                'last_studied': current_time,
                'study_duration': 0,
                'completion_percentage': 0.0,
                'confidence_score': 0.0,
                'mastery_level': ProficiencyLevel.BEGINNER.value,
                'quiz_scores': json.dumps([]),
                'practice_attempts': 0,
                'successful_attempts': 0,
                'learning_velocity': 0.0,
                'retention_score': 1.0,
                'next_review_date': current_time + timedelta(hours=self.min_review_interval),
                'metadata': json.dumps({'initialized_at': current_time.isoformat()})
            }
            
            self.db.execute_insert(self.learning_progress_table, progress_data)
            
            self.logger.debug(f"Learning progress initialized: user {user_id}, component {component_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize learning progress: {str(e)}")
            return False
    
    def update_learning_progress(self, user_id: str, component_id: str, 
                               study_duration: int, quiz_score: float = None,
                               practice_success: bool = None) -> bool:
        """
        更新学习进度
        
        Args:
            user_id: 用户ID
            component_id: 组件ID
            study_duration: 学习时长（分钟）
            quiz_score: 测验分数（0-100）
            practice_success: 练习是否成功
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 获取当前进度
            progress = self.get_learning_progress(user_id, component_id)
            if not progress:
                # 如果进度不存在，先初始化
                if not self.initialize_learning_progress(user_id, component_id):
                    return False
                progress = self.get_learning_progress(user_id, component_id)
            
            current_time = datetime.now()
            time_since_last_study = (current_time - progress.last_studied).total_seconds() / 3600  # 小时
            
            # 更新基本数据
            progress.study_duration += study_duration
            progress.last_studied = current_time
            
            # 更新测验分数
            if quiz_score is not None:
                progress.quiz_scores.append(quiz_score)
                # 保留最近10次测验分数
                if len(progress.quiz_scores) > 10:
                    progress.quiz_scores = progress.quiz_scores[-10:]
            
            # 更新练习记录
            if practice_success is not None:
                progress.practice_attempts += 1
                if practice_success:
                    progress.successful_attempts += 1
            
            # 计算完成度百分比
            component = self.get_knowledge_component(component_id)
            if component:
                # 基于学习时长和测验分数的完成度计算
                time_completion = min(1.0, progress.study_duration / component.estimated_study_time)
                quiz_completion = np.mean(progress.quiz_scores) / 100.0 if progress.quiz_scores else 0.0
                practice_completion = progress.successful_attempts / max(1, progress.practice_attempts)
                
                # 加权计算总体完成度
                progress.completion_percentage = (
                    0.4 * time_completion + 
                    0.4 * quiz_completion + 
                    0.2 * practice_completion
                ) * 100
            
            # 计算置信度分数
            progress.confidence_score = self._calculate_confidence_score(progress)
            
            # 更新熟练程度
            progress.mastery_level = self._determine_mastery_level(progress.completion_percentage, progress.confidence_score)
            
            # 计算学习速度
            progress.learning_velocity = self._calculate_learning_velocity(progress, study_duration, time_since_last_study)
            
            # 更新记忆保持分数
            progress.retention_score = self._calculate_retention_score(progress, time_since_last_study)
            
            # 计算下次复习时间
            progress.next_review_date = self._calculate_next_review_date(progress)
            
            # 更新数据库
            update_data = {
                'last_studied': progress.last_studied,
                'study_duration': progress.study_duration,
                'completion_percentage': progress.completion_percentage,
                'confidence_score': progress.confidence_score,
                'mastery_level': progress.mastery_level.value,
                'quiz_scores': json.dumps(progress.quiz_scores),
                'practice_attempts': progress.practice_attempts,
                'successful_attempts': progress.successful_attempts,
                'learning_velocity': progress.learning_velocity,
                'retention_score': progress.retention_score,
                'next_review_date': progress.next_review_date
            }
            
            affected = self.db.execute_update(
                self.learning_progress_table,
                update_data,
                "user_id = %s AND component_id = %s",
                (user_id, component_id)
            )
            
            if affected > 0:
                self.logger.debug(f"Learning progress updated: user {user_id}, component {component_id}")
                return True
            else:
                self.logger.warning(f"Learning progress not found for update: user {user_id}, component {component_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update learning progress: {str(e)}")
            return False
    
    def get_learning_progress(self, user_id: str, component_id: str) -> Optional[LearningProgress]:
        """
        获取学习进度
        
        Args:
            user_id: 用户ID
            component_id: 组件ID
            
        Returns:
            LearningProgress: 学习进度，如果不存在返回None
        """
        try:
            query = f"""
            SELECT * FROM {self.learning_progress_table} 
            WHERE user_id = %s AND component_id = %s
            """
            results = self.db.execute_query(query, (user_id, component_id))
            
            if not results:
                return None
            
            prog_data = results[0]
            
            return LearningProgress(
                component_id=prog_data['component_id'],
                user_id=prog_data['user_id'],
                start_time=prog_data['start_time'],
                last_studied=prog_data['last_studied'],
                study_duration=prog_data['study_duration'],
                completion_percentage=prog_data['completion_percentage'],
                confidence_score=prog_data['confidence_score'],
                mastery_level=ProficiencyLevel(prog_data['mastery_level']),
                quiz_scores=json.loads(prog_data['quiz_scores']),
                practice_attempts=prog_data['practice_attempts'],
                successful_attempts=prog_data['successful_attempts'],
                learning_velocity=prog_data['learning_velocity'],
                retention_score=prog_data['retention_score'],
                next_review_date=prog_data['next_review_date'],
                metadata=json.loads(prog_data['metadata']) if prog_data['metadata'] else {}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get learning progress: {str(e)}")
            return None
    
    def record_learning_session(self, user_id: str, component_ids: List[str],
                              start_time: datetime, end_time: datetime,
                              focus_score: float, comprehension_score: float,
                              resources_used: List[str], interaction_log: List[Dict[str, Any]],
                              achievements: List[str] = None, challenges_faced: List[str] = None,
                              session_rating: int = 3, notes: str = "") -> str:
        """
        记录学习会话
        
        Args:
            user_id: 用户ID
            component_ids: 学习的组件ID列表
            start_time: 开始时间
            end_time: 结束时间
            focus_score: 专注度分数（0-1）
            comprehension_score: 理解度分数（0-1）
            resources_used: 使用的资源列表
            interaction_log: 交互日志
            achievements: 取得的成就
            challenges_faced: 遇到的挑战
            session_rating: 会话评分（1-5）
            notes: 备注
            
        Returns:
            str: 会话ID
        """
        try:
            session_id = str(uuid.uuid4())
            duration = int((end_time - start_time).total_seconds() / 60)  # 转换为分钟
            
            session = LearningSession(
                session_id=session_id,
                user_id=user_id,
                component_ids=component_ids,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                focus_score=focus_score,
                comprehension_score=comprehension_score,
                resources_used=resources_used,
                interaction_log=interaction_log,
                achievements=achievements or [],
                challenges_faced=challenges_faced or [],
                session_rating=session_rating,
                notes=notes,
                metadata={'recorded_at': datetime.now().isoformat()}
            )
            
            # 准备数据库数据
            db_data = {
                'session_id': session.session_id,
                'user_id': session.user_id,
                'component_ids': json.dumps(session.component_ids),
                'start_time': session.start_time,
                'end_time': session.end_time,
                'duration': session.duration,
                'focus_score': session.focus_score,
                'comprehension_score': session.comprehension_score,
                'resources_used': json.dumps(session.resources_used),
                'interaction_log': json.dumps(session.interaction_log),
                'achievements': json.dumps(session.achievements),
                'challenges_faced': json.dumps(session.challenges_faced),
                'session_rating': session.session_rating,
                'notes': session.notes,
                'metadata': json.dumps(session.metadata)
            }
            
            # 插入数据库
            self.db.execute_insert(self.learning_sessions_table, db_data)
            
            # 更新相关组件的学习进度
            for component_id in component_ids:
                self.update_learning_progress(
                    user_id=user_id,
                    component_id=component_id,
                    study_duration=duration
                )
            
            self.logger.info(f"Learning session recorded: {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to record learning session: {str(e)}")
            raise
    
    def create_learning_path(self, user_id: str, name: str, description: str,
                           domain: LearningDomain, target_proficiency: ProficiencyLevel,
                           components: List[str], estimated_total_time: int,
                           target_completion_date: datetime = None, priority: int = 5) -> str:
        """
        创建学习路径
        
        Args:
            user_id: 用户ID
            name: 路径名称
            description: 路径描述
            domain: 学习领域
            target_proficiency: 目标熟练程度
            components: 组件ID列表
            estimated_total_time: 预计总学习时长（分钟）
            target_completion_date: 目标完成日期
            priority: 优先级（1-10）
            
        Returns:
            str: 路径ID
        """
        try:
            path_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            if not target_completion_date:
                # 默认3个月后
                target_completion_date = current_time + timedelta(days=90)
            
            # 创建里程碑
            milestones = self._generate_learning_milestones(components, estimated_total_time)
            
            path = LearningPath(
                path_id=path_id,
                user_id=user_id,
                name=name,
                description=description,
                domain=domain,
                target_proficiency=target_proficiency,
                components=components,
                estimated_total_time=estimated_total_time,
                current_progress=0.0,
                start_date=current_time,
                target_completion_date=target_completion_date,
                priority=priority,
                adaptive_adjustments={},
                milestones=milestones,
                metadata={'created_at': current_time.isoformat()}
            )
            
            # 准备数据库数据
            db_data = {
                'path_id': path.path_id,
                'user_id': path.user_id,
                'name': path.name,
                'description': path.description,
                'domain': path.domain.value,
                'target_proficiency': path.target_proficiency.value,
                'components': json.dumps(path.components),
                'estimated_total_time': path.estimated_total_time,
                'current_progress': path.current_progress,
                'start_date': path.start_date,
                'target_completion_date': path.target_completion_date,
                'priority': path.priority,
                'adaptive_adjustments': json.dumps(path.adaptive_adjustments),
                'milestones': json.dumps(path.milestones),
                'metadata': json.dumps(path.metadata)
            }
            
            # 插入数据库
            self.db.execute_insert(self.learning_paths_table, db_data)
            
            # 初始化所有组件的学习进度
            for component_id in components:
                self.initialize_learning_progress(user_id, component_id)
            
            self.logger.info(f"Learning path created: {path_id} - {name}")
            return path_id
            
        except Exception as e:
            self.logger.error(f"Failed to create learning path: {str(e)}")
            raise
    
    def record_skill_assessment(self, user_id: str, skill_name: str, domain: LearningDomain,
                              theoretical_score: float, practical_score: float,
                              confidence_level: float, evaluator: str, assessment_method: str,
                              feedback: str = "", improvement_suggestions: List[str] = None) -> str:
        """
        记录技能评估
        
        Args:
            user_id: 用户ID
            skill_name: 技能名称
            domain: 技能领域
            theoretical_score: 理论分数（0-100）
            practical_score: 实践分数（0-100）
            confidence_level: 置信度（0-1）
            evaluator: 评估者
            assessment_method: 评估方法
            feedback: 反馈意见
            improvement_suggestions: 改进建议
            
        Returns:
            str: 评估ID
        """
        try:
            assessment_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            # 计算下次评估日期（基于当前熟练程度）
            overall_score = (theoretical_score + practical_score) / 2
            if overall_score >= 80:
                next_assessment_days = 90  # 熟练程度高，3个月后评估
            elif overall_score >= 60:
                next_assessment_days = 60  # 中等熟练，2个月后评估
            else:
                next_assessment_days = 30  # 需要改进，1个月后评估
            
            next_assessment_date = current_time + timedelta(days=next_assessment_days)
            
            assessment = SkillAssessment(
                assessment_id=assessment_id,
                user_id=user_id,
                skill_name=skill_name,
                domain=domain,
                assessment_date=current_time,
                theoretical_score=theoretical_score,
                practical_score=practical_score,
                confidence_level=confidence_level,
                evaluator=evaluator,
                assessment_method=assessment_method,
                feedback=feedback,
                improvement_suggestions=improvement_suggestions or [],
                next_assessment_date=next_assessment_date,
                metadata={'recorded_at': current_time.isoformat()}
            )
            
            # 准备数据库数据
            db_data = {
                'assessment_id': assessment.assessment_id,
                'user_id': assessment.user_id,
                'skill_name': assessment.skill_name,
                'domain': assessment.domain.value,
                'assessment_date': assessment.assessment_date,
                'theoretical_score': assessment.theoretical_score,
                'practical_score': assessment.practical_score,
                'confidence_level': assessment.confidence_level,
                'evaluator': assessment.evaluator,
                'assessment_method': assessment.assessment_method,
                'feedback': assessment.feedback,
                'improvement_suggestions': json.dumps(assessment.improvement_suggestions),
                'next_assessment_date': assessment.next_assessment_date,
                'metadata': json.dumps(assessment.metadata)
            }
            
            # 插入数据库
            self.db.execute_insert(self.skill_assessments_table, db_data)
            
            self.logger.info(f"Skill assessment recorded: {assessment_id} for user {user_id}")
            return assessment_id
            
        except Exception as e:
            self.logger.error(f"Failed to record skill assessment: {str(e)}")
            raise
    
    def get_learning_recommendations(self, user_id: str, max_recommendations: int = 5) -> List[Dict[str, Any]]:
        """
        获取学习推荐
        
        Args:
            user_id: 用户ID
            max_recommendations: 最大推荐数量
            
        Returns:
            List[Dict]: 推荐列表
        """
        try:
            recommendations = []
            
            # 获取用户的学习进度
            query = f"""
            SELECT lp.*, kc.name, kc.difficulty_level, kc.domain
            FROM {self.learning_progress_table} lp
            JOIN {self.knowledge_components_table} kc ON lp.component_id = kc.component_id
            WHERE lp.user_id = %s
            """
            progress_results = self.db.execute_query(query, (user_id,))
            
            if not progress_results:
                # 如果没有学习记录，推荐入门级组件
                return self._get_beginner_recommendations(user_id, max_recommendations)
            
            # 分析学习模式
            learning_patterns = self._analyze_learning_patterns(user_id, progress_results)
            
            # 基于遗忘曲线的复习推荐
            review_recommendations = self._get_review_recommendations(user_id, progress_results)
            recommendations.extend(review_recommendations)
            
            # 基于学习路径的下一步推荐
            path_recommendations = self._get_path_based_recommendations(user_id)
            recommendations.extend(path_recommendations)
            
            # 基于相似用户的学习推荐
            collaborative_recommendations = self._get_collaborative_recommendations(user_id, progress_results)
            recommendations.extend(collaborative_recommendations)
            
            # 去重和排序
            unique_recommendations = self._deduplicate_recommendations(recommendations)
            sorted_recommendations = sorted(unique_recommendations, 
                                          key=lambda x: x.get('priority', 0), 
                                          reverse=True)
            
            return sorted_recommendations[:max_recommendations]
            
        except Exception as e:
            self.logger.error(f"Failed to get learning recommendations: {str(e)}")
            return []
    
    def get_learning_analytics(self, user_id: str, time_window_days: int = 30) -> Dict[str, Any]:
        """
        获取学习分析数据
        
        Args:
            user_id: 用户ID
            time_window_days: 时间窗口（天）
            
        Returns:
            Dict: 分析数据
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=time_window_days)
            
            # 获取学习会话数据
            session_query = f"""
            SELECT * FROM {self.learning_sessions_table} 
            WHERE user_id = %s AND start_time BETWEEN %s AND %s
            """
            sessions = self.db.execute_query(session_query, (user_id, start_time, end_time))
            
            # 获取学习进度数据
            progress_query = f"""
            SELECT * FROM {self.learning_progress_table} 
            WHERE user_id = %s AND last_studied BETWEEN %s AND %s
            """
            progress_records = self.db.execute_query(progress_query, (user_id, start_time, end_time))
            
            analytics = {
                'user_id': user_id,
                'analysis_period': f"{time_window_days} days",
                'study_time_metrics': {},
                'progress_metrics': {},
                'efficiency_metrics': {},
                'learning_patterns': {},
                'recommendations': []
            }
            
            # 学习时间统计
            total_study_time = sum(session['duration'] for session in sessions)
            average_session_length = total_study_time / len(sessions) if sessions else 0
            study_days = len(set(session['start_time'].date() for session in sessions))
            
            analytics['study_time_metrics'] = {
                'total_study_time_minutes': total_study_time,
                'average_session_length_minutes': average_session_length,
                'study_days_count': study_days,
                'study_consistency_percentage': (study_days / time_window_days) * 100
            }
            
            # 进度统计
            if progress_records:
                completion_scores = [record['completion_percentage'] for record in progress_records]
                confidence_scores = [record['confidence_score'] for record in progress_records]
                
                analytics['progress_metrics'] = {
                    'average_completion_percentage': np.mean(completion_scores) if completion_scores else 0,
                    'max_completion_percentage': max(completion_scores) if completion_scores else 0,
                    'average_confidence_score': np.mean(confidence_scores) if confidence_scores else 0,
                    'components_studied': len(progress_records)
                }
            
            # 效率统计
            if sessions:
                focus_scores = [session['focus_score'] for session in sessions]
                comprehension_scores = [session['comprehension_score'] for session in sessions]
                
                analytics['efficiency_metrics'] = {
                    'average_focus_score': np.mean(focus_scores) if focus_scores else 0,
                    'average_comprehension_score': np.mean(comprehension_scores) if comprehension_scores else 0,
                    'learning_efficiency_index': self._calculate_learning_efficiency(sessions, progress_records)
                }
            
            # 学习模式分析
            analytics['learning_patterns'] = self._analyze_learning_patterns_detailed(user_id, sessions, progress_records)
            
            # 生成改进建议
            analytics['recommendations'] = self._generate_analytics_recommendations(analytics)
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Failed to get learning analytics: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_confidence_score(self, progress: LearningProgress) -> float:
        """计算置信度分数"""
        try:
            # 基于测验分数的一致性
            quiz_consistency = 0.0
            if len(progress.quiz_scores) >= 2:
                quiz_consistency = 1.0 - (np.std(progress.quiz_scores) / 100.0)
            
            # 基于练习成功率
            practice_confidence = progress.successful_attempts / max(1, progress.practice_attempts)
            
            # 基于学习时长
            time_confidence = min(1.0, progress.study_duration / 120.0)  # 假设2小时达到完全置信
            
            # 综合置信度
            confidence = (0.4 * quiz_consistency + 
                         0.4 * practice_confidence + 
                         0.2 * time_confidence)
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            self.logger.debug(f"Error calculating confidence score: {str(e)}")
            return 0.5
    
    def _determine_mastery_level(self, completion_percentage: float, confidence_score: float) -> ProficiencyLevel:
        """确定熟练程度等级"""
        mastery_score = (completion_percentage / 100.0) * confidence_score
        
        if mastery_score >= 0.9:
            return ProficiencyLevel.EXPERT
        elif mastery_score >= 0.7:
            return ProficiencyLevel.ADVANCED
        elif mastery_score >= 0.3:
            return ProficiencyLevel.INTERMEDIATE
        else:
            return ProficiencyLevel.BEGINNER
    
    def _calculate_learning_velocity(self, progress: LearningProgress, current_duration: int, 
                                   time_since_last_study: float) -> float:
        """计算学习速度"""
        try:
            if progress.study_duration <= 0:
                return 0.0
            
            # 基于最近的学习效率和频率
            recent_efficiency = current_duration / max(1, time_since_last_study)
            overall_efficiency = progress.completion_percentage / max(1, progress.study_duration)
            
            # 综合学习速度
            velocity = (0.7 * recent_efficiency + 0.3 * overall_efficiency) / 10.0  # 归一化
            
            return max(0.0, min(1.0, velocity))
            
        except Exception as e:
            self.logger.debug(f"Error calculating learning velocity: {str(e)}")
            return 0.5
    
    def _calculate_retention_score(self, progress: LearningProgress, time_since_last_study: float) -> float:
        """计算记忆保持分数"""
        try:
            # 基于艾宾浩斯遗忘曲线
            hours_since_study = time_since_last_study
            decay_factor = math.exp(-hours_since_study / (24.0 * 7.0))  # 一周衰减常数
            
            # 初始保持分数基于掌握程度
            initial_retention = progress.confidence_score * (progress.completion_percentage / 100.0)
            
            # 应用衰减
            retention = initial_retention * decay_factor
            
            return max(0.0, min(1.0, retention))
            
        except Exception as e:
            self.logger.debug(f"Error calculating retention score: {str(e)}")
            return progress.retention_score * 0.9  # 保守衰减
    
    def _calculate_next_review_date(self, progress: LearningProgress) -> datetime:
        """计算下次复习时间"""
        try:
            # 基于记忆保持分数和熟练程度
            if progress.retention_score > 0.8:
                # 记忆保持良好，延长复习间隔
                review_interval_hours = self.min_review_interval * (1.0 / progress.retention_score)
            else:
                # 需要尽快复习
                review_interval_hours = self.min_review_interval
            
            # 基于熟练程度调整
            if progress.mastery_level == ProficiencyLevel.EXPERT:
                review_interval_hours *= 3.0
            elif progress.mastery_level == ProficiencyLevel.ADVANCED:
                review_interval_hours *= 2.0
            
            next_review = progress.last_studied + timedelta(hours=review_interval_hours)
            
            # 确保不会太早安排复习
            min_review = progress.last_studied + timedelta(hours=self.min_review_interval)
            return max(next_review, min_review)
            
        except Exception as e:
            self.logger.debug(f"Error calculating next review date: {str(e)}")
            return progress.last_studied + timedelta(hours=self.min_review_interval)
    
    def _generate_learning_milestones(self, components: List[str], total_time: int) -> List[Dict[str, Any]]:
        """生成学习里程碑"""
        milestones = []
        component_count = len(components)
        
        if component_count == 0:
            return milestones
        
        # 创建基于组件的里程碑
        for i, component_id in enumerate(components):
            milestone = {
                'milestone_id': str(uuid.uuid4()),
                'component_id': component_id,
                'name': f'完成组件 {i+1}',
                'target_completion': (i + 1) / component_count * 100,
                'completed': False,
                'completion_date': None
            }
            milestones.append(milestone)
        
        # 添加基于时间的里程碑
        time_milestones = [0.25, 0.5, 0.75, 1.0]  # 25%, 50%, 75%, 100%
        for progress in time_milestones:
            milestone = {
                'milestone_id': str(uuid.uuid4()),
                'component_id': None,
                'name': f'完成 {int(progress * 100)}% 学习内容',
                'target_completion': progress * 100,
                'completed': False,
                'completion_date': None
            }
            milestones.append(milestone)
        
        return milestones
    
    def _get_beginner_recommendations(self, user_id: str, max_recommendations: int) -> List[Dict[str, Any]]:
        """获取初学者推荐"""
        try:
            # 查询入门级知识组件
            query = f"""
            SELECT * FROM {self.knowledge_components_table} 
            WHERE difficulty_level <= 3 
            ORDER BY difficulty_level ASC 
            LIMIT %s
            """
            results = self.db.execute_query(query, (max_recommendations * 2,))
            
            recommendations = []
            for row in results:
                recommendation = {
                    'type': 'beginner_component',
                    'component_id': row['component_id'],
                    'name': row['name'],
                    'description': row['description'],
                    'reason': '适合初学者的入门内容',
                    'priority': 8,  # 高优先级
                    'estimated_time': row['estimated_study_time'],
                    'difficulty': row['difficulty_level']
                }
                recommendations.append(recommendation)
            
            return recommendations[:max_recommendations]
            
        except Exception as e:
            self.logger.error(f"Error getting beginner recommendations: {str(e)}")
            return []
    
    def _get_review_recommendations(self, user_id: str, progress_records: List[Dict]) -> List[Dict[str, Any]]:
        """获取复习推荐"""
        recommendations = []
        current_time = datetime.now()
        
        for record in progress_records:
            next_review = record['next_review_date']
            retention_score = record['retention_score']
            
            # 如果记忆保持分数低或已到复习时间，推荐复习
            if retention_score < 0.6 or current_time >= next_review:
                component = self.get_knowledge_component(record['component_id'])
                if component:
                    recommendation = {
                        'type': 'review',
                        'component_id': record['component_id'],
                        'name': component.name,
                        'description': f'复习 {component.name}',
                        'reason': f'记忆保持分数较低 ({retention_score:.1%})，建议复习',
                        'priority': 9 if retention_score < 0.4 else 7,
                        'estimated_time': 30,  # 复习时间较短
                        'retention_score': retention_score
                    }
                    recommendations.append(recommendation)
        
        return recommendations
    
    def _get_path_based_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """获取基于学习路径的推荐"""
        try:
            # 获取用户的学习路径
            query = f"SELECT * FROM {self.learning_paths_table} WHERE user_id = %s AND current_progress < 100"
            paths = self.db.execute_query(query, (user_id,))
            
            recommendations = []
            for path in paths:
                components = json.loads(path['components'])
                current_progress = path['current_progress']
                
                # 找到下一个应该学习的组件
                for i, component_id in enumerate(components):
                    progress = self.get_learning_progress(user_id, component_id)
                    if not progress or progress.completion_percentage < 80:
                        component = self.get_knowledge_component(component_id)
                        if component:
                            recommendation = {
                                'type': 'path_next',
                                'component_id': component_id,
                                'name': component.name,
                                'description': f'学习路径 "{path["name"]}" 的下一步',
                                'reason': f'继续学习路径 "{path["name"]}"',
                                'priority': 6,
                                'estimated_time': component.estimated_study_time,
                                'path_name': path['name']
                            }
                            recommendations.append(recommendation)
                        break
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting path-based recommendations: {str(e)}")
            return []
    
    def _get_collaborative_recommendations(self, user_id: str, progress_records: List[Dict]) -> List[Dict[str, Any]]:
        """获取协同过滤推荐"""
        # 简化实现：基于相似领域推荐
        try:
            # 获取用户已学习的领域
            user_domains = {}
            for record in progress_records:
                component = self.get_knowledge_component(record['component_id'])
                if component:
                    domain = component.domain.value
                    user_domains[domain] = user_domains.get(domain, 0) + record['completion_percentage']
            
            if not user_domains:
                return []
            
            # 找到用户最擅长的领域
            primary_domain = max(user_domains.items(), key=lambda x: x[1])[0]
            
            # 推荐同一领域的中级内容
            query = f"""
            SELECT * FROM {self.knowledge_components_table} 
            WHERE domain = %s AND difficulty_level BETWEEN 4 AND 7
            AND component_id NOT IN (
                SELECT component_id FROM {self.learning_progress_table} WHERE user_id = %s
            )
            ORDER BY difficulty_level ASC 
            LIMIT 3
            """
            results = self.db.execute_query(query, (primary_domain, user_id))
            
            recommendations = []
            for row in results:
                recommendation = {
                    'type': 'collaborative',
                    'component_id': row['component_id'],
                    'name': row['name'],
                    'description': row['description'],
                    'reason': f'基于您在 {primary_domain} 领域的学习进展推荐',
                    'priority': 5,
                    'estimated_time': row['estimated_study_time'],
                    'domain': primary_domain
                }
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting collaborative recommendations: {str(e)}")
            return []
    
    def _analyze_learning_patterns(self, user_id: str, progress_records: List[Dict]) -> Dict[str, Any]:
        """分析学习模式"""
        patterns = {
            'preferred_domains': {},
            'learning_pace': 'medium',
            'consistency_score': 0.0,
            'efficiency_trend': 'stable'
        }
        
        if not progress_records:
            return patterns
        
        # 分析领域偏好
        domain_completion = {}
        for record in progress_records:
            component = self.get_knowledge_component(record['component_id'])
            if component:
                domain = component.domain.value
                domain_completion[domain] = domain_completion.get(domain, 0) + record['completion_percentage']
        
        patterns['preferred_domains'] = domain_completion
        
        # 分析学习节奏
        completion_rates = [record['completion_percentage'] / max(1, record['study_duration']) 
                          for record in progress_records]
        avg_completion_rate = np.mean(completion_rates) if completion_rates else 0
        
        if avg_completion_rate > 2.0:
            patterns['learning_pace'] = 'fast'
        elif avg_completion_rate < 0.5:
            patterns['learning_pace'] = 'slow'
        else:
            patterns['learning_pace'] = 'medium'
        
        return patterns
    
    def _deduplicate_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
        """去重推荐"""
        seen = set()
        unique = []
        
        for rec in recommendations:
            key = rec['component_id']
            if key not in seen:
                seen.add(key)
                unique.append(rec)
        
        return unique
    
    def _calculate_learning_efficiency(self, sessions: List[Dict], progress_records: List[Dict]) -> float:
        """计算学习效率指数"""
        if not sessions or not progress_records:
            return 0.0
        
        # 基于专注度和理解度的效率计算
        avg_focus = np.mean([session['focus_score'] for session in sessions])
        avg_comprehension = np.mean([session['comprehension_score'] for session in sessions])
        
        # 基于进度增长的速度
        progress_gains = [record['completion_percentage'] for record in progress_records]
        progress_velocity = np.mean(np.diff(progress_gains)) if len(progress_gains) > 1 else 0
        
        # 综合效率指数
        efficiency = (0.4 * avg_focus + 0.4 * avg_comprehension + 0.2 * min(1.0, progress_velocity / 10.0))
        
        return max(0.0, min(1.0, efficiency))
    
    def _analyze_learning_patterns_detailed(self, user_id: str, sessions: List[Dict], 
                                          progress_records: List[Dict]) -> Dict[str, Any]:
        """详细分析学习模式"""
        patterns = {
            'time_patterns': {},
            'content_preferences': {},
            'efficiency_metrics': {},
            'challenge_areas': []
        }
        
        if not sessions:
            return patterns
        
        # 分析时间段偏好
        hour_counts = {}
        for session in sessions:
            hour = session['start_time'].hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        patterns['time_patterns']['by_hour'] = dict(sorted(hour_counts.items()))
        
        # 分析内容偏好
        domain_engagement = {}
        for record in progress_records:
            component = self.get_knowledge_component(record['component_id'])
            if component:
                domain = component.domain.value
                engagement = record['study_duration'] * record['completion_percentage']
                domain_engagement[domain] = domain_engagement.get(domain, 0) + engagement
        
        patterns['content_preferences'] = domain_engagement
        
        # 识别挑战领域
        low_confidence_components = []
        for record in progress_records:
            if record['confidence_score'] < 0.5 and record['study_duration'] > 30:
                component = self.get_knowledge_component(record['component_id'])
                if component:
                    low_confidence_components.append({
                        'component_id': record['component_id'],
                        'name': component.name,
                        'confidence_score': record['confidence_score'],
                        'study_duration': record['study_duration']
                    })
        
        patterns['challenge_areas'] = sorted(low_confidence_components, 
                                           key=lambda x: x['confidence_score'])[:5]
        
        return patterns
    
    def _generate_analytics_recommendations(self, analytics: Dict[str, Any]) -> List[str]:
        """生成分析建议"""
        recommendations = []
        
        # 基于学习时间的建议
        study_metrics = analytics.get('study_time_metrics', {})
        consistency = study_metrics.get('study_consistency_percentage', 0)
        
        if consistency < 50:
            recommendations.append("学习连续性较低，建议制定更规律的学习计划")
        elif consistency > 80:
            recommendations.append("学习连续性很好，继续保持!")
        
        # 基于效率的建议
        efficiency_metrics = analytics.get('efficiency_metrics', {})
        focus_score = efficiency_metrics.get('average_focus_score', 0)
        
        if focus_score < 0.6:
            recommendations.append("专注度有待提高，尝试在较少干扰的环境中学习")
        
        # 基于挑战领域的建议
        patterns = analytics.get('learning_patterns', {})
        challenge_areas = patterns.get('challenge_areas', [])
        
        if challenge_areas:
            area_names = [area['name'] for area in challenge_areas[:2]]
            recommendations.append(f"在 {', '.join(area_names)} 方面需要额外练习")
        
        return recommendations

