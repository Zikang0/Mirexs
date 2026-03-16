"""
记忆组织模块：组织记忆结构
实现基于分类和层次结构的记忆组织系统
"""

import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import logging
from .episodic_memory import EpisodicMemory
from .semantic_memory import SemanticMemory

class OrganizationStrategy(Enum):
    HIERARCHICAL = "hierarchical"
    TAXONOMIC = "taxonomic"
    THEMATIC = "thematic"
    CHRONOLOGICAL = "chronological"

class MemoryOrganization:
    """记忆组织系统 - 组织记忆结构"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # 初始化记忆系统
        self.episodic_memory = EpisodicMemory(config.get('episodic_config', {}))
        self.semantic_memory = SemanticMemory(config.get('semantic_config', {}))
        
        # 组织配置
        self.auto_organize = self.config.get('auto_organize', True)
        self.organization_interval = self.config.get('organization_interval', 3600)  # 1小时
        self.max_categories_per_item = self.config.get('max_categories_per_item', 3)
        
        # 分类系统
        self.category_system = self._initialize_category_system()
        self.organization_history = []
        
        self.initialized = True
        self.logger.info("记忆组织系统初始化成功")
    
    def _initialize_category_system(self) -> Dict[str, Any]:
        """初始化分类系统"""
        base_categories = {
            "personal": {
                "description": "个人经历和事件",
                "subcategories": ["work", "leisure", "relationships", "health"]
            },
            "knowledge": {
                "description": "一般知识和信息", 
                "subcategories": ["science", "history", "technology", "arts"]
            },
            "skills": {
                "description": "技能和程序性知识",
                "subcategories": ["professional", "personal", "creative", "physical"]
            },
            "goals": {
                "description": "目标和计划",
                "subcategories": ["short_term", "long_term", "personal", "professional"]
            }
        }
        return base_categories
    
    def organize_memory(self, 
                       memory_item: Dict[str, Any],
                       strategy: OrganizationStrategy = None) -> Dict[str, Any]:
        """
        组织单个记忆项
        
        Args:
            memory_item: 记忆项
            strategy: 组织策略
            
        Returns:
            组织结果
        """
        strategy = strategy or OrganizationStrategy.THEMATIC
        
        try:
            memory_type = memory_item.get('memory_type', 'episodic')
            
            if strategy == OrganizationStrategy.HIERARCHICAL:
                result = self._organize_hierarchical(memory_item, memory_type)
            elif strategy == OrganizationStrategy.TAXONOMIC:
                result = self._organize_taxonomic(memory_item, memory_type)
            elif strategy == OrganizationStrategy.THEMATIC:
                result = self._organize_thematic(memory_item, memory_type)
            elif strategy == OrganizationStrategy.CHRONOLOGICAL:
                result = self._organize_chronological(memory_item, memory_type)
            else:
                result = {"success": False, "error": f"未知的组织策略: {strategy}"}
            
            # 记录组织操作
            self._record_organization(memory_item, strategy, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"记忆组织失败: {e}")
            return {"success": False, "error": str(e)}
    
    def batch_organize(self, 
                      memory_items: List[Dict[str, Any]],
                      strategy: OrganizationStrategy = None) -> Dict[str, Any]:
        """
        批量组织记忆
        
        Args:
            memory_items: 记忆项列表
            strategy: 组织策略
            
        Returns:
            批量组织结果
        """
        strategy = strategy or OrganizationStrategy.THEMATIC
        
        results = {
            'total_processed': len(memory_items),
            'successful': 0,
            'failed': 0,
            'details': []
        }
        
        for item in memory_items:
            organization_result = self.organize_memory(item, strategy)
            results['details'].append(organization_result)
            
            if organization_result.get('success', False):
                results['successful'] += 1
            else:
                results['failed'] += 1
        
        # 记录批量组织会话
        batch_session = {
            'timestamp': datetime.datetime.now().isoformat(),
            'strategy': strategy.value,
            'results': results
        }
        self.organization_history.append(batch_session)
        
        return results
    
    def _organize_hierarchical(self, memory_item: Dict[str, Any], memory_type: str) -> Dict[str, Any]:
        """层次化组织"""
        categories = self._extract_categories(memory_item)
        hierarchical_structure = self._build_hierarchy(categories)
        
        # 应用层次结构
        memory_item['organization'] = {
            'type': 'hierarchical',
            'hierarchy': hierarchical_structure,
            'primary_category': categories[0] if categories else 'uncategorized'
        }
        
        return {
            "success": True,
            "strategy": "hierarchical",
            "categories_assigned": categories,
            "hierarchy_levels": len(hierarchical_structure)
        }
    
    def _organize_taxonomic(self, memory_item: Dict[str, Any], memory_type: str) -> Dict[str, Any]:
        """分类学组织"""
        # 基于预定义分类系统进行分类
        assigned_categories = self._classify_into_taxonomy(memory_item)
        
        memory_item['organization'] = {
            'type': 'taxonomic',
            'categories': assigned_categories,
            'taxonomy_system': 'base_categories'
        }
        
        return {
            "success": True,
            "strategy": "taxonomic", 
            "categories_assigned": assigned_categories
        }
    
    def _organize_thematic(self, memory_item: Dict[str, Any], memory_type: str) -> Dict[str, Any]:
        """主题组织"""
        themes = self._extract_themes(memory_item)
        related_themes = self._find_related_themes(themes)
        
        memory_item['organization'] = {
            'type': 'thematic',
            'primary_themes': themes,
            'related_themes': related_themes,
            'theme_connections': self._build_theme_connections(themes, related_themes)
        }
        
        return {
            "success": True,
            "strategy": "thematic",
            "primary_themes": themes,
            "related_themes_count": len(related_themes)
        }
    
    def _organize_chronological(self, memory_item: Dict[str, Any], memory_type: str) -> Dict[str, Any]:
        """时间顺序组织"""
        timestamp = memory_item.get('timestamp')
        if not timestamp:
            return {"success": False, "error": "无时间信息无法进行时间组织"}
        
        # 确定时间区间和上下文
        time_period = self._determine_time_period(timestamp)
        temporal_context = self._build_temporal_context(timestamp)
        
        memory_item['organization'] = {
            'type': 'chronological',
            'time_period': time_period,
            'temporal_context': temporal_context,
            'chronological_relationships': self._find_chronological_relationships(memory_item)
        }
        
        return {
            "success": True,
            "strategy": "chronological",
            "time_period": time_period,
            "temporal_context": temporal_context
        }
    
    def _extract_categories(self, memory_item: Dict[str, Any]) -> List[str]:
        """提取类别"""
        categories = []
        
        # 从现有类别中提取
        existing_categories = memory_item.get('categories', [])
        if existing_categories:
            if isinstance(existing_categories, str):
                categories.extend(existing_categories.split(','))
            else:
                categories.extend(existing_categories)
        
        # 从内容中提取新类别
        content = self._get_item_content(memory_item)
        if content:
            extracted_categories = self._analyze_content_for_categories(content)
            categories.extend(extracted_categories)
        
        # 去重和限制数量
        unique_categories = list(set(categories))
        return unique_categories[:self.max_categories_per_item]
    
    def _get_item_content(self, memory_item: Dict[str, Any]) -> str:
        """获取项目内容"""
        content_parts = []
        
        if memory_item.get('description'):
            content_parts.append(memory_item['description'])
        if memory_item.get('content'):
            content_parts.append(str(memory_item['content']))
        if memory_item.get('name'):
            content_parts.append(memory_item['name'])
        
        return ' '.join(content_parts)
    
    def _analyze_content_for_categories(self, content: str) -> List[str]:
        """从内容中分析类别"""
        # 简化实现 - 实际应使用NLP技术
        categories = []
        
        # 关键词到类别的映射
        keyword_mapping = {
            'work': ['work', 'job', 'career', 'professional'],
            'leisure': ['fun', 'entertainment', 'hobby', 'game', 'movie'],
            'health': ['health', 'fitness', 'exercise', 'diet', 'medical'],
            'technology': ['tech', 'computer', 'software', 'programming'],
            'science': ['science', 'research', 'experiment', 'discovery'],
            'personal': ['personal', 'family', 'friend', 'relationship']
        }
        
        content_lower = content.lower()
        for category, keywords in keyword_mapping.items():
            if any(keyword in content_lower for keyword in keywords):
                categories.append(category)
        
        return categories
    
    def _build_hierarchy(self, categories: List[str]) -> List[Dict[str, Any]]:
        """构建层次结构"""
        hierarchy = []
        
        for category in categories:
            # 查找父类别
            parent_category = self._find_parent_category(category)
            hierarchy_level = {
                'category': category,
                'level': self._get_category_level(category),
                'parent': parent_category
            }
            hierarchy.append(hierarchy_level)
        
        # 按层次排序
        hierarchy.sort(key=lambda x: x['level'])
        return hierarchy
    
    def _find_parent_category(self, category: str) -> Optional[str]:
        """查找父类别"""
        for parent, info in self.category_system.items():
            subcategories = info.get('subcategories', [])
            if category in subcategories:
                return parent
        return None
    
    def _get_category_level(self, category: str) -> int:
        """获取类别层次"""
        # 顶级类别
        if category in self.category_system:
            return 1
        
        # 子类别
        for parent, info in self.category_system.items():
            if category in info.get('subcategories', []):
                return 2
        
        return 3  # 未分类或低级类别
    
    def _classify_into_taxonomy(self, memory_item: Dict[str, Any]) -> List[str]:
        """分类到分类学系统"""
        categories = self._extract_categories(memory_item)
        validated_categories = []
        
        # 验证类别是否在分类系统中
        all_valid_categories = list(self.category_system.keys())
        for parent, info in self.category_system.items():
            all_valid_categories.extend(info.get('subcategories', []))
        
        for category in categories:
            if category in all_valid_categories:
                validated_categories.append(category)
        
        return validated_categories if validated_categories else ['uncategorized']
    
    def _extract_themes(self, memory_item: Dict[str, Any]) -> List[str]:
        """提取主题"""
        content = self._get_item_content(memory_item)
        if not content:
            return []
        
        # 简化主题提取
        themes = []
        
        # 基于情感的主题
        emotional_valence = memory_item.get('emotional_valence', 0)
        if emotional_valence > 0.3:
            themes.append('positive')
        elif emotional_valence < -0.3:
            themes.append('negative')
        
        # 基于重要性的主题
        importance = memory_item.get('importance', 0.5)
        if importance > 0.7:
            themes.append('important')
        elif importance < 0.3:
            themes.append('trivial')
        
        # 基于内容的主题
        content_themes = self._analyze_content_themes(content)
        themes.extend(content_themes)
        
        return list(set(themes))
    
    def _analyze_content_themes(self, content: str) -> List[str]:
        """分析内容主题"""
        # 简化实现
        themes = []
        
        theme_keywords = {
            'achievement': ['success', 'win', 'achieve', 'complete', 'accomplish'],
            'learning': ['learn', 'study', 'understand', 'discover', 'knowledge'],
            'problem': ['problem', 'issue', 'challenge', 'difficulty', 'trouble'],
            'celebration': ['celebrate', 'party', 'congratulations', 'achievement']
        }
        
        content_lower = content.lower()
        for theme, keywords in theme_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                themes.append(theme)
        
        return themes
    
    def _find_related_themes(self, themes: List[str]) -> List[str]:
        """查找相关主题"""
        related = []
        
        theme_relationships = {
            'achievement': ['success', 'celebration', 'accomplishment'],
            'learning': ['knowledge', 'education', 'growth'],
            'problem': ['challenge', 'solution', 'difficulty'],
            'positive': ['happy', 'joy', 'satisfaction']
        }
        
        for theme in themes:
            if theme in theme_relationships:
                related.extend(theme_relationships[theme])
        
        return list(set(related))
    
    def _build_theme_connections(self, primary_themes: List[str], related_themes: List[str]) -> Dict[str, List[str]]:
        """构建主题连接"""
        connections = {}
        
        for primary in primary_themes:
            connections[primary] = []
            for related in related_themes:
                # 简单的连接逻辑
                if primary != related:
                    connections[primary].append(related)
        
        return connections
    
    def _determine_time_period(self, timestamp) -> str:
        """确定时间段"""
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.datetime.fromisoformat(timestamp)
            except:
                return 'unknown'
        
        now = datetime.datetime.now()
        time_diff = now - timestamp
        
        if time_diff.days < 1:
            return 'today'
        elif time_diff.days < 7:
            return 'this_week'
        elif time_diff.days < 30:
            return 'this_month'
        elif time_diff.days < 365:
            return 'this_year'
        else:
            return 'long_ago'
    
    def _build_temporal_context(self, timestamp) -> Dict[str, Any]:
        """构建时间上下文"""
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.datetime.fromisoformat(timestamp)
            except:
                return {}
        
        return {
            'year': timestamp.year,
            'month': timestamp.month,
            'day': timestamp.day,
            'day_of_week': timestamp.strftime('%A'),
            'season': self._get_season(timestamp.month)
        }
    
    def _get_season(self, month: int) -> str:
        """获取季节"""
        if 3 <= month <= 5:
            return 'spring'
        elif 6 <= month <= 8:
            return 'summer'
        elif 9 <= month <= 11:
            return 'autumn'
        else:
            return 'winter'
    
    def _find_chronological_relationships(self, memory_item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """查找时间顺序关系"""
        # 简化实现 - 查找时间上接近的记忆
        relationships = []
        
        try:
            timestamp = memory_item.get('timestamp')
            if not timestamp:
                return relationships
            
            # 查找前后时间段的记忆
            if isinstance(timestamp, str):
                timestamp = datetime.datetime.fromisoformat(timestamp)
            
            time_window = datetime.timedelta(hours=24)
            start_time = timestamp - time_window
            end_time = timestamp + time_window
            
            related_events = self.episodic_memory.retrieve_events(
                start_time=start_time,
                end_time=end_time,
                limit=5
            )
            
            for event in related_events:
                if event.get('id') != memory_item.get('id'):
                    relationships.append({
                        'related_id': event.get('id'),
                        'relationship': 'temporal_proximity',
                        'time_difference': self._calculate_time_difference(timestamp, event.get('timestamp'))
                    })
        
        except Exception as e:
            self.logger.warning(f"查找时间关系失败: {e}")
        
        return relationships
    
    def _calculate_time_difference(self, time1, time2) -> str:
        """计算时间差"""
        if isinstance(time1, str):
            time1 = datetime.datetime.fromisoformat(time1)
        if isinstance(time2, str):
            time2 = datetime.datetime.fromisoformat(time2)
        
        diff = abs((time1 - time2).total_seconds())
        
        if diff < 3600:
            return f"{int(diff/60)}分钟"
        elif diff < 86400:
            return f"{int(diff/3600)}小时"
        else:
            return f"{int(diff/86400)}天"
    
    def _record_organization(self, 
                           memory_item: Dict[str, Any],
                           strategy: OrganizationStrategy,
                           result: Dict[str, Any]):
        """记录组织操作"""
        record = {
            'timestamp': datetime.datetime.now().isoformat(),
            'memory_id': memory_item.get('id'),
            'memory_type': memory_item.get('memory_type'),
            'strategy': strategy.value,
            'result': result,
            'categories_assigned': memory_item.get('organization', {}).get('categories', [])
        }
        
        self.organization_history.append(record)
        
        # 限制历史记录大小
        if len(self.organization_history) > 1000:
            self.organization_history = self.organization_history[-1000:]
    
    def get_organization_schema(self) -> Dict[str, Any]:
        """获取组织模式"""
        return {
            'category_system': self.category_system,
            'organization_strategies': [strategy.value for strategy in OrganizationStrategy],
            'configuration': {
                'auto_organize': self.auto_organize,
                'max_categories_per_item': self.max_categories_per_item
            }
        }
    
    def add_custom_category(self, 
                          category: str, 
                          parent: str = None,
                          description: str = "") -> bool:
        """
        添加自定义类别
        
        Args:
            category: 类别名称
            parent: 父类别
            description: 类别描述
            
        Returns:
            是否成功
        """
        try:
            if parent and parent in self.category_system:
                if 'subcategories' not in self.category_system[parent]:
                    self.category_system[parent]['subcategories'] = []
                self.category_system[parent]['subcategories'].append(category)
            else:
                self.category_system[category] = {
                    'description': description,
                    'subcategories': []
                }
            
            self.logger.info(f"添加自定义类别: {category}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加自定义类别失败: {e}")
            return False
    
    def analyze_organization_patterns(self) -> Dict[str, Any]:
        """分析组织模式"""
        if not self.organization_history:
            return {"error": "无组织历史数据"}
        
        total_organized = len(self.organization_history)
        
        # 策略使用统计
        strategy_usage = {}
        for record in self.organization_history:
            strategy = record.get('strategy', 'unknown')
            strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
        
        # 类别使用统计
        category_usage = {}
        for record in self.organization_history:
            categories = record.get('categories_assigned', [])
            for category in categories:
                category_usage[category] = category_usage.get(category, 0) + 1
        
        # 成功率统计
        success_count = sum(1 for record in self.organization_history 
                          if record.get('result', {}).get('success', False))
        success_rate = success_count / total_organized if total_organized > 0 else 0
        
        return {
            "total_organization_operations": total_organized,
            "success_rate": success_rate,
            "strategy_usage": strategy_usage,
            "category_usage": category_usage,
            "most_used_categories": sorted(category_usage.items(), key=lambda x: x[1], reverse=True)[:10]
        }

