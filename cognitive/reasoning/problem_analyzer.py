"""
问题分析器 - 分析问题本质和需求
深度理解用户问题的核心要素
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import jieba
import jieba.posseg as pseg

logger = logging.getLogger(__name__)

class ProblemType(Enum):
    """问题类型枚举"""
    FACTUAL_QUERY = "factual_query"  # 事实查询
    HOW_TO_GUIDE = "how_to_guide"    # 操作指南
    PROBLEM_SOLVING = "problem_solving"  # 问题解决
    CREATIVE_REQUEST = "creative_request"  # 创意请求
    ANALYSIS_REQUIRED = "analysis_required"  # 分析需求
    COMPARISON = "comparison"  # 比较分析

class ComplexityLevel(Enum):
    """复杂度级别"""
    SIMPLE = "simple"  # 简单
    MODERATE = "moderate"  # 中等
    COMPLEX = "complex"  # 复杂
    VERY_COMPLEX = "very_complex"  # 非常复杂

@dataclass
class ProblemAnalysis:
    """问题分析结果"""
    original_problem: str
    problem_type: ProblemType
    complexity: ComplexityLevel
    key_entities: List[str]  # 关键实体
    key_actions: List[str]  # 关键动作
    constraints: List[str]  # 约束条件
    goals: List[str]  # 目标
    assumptions: List[str]  # 假设
    context_elements: Dict[str, Any]  # 上下文元素
    suggested_approach: str  # 建议方法

class ProblemAnalyzer:
    """问题分析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.initialize_nlp_components()
        self.problem_patterns = self._load_problem_patterns()
        self.domain_knowledge = self._load_domain_knowledge()
        
    def initialize_nlp_components(self):
        """初始化NLP组件"""
        # 初始化中文分词
        jieba.initialize()
        
        # 加载专业词典
        self._load_technical_terms()
        
    def _load_technical_terms(self):
        """加载技术术语"""
        technical_terms = [
            '人工智能', '机器学习', '深度学习', '神经网络', '自然语言处理',
            '计算机视觉', '数据挖掘', '大数据', '云计算', '物联网',
            '区块链', '元宇宙', '数字化转型', '智能化', '自动化'
        ]
        
        for term in technical_terms:
            jieba.add_word(term)
    
    def _load_problem_patterns(self) -> Dict[str, Any]:
        """加载问题模式"""
        return {
            "factual_query": {
                "patterns": [
                    r"(什么是|什么是|解释|定义).+",
                    r".+的(意思|含义|定义)是什么",
                    r"谁发明了.+",
                    r".+是什么时候"
                ],
                "keywords": ["什么", "谁", "何时", "哪里", "定义", "解释"]
            },
            "how_to_guide": {
                "patterns": [
                    r"如何(.+)",
                    r"怎样(.+)",
                    r"怎么(.+)",
                    r"步骤|方法|教程"
                ],
                "keywords": ["如何", "怎样", "怎么", "步骤", "方法"]
            },
            "problem_solving": {
                "patterns": [
                    r"解决(.+)问题",
                    r"处理(.+)错误",
                    r"修复(.+)故障",
                    r"调试(.+)"
                ],
                "keywords": ["解决", "处理", "修复", "调试", "故障", "错误"]
            },
            "creative_request": {
                "patterns": [
                    r"创作(.+)",
                    r"写一(.+)",
                    r"生成(.+)",
                    r"设计(.+)"
                ],
                "keywords": ["创作", "写", "生成", "设计", "制作"]
            }
        }
    
    def _load_domain_knowledge(self) -> Dict[str, List[str]]:
        """加载领域知识"""
        return {
            "technology": [
                "编程", "开发", "代码", "算法", "系统", "网络", "安全",
                "数据库", "前端", "后端", "移动开发", "网页开发"
            ],
            "business": [
                "营销", "销售", "管理", "战略", "财务", "人力资源", "运营",
                "客户", "市场", "产品", "服务", "品牌"
            ],
            "creative": [
                "写作", "设计", "艺术", "音乐", "视频", "图片", "内容",
                "故事", "剧本", "诗歌", "创意"
            ],
            "academic": [
                "研究", "论文", "学习", "教育", "科学", "数学", "物理",
                "化学", "生物", "历史", "文学"
            ]
        }
    
    def analyze_problem(self, problem_text: str, context: Dict[str, Any] = None) -> ProblemAnalysis:
        """
        分析问题
        
        Args:
            problem_text: 问题文本
            context: 上下文信息
            
        Returns:
            ProblemAnalysis: 问题分析结果
        """
        self.logger.info(f"开始分析问题: {problem_text}")
        
        if context is None:
            context = {}
        
        # 1. 问题分类
        problem_type = self._classify_problem(problem_text)
        
        # 2. 复杂度评估
        complexity = self._assess_complexity(problem_text, context)
        
        # 3. 关键信息提取
        key_entities = self._extract_entities(problem_text)
        key_actions = self._extract_actions(problem_text)
        
        # 4. 约束和目标识别
        constraints = self._identify_constraints(problem_text, context)
        goals = self._identify_goals(problem_text)
        
        # 5. 假设识别
        assumptions = self._identify_assumptions(problem_text, context)
        
        # 6. 上下文分析
        context_elements = self._analyze_context(problem_text, context)
        
        # 7. 生成建议方法
        suggested_approach = self._suggest_approach(problem_type, complexity, key_actions, context)
        
        analysis = ProblemAnalysis(
            original_problem=problem_text,
            problem_type=problem_type,
            complexity=complexity,
            key_entities=key_entities,
            key_actions=key_actions,
            constraints=constraints,
            goals=goals,
            assumptions=assumptions,
            context_elements=context_elements,
            suggested_approach=suggested_approach
        )
        
        self.logger.info(f"问题分析完成，类型: {problem_type.value}, 复杂度: {complexity.value}")
        return analysis
    
    def _classify_problem(self, problem_text: str) -> ProblemType:
        """分类问题类型"""
        problem_lower = problem_text.lower()
        
        for problem_type, pattern_info in self.problem_patterns.items():
            # 检查模式匹配
            for pattern in pattern_info["patterns"]:
                if re.search(pattern, problem_lower):
                    if problem_type == "factual_query":
                        return ProblemType.FACTUAL_QUERY
                    elif problem_type == "how_to_guide":
                        return ProblemType.HOW_TO_GUIDE
                    elif problem_type == "problem_solving":
                        return ProblemType.PROBLEM_SOLVING
                    elif problem_type == "creative_request":
                        return ProblemType.CREATIVE_REQUEST
            
            # 检查关键词匹配
            for keyword in pattern_info["keywords"]:
                if keyword in problem_lower:
                    if problem_type == "factual_query":
                        return ProblemType.FACTUAL_QUERY
                    elif problem_type == "how_to_guide":
                        return ProblemType.HOW_TO_GUIDE
                    elif problem_type == "problem_solving":
                        return ProblemType.PROBLEM_SOLVING
                    elif problem_type == "creative_request":
                        return ProblemType.CREATIVE_REQUEST
        
        # 默认分类为分析需求
        return ProblemType.ANALYSIS_REQUIRED
    
    def _assess_complexity(self, problem_text: str, context: Dict[str, Any]) -> ComplexityLevel:
        """评估问题复杂度"""
        complexity_score = 0
        
        # 基于文本长度
        text_length = len(problem_text)
        if text_length < 20:
            complexity_score += 1
        elif text_length < 50:
            complexity_score += 2
        else:
            complexity_score += 3
        
        # 基于句子数量（简单统计句号）
        sentence_count = problem_text.count('。') + problem_text.count('！') + problem_text.count('？')
        complexity_score += min(sentence_count, 3)
        
        # 基于技术术语数量
        technical_terms_count = self._count_technical_terms(problem_text)
        complexity_score += min(technical_terms_count, 3)
        
        # 基于上下文复杂度
        if context.get("has_multiple_requirements", False):
            complexity_score += 2
        if context.get("requires_integration", False):
            complexity_score += 2
        
        # 转换为复杂度级别
        if complexity_score <= 3:
            return ComplexityLevel.SIMPLE
        elif complexity_score <= 6:
            return ComplexityLevel.MODERATE
        elif complexity_score <= 9:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.VERY_COMPLEX
    
    def _count_technical_terms(self, text: str) -> int:
        """统计技术术语数量"""
        count = 0
        words = jieba.lcut(text)
        
        # 检查每个领域的技术术语
        for domain, terms in self.domain_knowledge.items():
            for term in terms:
                if term in text:
                    count += 1
        
        return count
    
    def _extract_entities(self, text: str) -> List[str]:
        """提取关键实体"""
        entities = []
        
        # 使用分词和词性标注
        words = pseg.cut(text)
        
        for word, flag in words:
            # 提取名词性成分
            if flag.startswith('n') or flag in ['vn', 'an']:
                if len(word) > 1:  # 过滤单字
                    entities.append(word)
            
            # 提取专有名词
            elif flag in ['nr', 'ns', 'nt', 'nz']:
                entities.append(word)
        
        # 去重
        return list(set(entities))
    
    def _extract_actions(self, text: str) -> List[str]:
        """提取关键动作"""
        actions = []
        
        # 使用分词和词性标注
        words = pseg.cut(text)
        
        for word, flag in words:
            # 提取动词性成分
            if flag.startswith('v'):
                actions.append(word)
        
        # 去重并返回
        return list(set(actions))
    
    def _identify_constraints(self, text: str, context: Dict[str, Any]) -> List[str]:
        """识别约束条件"""
        constraints = []
        
        # 时间约束
        time_patterns = [
            r"在(.{1,10})内",
            r"截止到(.{1,10})",
            r"在(.{1,10})之前",
            r"时间限制",
            r"期限"
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                constraints.append(f"时间约束: {match}")
        
        # 资源约束
        resource_patterns = [
            r"使用(.{1,10})资源",
            r"在(.{1,10})环境下",
            r"预算(.{1,10})",
            r"内存限制",
            r"存储空间"
        ]
        
        for pattern in resource_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                constraints.append(f"资源约束: {match}")
        
        # 质量约束
        quality_patterns = [
            r"高质量",
            r"精确",
            r"准确率",
            r"可靠性",
            r"稳定性"
        ]
        
        for pattern in quality_patterns:
            if pattern in text:
                constraints.append(f"质量约束: {pattern}")
        
        # 从上下文中提取约束
        if "constraints" in context:
            constraints.extend(context["constraints"])
        
        return constraints
    
    def _identify_goals(self, text: str) -> List[str]:
        """识别目标"""
        goals = []
        
        # 明确的目标表述
        goal_patterns = [
            r"目标是(.+)",
            r"想要(.+)",
            r"需要(.+)",
            r"希望(.+)",
            r"目的是(.+)"
        ]
        
        for pattern in goal_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                goals.append(match.strip())
        
        # 如果没有明确目标，从问题中推断
        if not goals:
            # 根据问题类型推断目标
            problem_type = self._classify_problem(text)
            if problem_type == ProblemType.FACTUAL_QUERY:
                goals.append("获取准确信息")
            elif problem_type == ProblemType.HOW_TO_GUIDE:
                goals.append("学习操作方法")
            elif problem_type == ProblemType.PROBLEM_SOLVING:
                goals.append("解决问题")
            elif problem_type == ProblemType.CREATIVE_REQUEST:
                goals.append("生成创意内容")
        
        return goals
    
    def _identify_assumptions(self, text: str, context: Dict[str, Any]) -> List[str]:
        """识别假设"""
        assumptions = []
        
        # 从问题中提取假设
        assumption_indicators = [
            "假设", "如果", "假如", "要是", "既然", "因为"
        ]
        
        sentences = re.split(r'[。！？]', text)
        for sentence in sentences:
            for indicator in assumption_indicators:
                if indicator in sentence:
                    assumptions.append(sentence.strip())
                    break
        
        # 从上下文中提取假设
        if "assumptions" in context:
            assumptions.extend(context["assumptions"])
        
        return assumptions
    
    def _analyze_context(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析上下文"""
        context_elements = {}
        
        # 领域分析
        domain = self._identify_domain(text)
        context_elements["domain"] = domain
        
        # 技术栈分析
        tech_stack = self._identify_tech_stack(text)
        context_elements["tech_stack"] = tech_stack
        
        # 用户背景分析
        user_background = self._infer_user_background(text)
        context_elements["user_background"] = user_background
        
        # 合并传入的上下文
        context_elements.update(context)
        
        return context_elements
    
    def _identify_domain(self, text: str) -> str:
        """识别问题领域"""
        domain_scores = {}
        
        for domain, keywords in self.domain_knowledge.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            domain_scores[domain] = score
        
        # 返回得分最高的领域
        if domain_scores:
            return max(domain_scores.items(), key=lambda x: x[1])[0]
        else:
            return "general"
    
    def _identify_tech_stack(self, text: str) -> List[str]:
        """识别技术栈"""
        tech_keywords = {
            "Python": ["python", "py", "pytorch", "tensorflow"],
            "Java": ["java", "spring", "hibernate"],
            "JavaScript": ["javascript", "js", "node", "react", "vue"],
            "Database": ["mysql", "postgresql", "mongodb", "redis"],
            "Cloud": ["aws", "azure", "gcp", "cloud", "云"]
        }
        
        identified_tech = []
        text_lower = text.lower()
        
        for tech, keywords in tech_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    identified_tech.append(tech)
                    break
        
        return identified_tech
    
    def _infer_user_background(self, text: str) -> str:
        """推断用户背景"""
        # 基于问题复杂度和术语使用推断
        complexity = self._assess_complexity(text, {})
        technical_terms_count = self._count_technical_terms(text)
        
        if technical_terms_count >= 3 and complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX]:
            return "expert"
        elif technical_terms_count >= 1:
            return "intermediate"
        else:
            return "beginner"
    
    def _suggest_approach(self, problem_type: ProblemType, complexity: ComplexityLevel, 
                         key_actions: List[str], context: Dict[str, Any]) -> str:
        """生成建议方法"""
        approaches = {
            ProblemType.FACTUAL_QUERY: {
                ComplexityLevel.SIMPLE: "直接查询知识库获取准确答案",
                ComplexityLevel.MODERATE: "综合多个信息源进行验证",
                ComplexityLevel.COMPLEX: "深度研究并对比不同观点",
                ComplexityLevel.VERY_COMPLEX: "系统性的文献调研和分析"
            },
            ProblemType.HOW_TO_GUIDE: {
                ComplexityLevel.SIMPLE: "提供清晰的操作步骤说明",
                ComplexityLevel.MODERATE: "分步骤演示并提供示例",
                ComplexityLevel.COMPLEX: "详细教程包含原理说明和最佳实践",
                ComplexityLevel.VERY_COMPLEX: "完整的培训材料包含实践项目"
            },
            ProblemType.PROBLEM_SOLVING: {
                ComplexityLevel.SIMPLE: "快速诊断并提供解决方案",
                ComplexityLevel.MODERATE: "系统分析问题根源并提供多种解决方案",
                ComplexityLevel.COMPLEX: "深度技术分析和定制化解决方案",
                ComplexityLevel.VERY_COMPLEX: "多学科综合解决方案"
            },
            ProblemType.CREATIVE_REQUEST: {
                ComplexityLevel.SIMPLE: "基于模板快速生成内容",
                ComplexityLevel.MODERATE: "个性化创作考虑用户偏好",
                ComplexityLevel.COMPLEX: "创新性设计结合多种元素",
                ComplexityLevel.VERY_COMPLEX: "突破性创意实现和技术创新"
            }
        }
        
        default_approach = "系统性分析和分阶段执行"
        
        if problem_type in approaches and complexity in approaches[problem_type]:
            return approaches[problem_type][complexity]
        else:
            return default_approach
    
    def validate_analysis(self, analysis: ProblemAnalysis) -> Tuple[bool, List[str]]:
        """验证分析结果的合理性"""
        issues = []
        
        # 检查是否有明确的目标
        if not analysis.goals:
            issues.append("未能识别明确的目标")
        
        # 检查关键实体是否足够
        if len(analysis.key_entities) < 1:
            issues.append("识别到的关键实体过少")
        
        # 检查建议方法是否合理
        if not analysis.suggested_approach or len(analysis.suggested_approach) < 10:
            issues.append("建议方法不够具体")
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def compare_problems(self, problem1: str, problem2: str) -> float:
        """比较两个问题的相似度"""
        analysis1 = self.analyze_problem(problem1)
        analysis2 = self.analyze_problem(problem2)
        
        similarity_score = 0.0
        
        # 问题类型相似度
        if analysis1.problem_type == analysis2.problem_type:
            similarity_score += 0.3
        
        # 关键实体相似度
        common_entities = set(analysis1.key_entities) & set(analysis2.key_entities)
        entity_similarity = len(common_entities) / max(len(analysis1.key_entities), len(analysis2.key_entities), 1)
        similarity_score += entity_similarity * 0.4
        
        # 关键动作相似度
        common_actions = set(analysis1.key_actions) & set(analysis2.key_actions)
        action_similarity = len(common_actions) / max(len(analysis1.key_actions), len(analysis2.key_actions), 1)
        similarity_score += action_similarity * 0.3
        
        return min(similarity_score, 1.0)
