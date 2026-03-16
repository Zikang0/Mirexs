"""
个人助理智能体模块：处理个人事务
实现基于用户偏好和上下文的个性化助理服务
"""

import uuid
import datetime
import json
from typing import List, Dict, Any, Optional, Tuple
import logging
from enum import Enum
import asyncio

class PersonalDomain(Enum):
    SCHEDULE = "schedule"  # 日程管理
    COMMUNICATION = "communication"  # 通信管理
    INFORMATION = "information"  # 信息管理
    REMINDERS = "reminders"  # 提醒管理
    PREFERENCES = "preferences"  # 偏好管理

class PriorityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    URGENT = "urgent"

class PersonalAgent:
    """个人助理智能体 - 处理个人事务"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # 智能体身份
        self.agent_id = self.config.get('agent_id', f"personal_agent_{uuid.uuid4().hex[:8]}")
        self.agent_type = "personal"
        
        # 服务领域配置
        self.supported_domains = self.config.get('supported_domains', [domain.value for domain in PersonalDomain])
        self.service_level = self.config.get('service_level', 'standard')  # basic, standard, premium
        
        # 用户配置
        self.user_profile = self.config.get('user_profile', {})
        self.user_preferences = self.config.get('user_preferences', {})
        self.privacy_level = self.config.get('privacy_level', 'medium')  # low, medium, high
        
        # 数据存储
        self.schedule_data = self._initialize_schedule_data()
        self.reminder_system = self._initialize_reminder_system()
        self.communication_log = []
        self.information_base = self._initialize_information_base()
        
        # 工作状态
        self.current_tasks = set()
        self.service_history = []
        self.performance_metrics = {
            'tasks_completed': 0,
            'reminders_set': 0,
            'schedules_managed': 0,
            'user_satisfaction': 0.8,
            'response_times': []
        }
        
        # 个性化引擎
        self._initialize_personalization_engine()
        
        self.initialized = True
        self.logger.info(f"个人助理智能体初始化成功: {self.agent_id}")
    
    def _initialize_schedule_data(self) -> Dict[str, Any]:
        """初始化日程数据"""
        return {
            'events': [],
            'recurring_events': [],
            'working_hours': {'start': '09:00', 'end': '18:00'},
            'timezone': 'Asia/Shanghai',
            'preferred_meeting_times': ['10:00-12:00', '14:00-16:00']
        }
    
    def _initialize_reminder_system(self) -> Dict[str, Any]:
        """初始化提醒系统"""
        return {
            'active_reminders': [],
            'completed_reminders': [],
            'reminder_preferences': {
                'advance_notice': 15,  # 分钟
                'recurring_reminders': True,
                'escalation_enabled': True
            }
        }
    
    def _initialize_information_base(self) -> Dict[str, Any]:
        """初始化信息库"""
        return {
            'contacts': [],
            'important_dates': [],
            'frequent_locations': [],
            'personal_notes': [],
            'preferences': {
                'communication_style': 'professional',
                'response_timing': 'balanced',
                'information_depth': 'moderate'
            }
        }
    
    def _initialize_personalization_engine(self):
        """初始化个性化引擎"""
        try:
            # 加载用户行为模式
            self.user_patterns = self._analyze_user_patterns()
            
            # 初始化推荐系统
            self.recommendation_engine = self._create_recommendation_engine()
            
            self.logger.info("个性化引擎初始化完成")
            
        except Exception as e:
            self.logger.error(f"个性化引擎初始化失败: {e}")
            self.user_patterns = {}
            self.recommendation_engine = None
    
    def _analyze_user_patterns(self) -> Dict[str, Any]:
        """分析用户模式"""
        # 基于历史数据的简单模式分析
        patterns = {
            'schedule_patterns': {
                'busy_periods': [],
                'preferred_meeting_times': [],
                'break_patterns': []
            },
            'communication_patterns': {
                'response_times': {},
                'preferred_channels': [],
                'communication_style': 'balanced'
            },
            'preference_patterns': {
                'topic_interests': [],
                'avoidance_topics': [],
                'interaction_preferences': {}
            }
        }
        
        return patterns
    
    def _create_recommendation_engine(self):
        """创建推荐引擎"""
        # 简化的推荐引擎
        return {
            'content_based': True,
            'collaborative_filtering': False,
            'context_aware': True
        }
    
    async def manage_schedule(self,
                            task_id: str,
                            action: str,
                            schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        管理日程
        
        Args:
            task_id: 任务ID
            action: 操作类型 (add, update, delete, view)
            schedule_data: 日程数据
            
        Returns:
            操作结果
        """
        try:
            self.current_tasks.add(task_id)
            
            result = {}
            
            if action == 'add':
                result = await self._add_schedule_event(schedule_data)
            elif action == 'update':
                result = await self._update_schedule_event(schedule_data)
            elif action == 'delete':
                result = await self._delete_schedule_event(schedule_data)
            elif action == 'view':
                result = await self._view_schedule(schedule_data)
            else:
                result = {'success': False, 'error': f'不支持的操作: {action}'}
            
            # 记录服务历史
            self.service_history.append({
                'task_id': task_id,
                'action': 'schedule_management',
                'operation': action,
                'data': schedule_data,
                'result': result,
                'timestamp': datetime.datetime.now().isoformat()
            })
            
            # 更新性能指标
            self.performance_metrics['tasks_completed'] += 1
            self.performance_metrics['schedules_managed'] += 1
            
            self.current_tasks.remove(task_id)
            
            return {
                'success': True,
                'task_id': task_id,
                'action': action,
                'result': result
            }
            
        except Exception as e:
            self.logger.error(f"日程管理失败: {e}")
            self.current_tasks.remove(task_id)
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e)
            }
    
    async def _add_schedule_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加日程事件"""
        try:
            # 验证事件数据
            validation_result = self._validate_schedule_event(event_data)
            if not validation_result['valid']:
                return {'success': False, 'error': validation_result['errors']}
            
            # 检查时间冲突
            conflict_check = self._check_schedule_conflicts(event_data)
            if conflict_check['has_conflict']:
                return {
                    'success': False, 
                    'error': '时间冲突',
                    'conflicting_events': conflict_check['conflicting_events']
                }
            
            # 生成事件ID
            event_id = str(uuid.uuid4())
            event_data['id'] = event_id
            event_data['created_at'] = datetime.datetime.now().isoformat()
            event_data['status'] = 'scheduled'
            
            # 添加到日程
            self.schedule_data['events'].append(event_data)
            
            # 如果是重要事件，设置提醒
            if event_data.get('priority') in ['high', 'urgent']:
                reminder_data = self._create_reminder_from_event(event_data)
                await self._set_reminder(reminder_data)
            
            return {
                'success': True,
                'event_id': event_id,
                'message': '事件添加成功',
                'event_data': event_data
            }
            
        except Exception as e:
            self.logger.error(f"添加日程事件失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _validate_schedule_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证日程事件"""
        errors = []
        
        required_fields = ['title', 'start_time', 'end_time']
        for field in required_fields:
            if field not in event_data:
                errors.append(f"缺少必需字段: {field}")
        
        # 时间格式验证
        if 'start_time' in event_data and 'end_time' in event_data:
            try:
                start_time = datetime.datetime.fromisoformat(event_data['start_time'])
                end_time = datetime.datetime.fromisoformat(event_data['end_time'])
                
                if end_time <= start_time:
                    errors.append("结束时间必须晚于开始时间")
                
                if (end_time - start_time).total_seconds() > 86400:  # 24小时
                    errors.append("事件持续时间不能超过24小时")
                    
            except ValueError:
                errors.append("时间格式不正确，请使用ISO格式")
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    def _check_schedule_conflicts(self, new_event: Dict[str, Any]) -> Dict[str, Any]:
        """检查日程冲突"""
        conflicts = []
        
        try:
            new_start = datetime.datetime.fromisoformat(new_event['start_time'])
            new_end = datetime.datetime.fromisoformat(new_event['end_time'])
            
            for existing_event in self.schedule_data['events']:
                if existing_event.get('status') != 'scheduled':
                    continue
                
                existing_start = datetime.datetime.fromisoformat(existing_event['start_time'])
                existing_end = datetime.datetime.fromisoformat(existing_event['end_time'])
                
                # 检查时间重叠
                if (new_start < existing_end and new_end > existing_start):
                    conflicts.append({
                        'event_id': existing_event.get('id'),
                        'title': existing_event.get('title'),
                        'conflict_period': f"{existing_start} - {existing_end}"
                    })
            
            return {
                'has_conflict': len(conflicts) > 0,
                'conflicting_events': conflicts
            }
            
        except Exception as e:
            self.logger.error(f"检查日程冲突失败: {e}")
            return {'has_conflict': False, 'conflicting_events': []}
    
    def _create_reminder_from_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """从事件创建提醒"""
        reminder_time = datetime.datetime.fromisoformat(event_data['start_time']) - datetime.timedelta(
            minutes=self.reminder_system['reminder_preferences']['advance_notice']
        )
        
        return {
            'title': f"提醒: {event_data['title']}",
            'message': event_data.get('description', ''),
            'reminder_time': reminder_time.isoformat(),
            'event_id': event_data['id'],
            'priority': event_data.get('priority', 'medium'),
            'recurring': False
        }
    
    async def _update_schedule_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新日程事件"""
        event_id = event_data.get('id')
        if not event_id:
            return {'success': False, 'error': '缺少事件ID'}
        
        # 查找事件
        target_event = None
        for event in self.schedule_data['events']:
            if event.get('id') == event_id:
                target_event = event
                break
        
        if not target_event:
            return {'success': False, 'error': '事件不存在'}
        
        # 更新事件数据
        for key, value in event_data.items():
            if key != 'id':  # 不更新ID
                target_event[key] = value
        
        target_event['updated_at'] = datetime.datetime.now().isoformat()
        
        return {
            'success': True,
            'event_id': event_id,
            'message': '事件更新成功',
            'updated_event': target_event
        }
    
    async def _delete_schedule_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """删除日程事件"""
        event_id = event_data.get('id')
        if not event_id:
            return {'success': False, 'error': '缺少事件ID'}
        
        # 查找并删除事件
        for i, event in enumerate(self.schedule_data['events']):
            if event.get('id') == event_id:
                deleted_event = self.schedule_data['events'].pop(i)
                
                # 移除相关提醒
                self._remove_related_reminders(event_id)
                
                return {
                    'success': True,
                    'event_id': event_id,
                    'message': '事件删除成功',
                    'deleted_event': deleted_event
                }
        
        return {'success': False, 'error': '事件不存在'}
    
    def _remove_related_reminders(self, event_id: str):
        """移除相关提醒"""
        self.reminder_system['active_reminders'] = [
            reminder for reminder in self.reminder_system['active_reminders']
            if reminder.get('event_id') != event_id
        ]
    
    async def _view_schedule(self, view_params: Dict[str, Any]) -> Dict[str, Any]:
        """查看日程"""
        date_range = view_params.get('date_range', 'today')
        view_type = view_params.get('view_type', 'list')
        
        # 过滤事件
        filtered_events = self._filter_events_by_date_range(date_range)
        
        # 格式化输出
        if view_type == 'calendar':
            formatted_events = self._format_calendar_view(filtered_events)
        else:
            formatted_events = self._format_list_view(filtered_events)
        
        return {
            'success': True,
            'date_range': date_range,
            'view_type': view_type,
            'events': filtered_events,
            'formatted_view': formatted_events,
            'total_events': len(filtered_events)
        }
    
    def _filter_events_by_date_range(self, date_range: str) -> List[Dict[str, Any]]:
        """按日期范围过滤事件"""
        today = datetime.datetime.now().date()
        filtered_events = []
        
        for event in self.schedule_data['events']:
            if event.get('status') != 'scheduled':
                continue
            
            event_date = datetime.datetime.fromisoformat(event['start_time']).date()
            
            if date_range == 'today' and event_date == today:
                filtered_events.append(event)
            elif date_range == 'week' and (event_date - today).days <= 7:
                filtered_events.append(event)
            elif date_range == 'month' and (event_date - today).days <= 30:
                filtered_events.append(event)
            elif date_range == 'all':
                filtered_events.append(event)
        
        return filtered_events
    
    def _format_calendar_view(self, events: List[Dict[str, Any]]) -> str:
        """格式化日历视图"""
        calendar_view = "日程日历视图:\n"
        calendar_view += "=" * 50 + "\n"
        
        # 按日期分组
        events_by_date = {}
        for event in events:
            event_date = datetime.datetime.fromisoformat(event['start_time']).strftime('%Y-%m-%d')
            if event_date not in events_by_date:
                events_by_date[event_date] = []
            events_by_date[event_date].append(event)
        
        # 生成日历
        for date_str, date_events in sorted(events_by_date.items()):
            calendar_view += f"\n{date_str}:\n"
            for event in date_events:
                start_time = datetime.datetime.fromisoformat(event['start_time']).strftime('%H:%M')
                calendar_view += f"  {start_time} - {event['title']}\n"
        
        return calendar_view
    
    def _format_list_view(self, events: List[Dict[str, Any]]) -> str:
        """格式化列表视图"""
        list_view = "日程列表:\n"
        list_view += "=" * 50 + "\n"
        
        for event in sorted(events, key=lambda x: x['start_time']):
            start_time = datetime.datetime.fromisoformat(event['start_time']).strftime('%m-%d %H:%M')
            priority = event.get('priority', 'medium')
            list_view += f"{start_time} [{priority}] {event['title']}\n"
        
        return list_view
    
    async def set_reminder(self,
                         task_id: str,
                         reminder_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        设置提醒
        
        Args:
            task_id: 任务ID
            reminder_data: 提醒数据
            
        Returns:
            设置结果
        """
        try:
            self.current_tasks.add(task_id)
            
            result = await self._set_reminder(reminder_data)
            
            # 记录服务历史
            self.service_history.append({
                'task_id': task_id,
                'action': 'set_reminder',
                'reminder_data': reminder_data,
                'result': result,
                'timestamp': datetime.datetime.now().isoformat()
            })
            
            # 更新性能指标
            self.performance_metrics['tasks_completed'] += 1
            self.performance_metrics['reminders_set'] += 1
            
            self.current_tasks.remove(task_id)
            
            return {
                'success': True,
                'task_id': task_id,
                'result': result
            }
            
        except Exception as e:
            self.logger.error(f"设置提醒失败: {e}")
            self.current_tasks.remove(task_id)
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e)
            }
    
    async def _set_reminder(self, reminder_data: Dict[str, Any]) -> Dict[str, Any]:
        """设置提醒实现"""
        try:
            # 验证提醒数据
            validation_result = self._validate_reminder_data(reminder_data)
            if not validation_result['valid']:
                return {'success': False, 'error': validation_result['errors']}
            
            # 生成提醒ID
            reminder_id = str(uuid.uuid4())
            reminder_data['id'] = reminder_id
            reminder_data['created_at'] = datetime.datetime.now().isoformat()
            reminder_data['status'] = 'active'
            
            # 添加到提醒系统
            self.reminder_system['active_reminders'].append(reminder_data)
            
            # 启动提醒检查（在实际系统中会使用定时任务）
            self._schedule_reminder_check(reminder_data)
            
            return {
                'success': True,
                'reminder_id': reminder_id,
                'message': '提醒设置成功',
                'reminder_data': reminder_data
            }
            
        except Exception as e:
            self.logger.error(f"设置提醒实现失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _validate_reminder_data(self, reminder_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证提醒数据"""
        errors = []
        
        required_fields = ['title', 'reminder_time']
        for field in required_fields:
            if field not in reminder_data:
                errors.append(f"缺少必需字段: {field}")
        
        # 时间验证
        if 'reminder_time' in reminder_data:
            try:
                reminder_time = datetime.datetime.fromisoformat(reminder_data['reminder_time'])
                if reminder_time <= datetime.datetime.now():
                    errors.append("提醒时间必须是将来的时间")
            except ValueError:
                errors.append("提醒时间格式不正确，请使用ISO格式")
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    def _schedule_reminder_check(self, reminder_data: Dict[str, Any]):
        """调度提醒检查"""
        # 在实际系统中，这里会使用定时任务或事件循环
        # 这里使用简化实现
        reminder_time = datetime.datetime.fromisoformat(reminder_data['reminder_time'])
        time_difference = (reminder_time - datetime.datetime.now()).total_seconds()
        
        if time_difference > 0:
            # 记录需要检查的提醒
            self.logger.info(f"提醒已调度: {reminder_data['title']} 在 {time_difference} 秒后")
        else:
            self.logger.warning(f"提醒时间已过: {reminder_data['title']}")
    
    async def provide_information(self,
                                task_id: str,
                                query: str,
                                context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        提供信息
        
        Args:
            task_id: 任务ID
            query: 查询内容
            context: 上下文信息
            
        Returns:
            信息结果
        """
        try:
            self.current_tasks.add(task_id)
            
            # 分析查询意图
            intent_analysis = self._analyze_query_intent(query, context)
            
            # 检索相关信息
            information_result = await self._retrieve_information(intent_analysis, context)
            
            # 个性化响应
            personalized_response = self._personalize_response(information_result, intent_analysis)
            
            # 记录服务历史
            self.service_history.append({
                'task_id': task_id,
                'action': 'information_provision',
                'query': query,
                'intent_analysis': intent_analysis,
                'response': personalized_response,
                'timestamp': datetime.datetime.now().isoformat()
            })
            
            # 更新性能指标
            self.performance_metrics['tasks_completed'] += 1
            
            self.current_tasks.remove(task_id)
            
            return {
                'success': True,
                'task_id': task_id,
                'query': query,
                'response': personalized_response,
                'intent_analysis': intent_analysis
            }
            
        except Exception as e:
            self.logger.error(f"信息提供失败: {e}")
            self.current_tasks.remove(task_id)
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e)
            }
    
    def _analyze_query_intent(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析查询意图"""
        query_lower = query.lower()
        
        intent_categories = {
            'schedule': ['日程', '安排', '会议', '约会', '时间表'],
            'reminder': ['提醒', '记住', '别忘了', '记得'],
            'contact': ['联系人', '电话', '邮箱', '地址'],
            'information': ['信息', '资料', '详情', '了解'],
            'preference': ['偏好', '喜欢', '习惯', '设置']
        }
        
        detected_intents = []
        confidence_scores = {}
        
        for intent, keywords in intent_categories.items():
            keyword_matches = sum(1 for keyword in keywords if keyword in query_lower)
            if keyword_matches > 0:
                detected_intents.append(intent)
                confidence_scores[intent] = keyword_matches / len(keywords)
        
        # 如果没有检测到明确意图，使用默认
        if not detected_intents:
            detected_intents = ['information']
            confidence_scores['information'] = 0.5
        
        return {
            'primary_intent': detected_intents[0],
            'all_intents': detected_intents,
            'confidence_scores': confidence_scores,
            'query_complexity': self._assess_query_complexity(query),
            'urgency_level': self._assess_urgency_level(query, context)
        }
    
    def _assess_query_complexity(self, query: str) -> str:
        """评估查询复杂度"""
        word_count = len(query.split())
        
        if word_count <= 3:
            return 'simple'
        elif word_count <= 8:
            return 'moderate'
        else:
            return 'complex'
    
    def _assess_urgency_level(self, query: str, context: Dict[str, Any]) -> str:
        """评估紧急性"""
        urgent_keywords = ['紧急', '立刻', '马上', '尽快', '立即']
        query_lower = query.lower()
        
        if any(keyword in query_lower for keyword in urgent_keywords):
            return 'high'
        elif context and context.get('urgent'):
            return 'high'
        else:
            return 'normal'
    
    async def _retrieve_information(self, intent_analysis: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """检索信息"""
        primary_intent = intent_analysis['primary_intent']
        
        if primary_intent == 'schedule':
            return await self._get_schedule_information(context)
        elif primary_intent == 'reminder':
            return await self._get_reminder_information(context)
        elif primary_intent == 'contact':
            return await self._get_contact_information(context)
        elif primary_intent == 'preference':
            return await self._get_preference_information(context)
        else:
            return await self._get_general_information(context)
    
    async def _get_schedule_information(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """获取日程信息"""
        date_range = context.get('date_range', 'today')
        events = self._filter_events_by_date_range(date_range)
        
        return {
            'information_type': 'schedule',
            'date_range': date_range,
            'events': events,
            'summary': f"找到 {len(events)} 个日程事件",
            'suggestions': self._generate_schedule_suggestions(events)
        }
    
    def _generate_schedule_suggestions(self, events: List[Dict[str, Any]]) -> List[str]:
        """生成日程建议"""
        suggestions = []
        
        # 检查时间冲突
        conflict_check = self._check_multiple_conflicts(events)
        if conflict_check['has_conflicts']:
            suggestions.append("检测到日程冲突，建议调整时间安排")
        
        # 检查密集安排
        if len(events) > 5:
            suggestions.append("今日日程较多，建议安排休息时间")
        
        # 检查重要事件准备
        important_events = [e for e in events if e.get('priority') in ['high', 'urgent']]
        if important_events:
            suggestions.append(f"今日有 {len(important_events)} 个重要事件，请提前准备")
        
        return suggestions
    
    def _check_multiple_conflicts(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检查多个事件冲突"""
        conflicts = []
        
        for i, event1 in enumerate(events):
            for j, event2 in enumerate(events[i+1:], i+1):
                conflict_check = self._check_schedule_conflicts_between(event1, event2)
                if conflict_check['has_conflict']:
                    conflicts.append({
                        'event1': event1.get('title'),
                        'event2': event2.get('title'),
                        'conflict_period': conflict_check['conflict_period']
                    })
        
        return {
            'has_conflicts': len(conflicts) > 0,
            'conflict_details': conflicts
        }
    
    def _check_schedule_conflicts_between(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> Dict[str, Any]:
        """检查两个事件间的冲突"""
        try:
            start1 = datetime.datetime.fromisoformat(event1['start_time'])
            end1 = datetime.datetime.fromisoformat(event1['end_time'])
            start2 = datetime.datetime.fromisoformat(event2['start_time'])
            end2 = datetime.datetime.fromisoformat(event2['end_time'])
            
            has_conflict = (start1 < end2 and end1 > start2)
            
            return {
                'has_conflict': has_conflict,
                'conflict_period': f"{max(start1, start2)} - {min(end1, end2)}" if has_conflict else None
            }
            
        except Exception:
            return {'has_conflict': False, 'conflict_period': None}
    
    async def _get_reminder_information(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """获取提醒信息"""
        active_reminders = self.reminder_system['active_reminders']
        completed_reminders = self.reminder_system['completed_reminders']
        
        return {
            'information_type': 'reminders',
            'active_reminders': active_reminders,
            'completed_reminders': completed_reminders,
            'summary': f"有 {len(active_reminders)} 个活跃提醒，{len(completed_reminders)} 个已完成提醒"
        }
    
    async def _get_contact_information(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """获取联系人信息"""
        search_term = context.get('search_term', '')
        contacts = self.information_base.get('contacts', [])
        
        if search_term:
            filtered_contacts = [
                contact for contact in contacts
                if search_term.lower() in contact.get('name', '').lower()
            ]
        else:
            filtered_contacts = contacts
        
        return {
            'information_type': 'contacts',
            'contacts': filtered_contacts,
            'summary': f"找到 {len(filtered_contacts)} 个联系人"
        }
    
    async def _get_preference_information(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """获取偏好信息"""
        return {
            'information_type': 'preferences',
            'user_preferences': self.user_preferences,
            'communication_style': self.information_base['preferences']['communication_style'],
            'response_timing': self.information_base['preferences']['response_timing']
        }
    
    async def _get_general_information(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """获取一般信息"""
        return {
            'information_type': 'general',
            'message': '这是一个一般信息查询响应',
            'suggestions': [
                '您可以询问关于日程、提醒、联系人等信息',
                '使用更具体的关键词可以获得更精确的结果'
            ]
        }
    
    def _personalize_response(self, information_result: Dict[str, Any], intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """个性化响应"""
        communication_style = self.information_base['preferences']['communication_style']
        
        # 根据沟通风格调整响应
        if communication_style == 'professional':
            tone = '专业、正式'
            detail_level = '详细'
        elif communication_style == 'casual':
            tone = '轻松、友好'
            detail_level = '简洁'
        else:  # balanced
            tone = '平衡、适中'
            detail_level = '适中'
        
        # 根据紧急性调整响应格式
        if intent_analysis['urgency_level'] == 'high':
            format_style = '直接、重点突出'
        else:
            format_style = '完整、有条理'
        
        personalized_response = {
            **information_result,
            'personalization': {
                'tone': tone,
                'detail_level': detail_level,
                'format_style': format_style,
                'adapted_for_urgency': intent_analysis['urgency_level']
            },
            'response_timestamp': datetime.datetime.now().isoformat()
        }
        
        return personalized_response
    
    def get_capabilities(self) -> List[str]:
        """获取能力列表"""
        capabilities = [
            'schedule_management',
            'reminder_management', 
            'information_retrieval',
            'personal_assistance',
            'preference_learning'
        ]
        
        # 添加支持的服务领域
        for domain in self.supported_domains:
            capabilities.append(f"{domain}_services")
        
        return capabilities
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            **self.performance_metrics,
            'current_tasks': list(self.current_tasks),
            'supported_domains': self.supported_domains,
            'service_level': self.service_level
        }
    
    def get_service_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取服务历史"""
        return self.service_history[-limit:] if limit else self.service_history
    
    def update_user_preferences(self, new_preferences: Dict[str, Any]) -> bool:
        """更新用户偏好"""
        try:
            self.user_preferences.update(new_preferences)
            
            # 更新信息库中的偏好
            if 'communication_style' in new_preferences:
                self.information_base['preferences']['communication_style'] = new_preferences['communication_style']
            if 'response_timing' in new_preferences:
                self.information_base['preferences']['response_timing'] = new_preferences['response_timing']
            
            self.logger.info("用户偏好已更新")
            return True
            
        except Exception as e:
            self.logger.error(f"更新用户偏好失败: {e}")
            return False

