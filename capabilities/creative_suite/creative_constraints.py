"""
创意约束：创意内容约束条件管理
支持内容审查、合规检查、品牌指南执行等功能
"""

import os
import re
import logging
import json
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
from enum import Enum

import torch
from transformers import (
    pipeline,
    AutoTokenizer,
    AutoModelForSequenceClassification
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ConstraintType(Enum):
    """约束类型枚举"""
    CONTENT_SAFETY = "content_safety"
    BRAND_GUIDELINES = "brand_guidelines"
    LEGAL_COMPLIANCE = "legal_compliance"
    QUALITY_STANDARDS = "quality_standards"
    STYLE_GUIDE = "style_guide"
    ACCESSIBILITY = "accessibility"

class ConstraintSeverity(Enum):
    """约束严重程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ConstraintViolation(BaseModel):
    """约束违反记录"""
    constraint_type: ConstraintType
    severity: ConstraintSeverity
    message: str
    position: Optional[Tuple[int, int]] = None
    offending_text: Optional[str] = None
    suggestion: Optional[str] = None

class ConstraintCheckResult(BaseModel):
    """约束检查结果"""
    content: str
    violations: List[ConstraintViolation]
    passed: bool
    score: float  # 合规分数 0.0-1.0
    metadata: Dict[str, Any]

class BrandGuidelines(BaseModel):
    """品牌指南配置"""
    brand_name: str
    prohibited_terms: List[str]
    required_terms: List[str]
    tone_requirements: Dict[str, Any]
    style_preferences: Dict[str, Any]
    logo_usage_rules: Dict[str, Any]

class CreativeConstraints:
    """创意约束管理器"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.safety_classifier = None
        self.compliance_checker = None
        
        # 约束规则库
        self.constraint_rules = self._load_constraint_rules()
        
        # 品牌指南
        self.brand_guidelines: Dict[str, BrandGuidelines] = {}
        
        # 加载模型
        self._initialize_models()
        
        logger.info("CreativeConstraints initialized")
    
    def _load_constraint_rules(self) -> Dict[ConstraintType, List[Dict]]:
        """加载约束规则"""
        return {
            ConstraintType.CONTENT_SAFETY: [
                {
                    "pattern": r"(暴力|血腥|恐怖|极端)",
                    "severity": ConstraintSeverity.HIGH,
                    "message": "检测到不安全内容",
                    "suggestion": "移除或修改相关内容"
                },
                {
                    "pattern": r"(仇恨|歧视|侮辱)",
                    "severity": ConstraintSeverity.CRITICAL,
                    "message": "检测到仇恨言论",
                    "suggestion": "立即移除相关内容"
                }
            ],
            ConstraintType.LEGAL_COMPLIANCE: [
                {
                    "pattern": r"(版权|侵权|盗版)",
                    "severity": ConstraintSeverity.HIGH,
                    "message": "可能涉及版权问题",
                    "suggestion": "确保内容原创或获得授权"
                },
                {
                    "pattern": r"(诽谤|诋毁|污蔑)",
                    "severity": ConstraintSeverity.HIGH,
                    "message": "可能涉及诽谤内容",
                    "suggestion": "修改为客观表述"
                }
            ],
            ConstraintType.QUALITY_STANDARDS: [
                {
                    "pattern": r"。{3,}",
                    "severity": ConstraintSeverity.LOW,
                    "message": "过多重复标点",
                    "suggestion": "规范标点使用"
                },
                {
                    "condition": "readability_score < 0.3",
                    "severity": ConstraintSeverity.MEDIUM,
                    "message": "可读性过低",
                    "suggestion": "简化语言表达"
                }
            ]
        }
    
    def _initialize_models(self):
        """初始化模型"""
        try:
            # 加载内容安全分类器
            self.safety_classifier = pipeline(
                "text-classification",
                model="unitary/toxic-bert",
                device=0 if self.device == "cuda" else -1
            )
            
            logger.info("Creative constraint models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize constraint models: {e}")
    
    def add_brand_guidelines(self, guidelines: BrandGuidelines):
        """添加品牌指南"""
        self.brand_guidelines[guidelines.brand_name] = guidelines
        logger.info(f"Added brand guidelines for {guidelines.brand_name}")
    
    def remove_brand_guidelines(self, brand_name: str):
        """移除品牌指南"""
        if brand_name in self.brand_guidelines:
            del self.brand_guidelines[brand_name]
            logger.info(f"Removed brand guidelines for {brand_name}")
    
    def check_constraints(self, 
                         content: str,
                         brand_name: Optional[str] = None,
                         constraint_types: Optional[List[ConstraintType]] = None) -> ConstraintCheckResult:
        """
        检查内容约束
        
        Args:
            content: 要检查的内容
            brand_name: 品牌名称（用于品牌指南检查）
            constraint_types: 要检查的约束类型
            
        Returns:
            ConstraintCheckResult: 检查结果
        """
        try:
            if constraint_types is None:
                constraint_types = list(ConstraintType)
            
            violations = []
            
            # 按类型检查约束
            for constraint_type in constraint_types:
                type_violations = self._check_constraint_type(content, constraint_type, brand_name)
                violations.extend(type_violations)
            
            # 计算合规分数
            score = self._calculate_compliance_score(violations, len(content))
            
            return ConstraintCheckResult(
                content=content,
                violations=violations,
                passed=len(violations) == 0,
                score=score,
                metadata={
                    "checked_constraints": [ct.value for ct in constraint_types],
                    "brand_name": brand_name,
                    "checked_at": datetime.now().isoformat(),
                    "content_length": len(content)
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to check constraints: {e}")
            raise
    
    def _check_constraint_type(self, 
                             content: str, 
                             constraint_type: ConstraintType,
                             brand_name: Optional[str]) -> List[ConstraintViolation]:
        """检查特定类型的约束"""
        violations = []
        
        if constraint_type == ConstraintType.CONTENT_SAFETY:
            violations.extend(self._check_content_safety(content))
        
        elif constraint_type == ConstraintType.BRAND_GUIDELINES:
            if brand_name and brand_name in self.brand_guidelines:
                violations.extend(self._check_brand_guidelines(content, brand_name))
        
        elif constraint_type == ConstraintType.LEGAL_COMPLIANCE:
            violations.extend(self._check_legal_compliance(content))
        
        elif constraint_type == ConstraintType.QUALITY_STANDARDS:
            violations.extend(self._check_quality_standards(content))
        
        elif constraint_type == ConstraintType.STYLE_GUIDE:
            violations.extend(self._check_style_guide(content))
        
        elif constraint_type == ConstraintType.ACCESSIBILITY:
            violations.extend(self._check_accessibility(content))
        
        return violations
    
    def _check_content_safety(self, content: str) -> List[ConstraintViolation]:
        """检查内容安全"""
        violations = []
        
        try:
            # 使用AI模型进行安全分类
            if self.safety_classifier:
                safety_result = self.safety_classifier(content[:512])[0]
                if safety_result['label'] in ['toxic', 'obscene', 'threat'] and safety_result['score'] > 0.7:
                    violations.append(ConstraintViolation(
                        constraint_type=ConstraintType.CONTENT_SAFETY,
                        severity=ConstraintSeverity.HIGH,
                        message=f"检测到不安全内容: {safety_result['label']}",
                        suggestion="修改或移除不安全内容"
                    ))
        
        except Exception as e:
            logger.warning(f"AI safety check failed: {e}")
        
        # 基于规则的安全检查
        rules = self.constraint_rules.get(ConstraintType.CONTENT_SAFETY, [])
        violations.extend(self._apply_rules(content, rules, ConstraintType.CONTENT_SAFETY))
        
        return violations
    
    def _check_brand_guidelines(self, content: str, brand_name: str) -> List[ConstraintViolation]:
        """检查品牌指南"""
        violations = []
        guidelines = self.brand_guidelines[brand_name]
        
        # 检查禁止术语
        for prohibited_term in guidelines.prohibited_terms:
            if prohibited_term in content:
                violations.append(ConstraintViolation(
                    constraint_type=ConstraintType.BRAND_GUIDELINES,
                    severity=ConstraintSeverity.MEDIUM,
                    message=f"使用了禁止术语: {prohibited_term}",
                    offending_text=prohibited_term,
                    suggestion=f"替换禁止术语 '{prohibited_term}'"
                ))
        
        # 检查必需术语
        for required_term in guidelines.required_terms:
            if required_term not in content:
                violations.append(ConstraintViolation(
                    constraint_type=ConstraintType.BRAND_GUIDELINES,
                    severity=ConstraintSeverity.LOW,
                    message=f"缺少必需术语: {required_term}",
                    suggestion=f"添加品牌术语 '{required_term}'"
                ))
        
        # 检查语气要求
        tone_rules = guidelines.tone_requirements
        if "formal_required" in tone_rules and tone_rules["formal_required"]:
            # 检查正式语气
            informal_indicators = ['哥们', '亲', '哈喽', '嘿']
            for indicator in informal_indicators:
                if indicator in content:
                    violations.append(ConstraintViolation(
                        constraint_type=ConstraintType.BRAND_GUIDELINES,
                        severity=ConstraintSeverity.LOW,
                        message="使用了非正式语气",
                        offending_text=indicator,
                        suggestion="使用更正式的表达方式"
                    ))
        
        return violations
    
    def _check_legal_compliance(self, content: str) -> List[ConstraintViolation]:
        """检查法律合规"""
        violations = []
        
        # 基于规则的法律合规检查
        rules = self.constraint_rules.get(ConstraintType.LEGAL_COMPLIANCE, [])
        violations.extend(self._apply_rules(content, rules, ConstraintType.LEGAL_COMPLIANCE))
        
        # 检查虚假宣传
        exaggeration_terms = ['最', '第一', '独家', '绝对', '保证']
        for term in exaggeration_terms:
            if term in content:
                # 检查上下文是否构成虚假宣传
                context_start = max(0, content.find(term) - 20)
                context_end = min(len(content), content.find(term) + 20)
                context = content[context_start:context_end]
                
                violations.append(ConstraintViolation(
                    constraint_type=ConstraintType.LEGAL_COMPLIANCE,
                    severity=ConstraintSeverity.MEDIUM,
                    message="可能涉及夸大宣传",
                    offending_text=term,
                    suggestion="使用更客观的表述",
                    position=(content.find(term), content.find(term) + len(term))
                ))
        
        return violations
    
    def _check_quality_standards(self, content: str) -> List[ConstraintViolation]:
        """检查质量标准"""
        violations = []
        
        # 基于规则的质量检查
        rules = self.constraint_rules.get(ConstraintType.QUALITY_STANDARDS, [])
        violations.extend(self._apply_rules(content, rules, ConstraintType.QUALITY_STANDARDS))
        
        # 检查拼写错误（简化实现）
        common_typos = {
            '的得地': '注意"的、得、地"的使用',
            '在做': '应为"在作"',
            '帐号': '应为"账号"'
        }
        
        for typo, correction in common_typos.items():
            if typo in content:
                violations.append(ConstraintViolation(
                    constraint_type=ConstraintType.QUALITY_STANDARDS,
                    severity=ConstraintSeverity.LOW,
                    message=f"可能拼写错误: {typo}",
                    offending_text=typo,
                    suggestion=correction
                ))
        
        # 检查可读性
        readability_score = self._calculate_readability(content)
        if readability_score < 0.3:
            violations.append(ConstraintViolation(
                constraint_type=ConstraintType.QUALITY_STANDARDS,
                severity=ConstraintSeverity.MEDIUM,
                message="可读性较低",
                suggestion="简化语言表达，使用更短的句子"
            ))
        
        return violations
    
    def _check_style_guide(self, content: str) -> List[ConstraintViolation]:
        """检查风格指南"""
        violations = []
        
        # 检查标点使用
        if '  ' in content:  # 多个空格
            violations.append(ConstraintViolation(
                constraint_type=ConstraintType.STYLE_GUIDE,
                severity=ConstraintSeverity.LOW,
                message="多个连续空格",
                suggestion="使用单个空格"
            ))
        
        # 检查英文标点
        if re.search(r'[a-zA-Z][。]', content):  # 英文后使用中文句号
            violations.append(ConstraintViolation(
                constraint_type=ConstraintType.STYLE_GUIDE,
                severity=ConstraintSeverity.LOW,
                message="中英文标点混用",
                suggestion="统一标点符号"
            ))
        
        return violations
    
    def _check_accessibility(self, content: str) -> List[ConstraintViolation]:
        """检查可访问性"""
        violations = []
        
        # 检查图片替代文本（在HTML内容中）
        if '<img' in content and 'alt=' not in content:
            violations.append(ConstraintViolation(
                constraint_type=ConstraintType.ACCESSIBILITY,
                severity=ConstraintSeverity.MEDIUM,
                message="图片缺少替代文本",
                suggestion="为所有图片添加alt属性"
            ))
        
        # 检查颜色对比度提示（在HTML内容中）
        if 'color:' in content and 'background' in content:
            # 提醒检查颜色对比度
            violations.append(ConstraintViolation(
                constraint_type=ConstraintType.ACCESSIBILITY,
                severity=ConstraintSeverity.LOW,
                message="可能需要检查颜色对比度",
                suggestion="确保文字和背景有足够对比度"
            ))
        
        return violations
    
    def _apply_rules(self, content: str, rules: List[Dict], constraint_type: ConstraintType) -> List[ConstraintViolation]:
        """应用规则检查"""
        violations = []
        
        for rule in rules:
            if "pattern" in rule:
                # 正则表达式规则
                pattern = rule["pattern"]
                matches = list(re.finditer(pattern, content))
                
                for match in matches:
                    violations.append(ConstraintViolation(
                        constraint_type=constraint_type,
                        severity=rule["severity"],
                        message=rule["message"],
                        offending_text=match.group(),
                        suggestion=rule.get("suggestion"),
                        position=(match.start(), match.end())
                    ))
            
            elif "condition" in rule:
                # 条件规则
                condition = rule["condition"]
                
                # 简单的条件评估（实际应该使用更复杂的表达式解析）
                if "readability_score" in condition:
                    readability = self._calculate_readability(content)
                    threshold = float(condition.split('<')[1].strip())
                    
                    if readability < threshold:
                        violations.append(ConstraintViolation(
                            constraint_type=constraint_type,
                            severity=rule["severity"],
                            message=rule["message"],
                            suggestion=rule.get("suggestion")
                        ))
        
        return violations
    
    def _calculate_readability(self, content: str) -> float:
        """计算可读性分数"""
        # 简化的可读性计算
        sentences = re.split(r'[。！？.!?]', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.5
        
        words = re.findall(r'\b\w+\b', content)
        
        if not words:
            return 0.5
        
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # 简化可读性公式
        readability = 1.0 - min(1.0, (avg_sentence_length / 25 + avg_word_length / 6) / 2)
        return max(0.0, min(1.0, readability))
    
    def _calculate_compliance_score(self, violations: List[ConstraintViolation], content_length: int) -> float:
        """计算合规分数"""
        if not violations:
            return 1.0
        
        # 根据严重程度加权计算
        severity_weights = {
            ConstraintSeverity.LOW: 0.1,
            ConstraintSeverity.MEDIUM: 0.3,
            ConstraintSeverity.HIGH: 0.6,
            ConstraintSeverity.CRITICAL: 1.0
        }
        
        total_weight = sum(severity_weights[v.severity] for v in violations)
        
        # 考虑内容长度的归一化
        normalized_penalty = total_weight / max(1, content_length / 100)
        
        return max(0.0, 1.0 - normalized_penalty)
    
    def auto_correct_violations(self, check_result: ConstraintCheckResult) -> str:
        """自动修正违反约束的内容"""
        corrected_content = check_result.content
        
        # 按严重程度排序，先处理严重的问题
        sorted_violations = sorted(
            check_result.violations,
            key=lambda v: list(ConstraintSeverity).index(v.severity),
            reverse=True
        )
        
        offset = 0
        
        for violation in sorted_violations:
            if violation.offending_text and violation.suggestion and violation.position:
                start, end = violation.position
                start += offset
                end += offset
                
                # 应用修正
                if violation.constraint_type == ConstraintType.CONTENT_SAFETY:
                    # 对于不安全内容，直接移除
                    corrected_content = corrected_content[:start] + "[已移除]" + corrected_content[end:]
                    offset += len("[已移除]") - (end - start)
                
                elif violation.constraint_type == ConstraintType.BRAND_GUIDELINES:
                    # 对于品牌指南问题，尝试替换
                    if "替换" in violation.suggestion:
                        # 提取建议的新术语
                        new_term = violation.suggestion.split("'")[1] if "'" in violation.suggestion else "[适当术语]"
                        corrected_content = corrected_content[:start] + new_term + corrected_content[end:]
                        offset += len(new_term) - (end - start)
                
                elif violation.constraint_type == ConstraintType.QUALITY_STANDARDS:
                    # 对于质量问题，应用建议修正
                    if "拼写错误" in violation.message:
                        # 简单的拼写修正
                        correction_map = {
                            '的得地': '的',
                            '在做': '在作',
                            '帐号': '账号'
                        }
                        for wrong, right in correction_map.items():
                            if wrong in violation.offending_text:
                                corrected_content = corrected_content[:start] + right + corrected_content[end:]
                                offset += len(right) - (end - start)
                                break
        
        return corrected_content
    
    def batch_check_constraints(self, 
                              contents: List[str],
                              brand_names: Optional[List[str]] = None,
                              constraint_types_list: Optional[List[List[ConstraintType]]] = None) -> List[ConstraintCheckResult]:
        """批量检查约束"""
        results = []
        
        if brand_names is None:
            brand_names = [None] * len(contents)
        
        if constraint_types_list is None:
            constraint_types_list = [None] * len(contents)
        
        for content, brand_name, constraint_types in zip(contents, brand_names, constraint_types_list):
            try:
                result = self.check_constraints(content, brand_name, constraint_types)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to check constraints for content: {e}")
                results.append(ConstraintCheckResult(
                    content=content,
                    violations=[],
                    passed=False,
                    score=0.0,
                    metadata={"error": str(e)}
                ))
        
        return results
    
    def generate_compliance_report(self, check_results: List[ConstraintCheckResult]) -> Dict[str, Any]:
        """生成合规报告"""
        total_checks = len(check_results)
        passed_checks = sum(1 for r in check_results if r.passed)
        average_score = sum(r.score for r in check_results) / total_checks if total_checks > 0 else 0.0
        
        # 统计违反类型
        violation_stats = {}
        for result in check_results:
            for violation in result.violations:
                violation_type = violation.constraint_type.value
                violation_stats[violation_type] = violation_stats.get(violation_type, 0) + 1
        
        # 统计严重程度
        severity_stats = {}
        for result in check_results:
            for violation in result.violations:
                severity = violation.severity.value
                severity_stats[severity] = severity_stats.get(severity, 0) + 1
        
        return {
            "summary": {
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "pass_rate": passed_checks / total_checks if total_checks > 0 else 0.0,
                "average_compliance_score": average_score
            },
            "violation_statistics": violation_stats,
            "severity_distribution": severity_stats,
            "generated_at": datetime.now().isoformat()
        }

# 单例实例
_creative_constraints_instance = None

def get_creative_constraints() -> CreativeConstraints:
    """获取创意约束管理器单例"""
    global _creative_constraints_instance
    if _creative_constraints_instance is None:
        _creative_constraints_instance = CreativeConstraints()
    return _creative_constraints_instance

