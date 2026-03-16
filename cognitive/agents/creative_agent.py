"""
创意智能体模块：处理创意相关任务
实现基于生成式AI的创意内容生成系统
"""

import uuid
import datetime
import json
from typing import List, Dict, Any, Optional, Tuple
import logging
import asyncio
from enum import Enum

class CreativeDomain(Enum):
    WRITING = "writing"  # 写作
    DESIGN = "design"    # 设计
    MUSIC = "music"      # 音乐
    ART = "art"          # 艺术
    MARKETING = "marketing"  # 营销

class CreativeStyle(Enum):
    PROFESSIONAL = "professional"
    CREATIVE = "creative" 
    FORMAL = "formal"
    CASUAL = "casual"
    PERSUASIVE = "persuasive"

class CreativeAgent:
    """创意智能体 - 处理创意相关任务"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # 智能体身份
        self.agent_id = self.config.get('agent_id', f"creative_agent_{uuid.uuid4().hex[:8]}")
        self.agent_type = "creative"
        
        # 创意能力配置
        self.supported_domains = self.config.get('supported_domains', [domain.value for domain in CreativeDomain])
        self.creative_styles = self.config.get('creative_styles', [style.value for style in CreativeStyle])
        self.quality_level = self.config.get('quality_level', 0.8)  # 创意质量水平
        
        # 模型配置
        self.llm_provider = self.config.get('llm_provider', 'openai')
        self.llm_config = self.config.get('llm_config', {})
        self.creativity_temperature = self.config.get('creativity_temperature', 0.9)
        
        # 内容模板
        self.content_templates = self._load_content_templates()
        self.style_guides = self._load_style_guides()
        
        # 工作状态
        self.current_tasks = set()
        self.creative_history = []
        self.performance_metrics = {
            'tasks_completed': 0,
            'content_generated': 0,
            'average_quality_score': 0,
            'domain_expertise': {domain: 0.5 for domain in self.supported_domains}
        }
        
        # 初始化创意模型
        self._initialize_creative_models()
        
        self.initialized = True
        self.logger.info(f"创意智能体初始化成功: {self.agent_id}")
    
    def _load_content_templates(self) -> Dict[str, Any]:
        """加载内容模板"""
        return {
            'article': {
                'structure': ['标题', '引言', '主体', '结论'],
                'length_ranges': {'short': 300, 'medium': 800, 'long': 2000}
            },
            'social_media': {
                'platforms': ['twitter', 'facebook', 'instagram', 'linkedin'],
                'character_limits': {'twitter': 280, 'facebook': 5000, 'instagram': 2200, 'linkedin': 3000}
            },
            'marketing_copy': {
                'types': ['广告文案', '产品描述', '品牌故事', '号召性用语'],
                'persuasion_techniques': ['情感诉求', '逻辑论证', '社会证明', '稀缺性']
            },
            'creative_writing': {
                'genres': ['小说', '诗歌', '剧本', '散文'],
                'elements': ['情节', '角色', '场景', '对话']
            }
        }
    
    def _load_style_guides(self) -> Dict[str, Any]:
        """加载风格指南"""
        return {
            'professional': {
                'tone': '正式、专业',
                'vocabulary': '行业术语、精确表达',
                'structure': '逻辑清晰、层次分明'
            },
            'creative': {
                'tone': '生动、富有想象力', 
                'vocabulary': '比喻、象征、创新词汇',
                'structure': '灵活多变、突破常规'
            },
            'formal': {
                'tone': '庄重、礼貌',
                'vocabulary': '标准用语、避免口语',
                'structure': '规范格式、完整结构'
            },
            'casual': {
                'tone': '轻松、友好',
                'vocabulary': '日常用语、简洁明了', 
                'structure': '随意自然、重点突出'
            },
            'persuasive': {
                'tone': '有说服力、引人注目',
                'vocabulary': '强烈词汇、行动导向',
                'structure': '问题-解决方案、价值主张'
            }
        }
    
    def _initialize_creative_models(self):
        """初始化创意模型"""
        try:
            # 在实际系统中，这里会加载预训练的创意模型
            # 使用配置的LLM提供商
            
            if self.llm_provider == 'openai':
                # 初始化OpenAI客户端
                import openai
                api_key = self.llm_config.get('api_key')
                if api_key:
                    openai.api_key = api_key
                self.llm_client = openai
                
            elif self.llm_provider == 'huggingface':
                # 初始化HuggingFace模型
                from transformers import pipeline
                model_name = self.llm_config.get('model_name', 'gpt2')
                self.creative_generator = pipeline('text-generation', model=model_name)
                
            elif self.llm_provider == 'local':
                # 本地模型初始化
                model_path = self.llm_config.get('model_path')
                self.logger.info(f"加载本地创意模型: {model_path}")
                
            else:
                self.logger.warning(f"不支持的LLM提供商: {self.llm_provider}")
                self.llm_client = None
            
            self.logger.info("创意模型初始化完成")
            
        except Exception as e:
            self.logger.error(f"创意模型初始化失败: {e}")
            self.llm_client = None
    
    async def generate_content(self,
                            task_id: str,
                            content_type: str,
                            topic: str,
                            requirements: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        生成创意内容
        
        Args:
            task_id: 任务ID
            content_type: 内容类型
            topic: 主题
            requirements: 具体要求
            
        Returns:
            生成结果
        """
        requirements = requirements or {}
        
        try:
            self.current_tasks.add(task_id)
            
            # 分析需求
            analyzed_requirements = self._analyze_requirements(content_type, topic, requirements)
            
            # 生成内容大纲
            outline = await self._create_content_outline(analyzed_requirements)
            
            # 生成完整内容
            content = await self._generate_full_content(outline, analyzed_requirements)
            
            # 质量评估和优化
            optimized_content = await self._optimize_content(content, analyzed_requirements)
            
            # 记录创意历史
            creative_record = {
                'task_id': task_id,
                'timestamp': datetime.datetime.now().isoformat(),
                'content_type': content_type,
                'topic': topic,
                'requirements': requirements,
                'generated_content': optimized_content,
                'quality_score': self._evaluate_content_quality(optimized_content, analyzed_requirements)
            }
            self.creative_history.append(creative_record)
            
            # 更新性能指标
            self._update_performance_metrics(creative_record)
            
            self.current_tasks.remove(task_id)
            
            return {
                'success': True,
                'task_id': task_id,
                'content': optimized_content,
                'quality_score': creative_record['quality_score'],
                'generation_time': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"内容生成失败: {e}")
            self.current_tasks.remove(task_id)
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e)
            }
    
    def _analyze_requirements(self, content_type: str, topic: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """分析需求"""
        analyzed = {
            'content_type': content_type,
            'topic': topic,
            'style': requirements.get('style', 'creative'),
            'tone': requirements.get('tone', 'professional'),
            'length': requirements.get('length', 'medium'),
            'target_audience': requirements.get('target_audience', 'general'),
            'keywords': requirements.get('keywords', []),
            'exclude_topics': requirements.get('exclude_topics', []),
            'domain': self._identify_domain(content_type, topic)
        }
        
        # 验证风格支持
        if analyzed['style'] not in self.creative_styles:
            analyzed['style'] = 'creative'
            self.logger.warning(f"不支持的风格: {requirements['style']}, 使用默认风格: creative")
        
        # 确定内容长度
        if content_type in self.content_templates and 'length_ranges' in self.content_templates[content_type]:
            length_ranges = self.content_templates[content_type]['length_ranges']
            analyzed['target_length'] = length_ranges.get(analyzed['length'], length_ranges['medium'])
        else:
            analyzed['target_length'] = 500  # 默认长度
        
        return analyzed
    
    def _identify_domain(self, content_type: str, topic: str) -> str:
        """识别内容领域"""
        domain_keywords = {
            'writing': ['文章', '博客', '故事', '文案', '写作'],
            'design': ['设计', '视觉', '图形', 'UI', 'UX'],
            'music': ['音乐', '歌曲', '旋律', '节奏', '作曲'],
            'art': ['艺术', '绘画', '创作', '美学', '视觉'],
            'marketing': ['营销', '广告', '推广', '品牌', '销售']
        }
        
        # 基于内容类型和主题关键词识别领域
        content_text = f"{content_type} {topic}".lower()
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in content_text for keyword in keywords):
                return domain
        
        return 'writing'  # 默认领域
    
    async def _create_content_outline(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """创建内容大纲"""
        try:
            prompt = self._build_outline_prompt(requirements)
            outline_response = await self._call_creative_model(prompt, max_tokens=500)
            
            # 解析大纲
            outline = self._parse_outline_response(outline_response, requirements)
            return outline
            
        except Exception as e:
            self.logger.error(f"创建大纲失败: {e}")
            # 返回默认大纲
            return self._create_default_outline(requirements)
    
    def _build_outline_prompt(self, requirements: Dict[str, Any]) -> str:
        """构建大纲生成提示"""
        template = self.content_templates.get(requirements['content_type'], {})
        style_guide = self.style_guides.get(requirements['style'], {})
        
        prompt = f"""
        请为以下内容创建详细大纲：
        
        内容类型：{requirements['content_type']}
        主题：{requirements['topic']}
        风格：{requirements['style']} - {style_guide.get('tone', '')}
        目标受众：{requirements['target_audience']}
        目标长度：{requirements['target_length']}字
        关键词：{', '.join(requirements['keywords'])}
        
        请按照以下结构创建大纲：
        {template.get('structure', ['引言', '主体', '结论'])}
        
        要求：
        - 逻辑清晰，层次分明
        - 符合{requirements['style']}风格
        - 包含具体的内容要点
        - 确保内容完整性和连贯性
        
        请以JSON格式返回大纲，包含标题和主要部分。
        """
        
        return prompt
    
    async def _call_creative_model(self, prompt: str, max_tokens: int = 1000) -> str:
        """调用创意模型"""
        try:
            if self.llm_provider == 'openai' and self.llm_client:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.llm_client.ChatCompletion.create(
                        model=self.llm_config.get('model', 'gpt-3.5-turbo'),
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=self.creativity_temperature
                    )
                )
                return response.choices[0].message.content
                
            elif self.llm_provider == 'huggingface' and hasattr(self, 'creative_generator'):
                response = self.creative_generator(
                    prompt,
                    max_length=max_tokens,
                    temperature=self.creativity_temperature,
                    do_sample=True
                )
                return response[0]['generated_text']
                
            else:
                # 模拟响应
                return self._generate_mock_response(prompt)
                
        except Exception as e:
            self.logger.error(f"调用创意模型失败: {e}")
            return self._generate_mock_response(prompt)
    
    def _generate_mock_response(self, prompt: str) -> str:
        """生成模拟响应（备用）"""
        # 基于提示生成简单的模拟内容
        if "大纲" in prompt:
            return json.dumps({
                "title": "模拟创意内容标题",
                "sections": [
                    {"title": "引言", "content": "介绍主题背景和重要性"},
                    {"title": "主体", "content": "详细展开论述，包含关键论点"},
                    {"title": "结论", "content": "总结要点，提出展望"}
                ]
            }, ensure_ascii=False)
        else:
            return "这是模拟生成的创意内容。在实际系统中，这里会调用真实的AI模型来生成高质量的内容。"
    
    def _parse_outline_response(self, response: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """解析大纲响应"""
        try:
            # 尝试解析JSON响应
            outline_data = json.loads(response)
            return outline_data
        except json.JSONDecodeError:
            # 如果响应不是JSON，创建结构化大纲
            self.logger.warning("大纲响应不是有效的JSON，进行结构化处理")
            return self._structure_text_outline(response, requirements)
    
    def _structure_text_outline(self, text: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """将文本响应结构化为大纲"""
        lines = text.split('\n')
        sections = []
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检测章节标题
            if any(marker in line for marker in ['#', '标题', '章节', '部分']):
                if current_section:
                    sections.append(current_section)
                current_section = {'title': line, 'points': []}
            elif current_section and line:
                current_section['points'].append(line)
        
        if current_section:
            sections.append(current_section)
        
        return {
            'title': f"{requirements['topic']} - 创意内容",
            'sections': sections
        }
    
    def _create_default_outline(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """创建默认大纲"""
        template = self.content_templates.get(requirements['content_type'], {})
        default_structure = template.get('structure', ['引言', '主体', '结论'])
        
        sections = []
        for section_name in default_structure:
            sections.append({
                'title': section_name,
                'points': [f"{section_name}部分的关键内容点"]
            })
        
        return {
            'title': requirements['topic'],
            'sections': sections
        }
    
    async def _generate_full_content(self, outline: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """生成完整内容"""
        full_content = {}
        
        for section in outline.get('sections', []):
            section_title = section['title']
            section_prompt = self._build_section_prompt(section, requirements)
            
            section_content = await self._call_creative_model(section_prompt, max_tokens=800)
            full_content[section_title] = {
                'content': section_content,
                'points': section.get('points', [])
            }
        
        return {
            'title': outline.get('title', '未命名内容'),
            'outline': outline,
            'sections': full_content,
            'metadata': {
                'content_type': requirements['content_type'],
                'style': requirements['style'],
                'generated_at': datetime.datetime.now().isoformat()
            }
        }
    
    def _build_section_prompt(self, section: Dict[str, Any], requirements: Dict[str, Any]) -> str:
        """构建章节内容生成提示"""
        style_guide = self.style_guides.get(requirements['style'], {})
        
        prompt = f"""
        请撰写以下章节的详细内容：
        
        章节标题：{section['title']}
        主要内容点：{', '.join(section.get('points', []))}
        
        整体主题：{requirements['topic']}
        写作风格：{requirements['style']}
        - 语气：{style_guide.get('tone', '专业')}
        - 词汇：{style_guide.get('vocabulary', '标准')}
        - 结构：{style_guide.get('structure', '清晰')}
        
        目标受众：{requirements['target_audience']}
        关键词：{', '.join(requirements['keywords'])}
        
        要求：
        - 内容充实，论述清晰
        - 符合整体风格要求
        - 自然融入关键词
        - 保持段落连贯性
        - 字数约{requirements['target_length'] // len(requirements.get('sections', 3))}字
        
        请直接返回章节内容，不需要额外的格式说明。
        """
        
        return prompt
    
    async def _optimize_content(self, content: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """优化内容质量"""
        try:
            # 内容质量检查
            quality_issues = self._check_content_quality(content, requirements)
            
            if quality_issues:
                # 进行内容优化
                optimized_sections = {}
                for section_title, section_data in content['sections'].items():
                    optimized_content = await self._optimize_section_content(
                        section_data['content'], section_title, requirements, quality_issues
                    )
                    optimized_sections[section_title] = {
                        'content': optimized_content,
                        'points': section_data['points']
                    }
                
                content['sections'] = optimized_sections
                content['metadata']['optimized'] = True
                content['metadata']['optimized_at'] = datetime.datetime.now().isoformat()
            
            return content
            
        except Exception as e:
            self.logger.error(f"内容优化失败: {e}")
            return content
    
    def _check_content_quality(self, content: Dict[str, Any], requirements: Dict[str, Any]) -> List[str]:
        """检查内容质量问题"""
        issues = []
        
        # 检查内容完整性
        total_content = ""
        for section_data in content['sections'].values():
            total_content += section_data['content']
        
        # 长度检查
        content_length = len(total_content)
        target_length = requirements['target_length']
        length_tolerance = 0.2  # 20%容差
        
        if abs(content_length - target_length) > target_length * length_tolerance:
            issues.append(f"内容长度不符: 当前{content_length}字, 目标{target_length}字")
        
        # 关键词覆盖检查
        keywords = requirements.get('keywords', [])
        if keywords:
            missing_keywords = []
            for keyword in keywords:
                if keyword not in total_content:
                    missing_keywords.append(keyword)
            
            if missing_keywords:
                issues.append(f"缺失关键词: {', '.join(missing_keywords)}")
        
        # 风格一致性检查
        style_guide = self.style_guides.get(requirements['style'], {})
        # 这里可以添加更复杂的风格检查逻辑
        
        return issues
    
    async def _optimize_section_content(self, content: str, section_title: str, requirements: Dict[str, Any], issues: List[str]) -> str:
        """优化章节内容"""
        optimization_prompt = f"""
        请优化以下内容：
        
        章节：{section_title}
        原内容：{content}
        
        需要解决的问题：
        {chr(10).join(f'- {issue}' for issue in issues)}
        
        优化要求：
        - 保持原意不变
        - 解决上述质量问题
        - 符合{requirements['style']}风格
        - 提高内容质量和可读性
        
        请直接返回优化后的内容。
        """
        
        optimized_content = await self._call_creative_model(optimization_prompt, max_tokens=1000)
        return optimized_content
    
    def _evaluate_content_quality(self, content: Dict[str, Any], requirements: Dict[str, Any]) -> float:
        """评估内容质量"""
        quality_score = 0.0
        factors = []
        
        # 内容完整性
        total_content = ""
        for section_data in content['sections'].values():
            total_content += section_data.get('content', '')
        
        content_length = len(total_content)
        target_length = requirements['target_length']
        length_score = 1.0 - min(1.0, abs(content_length - target_length) / target_length)
        factors.append(('长度匹配', length_score, 0.2))
        
        # 关键词覆盖
        keywords = requirements.get('keywords', [])
        if keywords:
            keyword_coverage = sum(1 for keyword in keywords if keyword in total_content) / len(keywords)
            factors.append(('关键词覆盖', keyword_coverage, 0.3))
        else:
            factors.append(('关键词覆盖', 1.0, 0.3))
        
        # 结构完整性
        outline = content.get('outline', {})
        expected_sections = len(outline.get('sections', []))
        actual_sections = len(content.get('sections', {}))
        structure_score = actual_sections / expected_sections if expected_sections > 0 else 1.0
        factors.append(('结构完整', structure_score, 0.3))
        
        # 基础质量分
        factors.append(('基础质量', self.quality_level, 0.2))
        
        # 计算加权总分
        for factor, score, weight in factors:
            quality_score += score * weight
        
        return min(1.0, quality_score)
    
    def _update_performance_metrics(self, creative_record: Dict[str, Any]):
        """更新性能指标"""
        self.performance_metrics['tasks_completed'] += 1
        self.performance_metrics['content_generated'] += 1
        
        # 更新平均质量分
        current_avg = self.performance_metrics['average_quality_score']
        new_score = creative_record['quality_score']
        total_tasks = self.performance_metrics['tasks_completed']
        
        self.performance_metrics['average_quality_score'] = (
            (current_avg * (total_tasks - 1) + new_score) / total_tasks
        )
        
        # 更新领域专长
        domain = creative_record.get('requirements', {}).get('domain', 'writing')
        if domain in self.performance_metrics['domain_expertise']:
            current_expertise = self.performance_metrics['domain_expertise'][domain]
            # 基于任务质量提升专长评分
            new_expertise = min(1.0, current_expertise + (new_score * 0.1))
            self.performance_metrics['domain_expertise'][domain] = new_expertise
    
    def get_capabilities(self) -> List[str]:
        """获取能力列表"""
        capabilities = [
            'content_generation',
            'creative_writing', 
            'copywriting',
            'content_optimization',
            'idea_generation'
        ]
        
        # 添加支持的领域能力
        for domain in self.supported_domains:
            capabilities.append(f"{domain}_content")
        
        return capabilities
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            **self.performance_metrics,
            'current_tasks': list(self.current_tasks),
            'supported_domains': self.supported_domains,
            'creative_styles': self.creative_styles
        }
    
    def get_creative_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取创意历史"""
        return self.creative_history[-limit:] if limit else self.creative_history

