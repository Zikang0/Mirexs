"""
数据验证工具模块

提供数据验证、规则检查、质量评估、模式验证等功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
import re
from datetime import datetime
import json
import logging
from collections import Counter
import jsonschema
from jsonschema import validate, ValidationError

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchemaValidator:
    """模式验证器"""
    
    def __init__(self, schema: Optional[Dict] = None):
        """初始化模式验证器
        
        Args:
            schema: JSON Schema格式的模式定义
        """
        self.schema = schema or {}
        self.validation_results = {}
    
    def validate_schema(self, data: pd.DataFrame, schema: Optional[Dict] = None) -> Dict[str, Any]:
        """验证数据模式
        
        Args:
            data: 输入数据
            schema: JSON Schema格式的模式定义
            
        Returns:
            验证结果
        """
        if schema is not None:
            self.schema = schema
        
        results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        # 验证列存在性
        if 'required' in self.schema:
            required_columns = self.schema['required']
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                results['errors'].append(f"缺少必填列: {missing_columns}")
                results['is_valid'] = False
        
        # 验证列类型
        if 'properties' in self.schema:
            for col, col_schema in self.schema['properties'].items():
                if col in data.columns:
                    type_check = self._check_column_type(data[col], col_schema)
                    if not type_check['is_valid']:
                        results['errors'].append(f"列 '{col}' 类型错误: {type_check['message']}")
                        results['is_valid'] = False
                    
                    # 验证值范围
                    range_check = self._check_value_range(data[col], col_schema)
                    if not range_check['is_valid']:
                        results['errors'].append(f"列 '{col}' 值范围错误: {range_check['message']}")
                        results['is_valid'] = False
                    
                    # 验证枚举值
                    enum_check = self._check_enum_values(data[col], col_schema)
                    if not enum_check['is_valid']:
                        results['errors'].append(f"列 '{col}' 枚举值错误: {enum_check['message']}")
                        results['is_valid'] = False
                    
                    # 验证模式
                    pattern_check = self._check_pattern(data[col], col_schema)
                    if not pattern_check['is_valid']:
                        results['warnings'].append(f"列 '{col}' 模式警告: {pattern_check['message']}")
        
        # 验证唯一性
        if 'unique' in self.schema:
            unique_columns = self.schema['unique']
            for col in unique_columns:
                if col in data.columns and data[col].duplicated().any():
                    results['errors'].append(f"列 '{col}' 必须唯一，但存在重复值")
                    results['is_valid'] = False
        
        self.validation_results = results
        return results
    
    def _check_column_type(self, series: pd.Series, col_schema: Dict) -> Dict[str, Any]:
        """检查列类型"""
        expected_type = col_schema.get('type', 'string')
        
        type_mapping = {
            'string': ['object', 'string'],
            'number': ['int64', 'float64', 'int32', 'float32'],
            'integer': ['int64', 'int32'],
            'boolean': ['bool', 'boolean'],
            'array': ['object'],
            'object': ['object'],
            'null': ['object']
        }
        
        actual_type = str(series.dtype)
        expected_types = type_mapping.get(expected_type, [expected_type])
        
        if not any(t in actual_type for t in expected_types):
            return {
                'is_valid': False,
                'message': f"期望类型 {expected_type}，实际类型 {actual_type}"
            }
        
        return {'is_valid': True, 'message': ''}
    
    def _check_value_range(self, series: pd.Series, col_schema: Dict) -> Dict[str, Any]:
        """检查值范围"""
        if not pd.api.types.is_numeric_dtype(series):
            return {'is_valid': True, 'message': ''}
        
        series_clean = series.dropna()
        if len(series_clean) == 0:
            return {'is_valid': True, 'message': ''}
        
        if 'minimum' in col_schema:
            min_val = col_schema['minimum']
            if series_clean.min() < min_val:
                return {
                    'is_valid': False,
                    'message': f"最小值 {series_clean.min()} 小于允许的最小值 {min_val}"
                }
        
        if 'maximum' in col_schema:
            max_val = col_schema['maximum']
            if series_clean.max() > max_val:
                return {
                    'is_valid': False,
                    'message': f"最大值 {series_clean.max()} 大于允许的最大值 {max_val}"
                }
        
        if 'exclusiveMinimum' in col_schema:
            min_val = col_schema['exclusiveMinimum']
            if series_clean.min() <= min_val:
                return {
                    'is_valid': False,
                    'message': f"最小值 {series_clean.min()} 必须大于 {min_val}"
                }
        
        if 'exclusiveMaximum' in col_schema:
            max_val = col_schema['exclusiveMaximum']
            if series_clean.max() >= max_val:
                return {
                    'is_valid': False,
                    'message': f"最大值 {series_clean.max()} 必须小于 {max_val}"
                }
        
        return {'is_valid': True, 'message': ''}
    
    def _check_enum_values(self, series: pd.Series, col_schema: Dict) -> Dict[str, Any]:
        """检查枚举值"""
        if 'enum' not in col_schema:
            return {'is_valid': True, 'message': ''}
        
        allowed_values = set(col_schema['enum'])
        series_values = set(series.dropna().unique())
        
        invalid_values = series_values - allowed_values
        if invalid_values:
            return {
                'is_valid': False,
                'message': f"包含不允许的值: {list(invalid_values)[:5]}"
            }
        
        return {'is_valid': True, 'message': ''}
    
    def _check_pattern(self, series: pd.Series, col_schema: Dict) -> Dict[str, Any]:
        """检查模式"""
        if 'pattern' not in col_schema:
            return {'is_valid': True, 'message': ''}
        
        pattern = col_schema['pattern']
        series_str = series.astype(str)
        
        mismatches = ~series_str.str.match(pattern, na=False)
        mismatch_count = mismatches.sum()
        
        if mismatch_count > 0:
            return {
                'is_valid': False,
                'message': f"{mismatch_count} 个值不符合模式 '{pattern}'"
            }
        
        return {'is_valid': True, 'message': ''}
    
    def get_validation_results(self) -> Dict[str, Any]:
        """获取验证结果"""
        return self.validation_results


class BusinessRuleValidator:
    """业务规则验证器"""
    
    def __init__(self, rules: Optional[List[Dict]] = None):
        """初始化业务规则验证器
        
        Args:
            rules: 业务规则列表
        """
        self.rules = rules or []
        self.rule_results = {}
    
    def add_rule(self, rule: Dict) -> 'BusinessRuleValidator':
        """添加规则"""
        self.rules.append(rule)
        return self
    
    def validate(self, data: pd.DataFrame, rules: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """验证业务规则
        
        Args:
            data: 输入数据
            rules: 业务规则列表
            
        Returns:
            验证结果
        """
        if rules is not None:
            self.rules = rules
        
        results = {
            'is_valid': True,
            'rules_passed': 0,
            'rules_failed': 0,
            'rule_results': {},
            'errors': [],
            'warnings': []
        }
        
        for i, rule in enumerate(self.rules):
            rule_name = rule.get('name', f'rule_{i}')
            rule_type = rule.get('type')
            rule_params = rule.get('params', {})
            
            try:
                if rule_type == 'range_check':
                    rule_result = self._validate_range(data, rule_params)
                elif rule_type == 'pattern_check':
                    rule_result = self._validate_pattern(data, rule_params)
                elif rule_type == 'reference_check':
                    rule_result = self._validate_reference(data, rule_params)
                elif rule_type == 'custom_check':
                    rule_result = self._validate_custom(data, rule_params)
                elif rule_type == 'consistency_check':
                    rule_result = self._validate_consistency(data, rule_params)
                elif rule_type == 'uniqueness_check':
                    rule_result = self._validate_uniqueness(data, rule_params)
                elif rule_type == 'completeness_check':
                    rule_result = self._validate_completeness(data, rule_params)
                elif rule_type == 'dependency_check':
                    rule_result = self._validate_dependency(data, rule_params)
                elif rule_type == 'threshold_check':
                    rule_result = self._validate_threshold(data, rule_params)
                else:
                    rule_result = {'is_valid': False, 'error': f"不支持的规则类型: {rule_type}"}
                
                results['rule_results'][rule_name] = rule_result
                
                if rule_result.get('is_valid', False):
                    results['rules_passed'] += 1
                else:
                    results['rules_failed'] += 1
                    results['is_valid'] = False
                    
                    if 'error' in rule_result:
                        results['errors'].append(f"{rule_name}: {rule_result['error']}")
                    if 'warnings' in rule_result:
                        results['warnings'].extend([f"{rule_name}: {w}" for w in rule_result['warnings']])
            
            except Exception as e:
                results['rules_failed'] += 1
                results['is_valid'] = False
                results['errors'].append(f"{rule_name}: 执行失败 - {str(e)}")
        
        self.rule_results = results
        return results
    
    def _validate_range(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """范围检查"""
        column = params.get('column')
        min_val = params.get('min')
        max_val = params.get('max')
        inclusive_min = params.get('inclusive_min', True)
        inclusive_max = params.get('inclusive_max', True)
        
        if column not in data.columns:
            return {'is_valid': False, 'error': f"列 '{column}' 不存在"}
        
        if not pd.api.types.is_numeric_dtype(data[column]):
            return {'is_valid': False, 'error': f"列 '{column}' 不是数值类型"}
        
        series = data[column].dropna()
        violations = []
        
        if min_val is not None:
            if inclusive_min:
                below_min = series < min_val
            else:
                below_min = series <= min_val
            violations.extend(series[below_min].index.tolist())
        
        if max_val is not None:
            if inclusive_max:
                above_max = series > max_val
            else:
                above_max = series >= max_val
            violations.extend(series[above_max].index.tolist())
        
        if violations:
            return {
                'is_valid': False,
                'error': f"有 {len(violations)} 个值超出范围 [{min_val}, {max_val}]",
                'violation_count': len(violations),
                'violation_indices': list(set(violations))[:10]
            }
        
        return {'is_valid': True, 'message': '所有值都在有效范围内'}
    
    def _validate_pattern(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """模式检查"""
        column = params.get('column')
        pattern = params.get('pattern')
        
        if column not in data.columns:
            return {'is_valid': False, 'error': f"列 '{column}' 不存在"}
        
        series = data[column].astype(str)
        violations = []
        
        for idx, value in series.items():
            if not re.match(pattern, value):
                violations.append(idx)
        
        if violations:
            return {
                'is_valid': False,
                'error': f"有 {len(violations)} 个值不符合模式 '{pattern}'",
                'violation_count': len(violations),
                'violation_indices': violations[:10]
            }
        
        return {'is_valid': True, 'message': '所有值都符合模式要求'}
    
    def _validate_reference(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """参考值检查"""
        column = params.get('column')
        reference_values = set(params.get('reference_values', []))
        reference_file = params.get('reference_file')
        
        if column not in data.columns:
            return {'is_valid': False, 'error': f"列 '{column}' 不存在"}
        
        # 如果提供了参考文件，加载参考值
        if reference_file:
            try:
                ref_df = pd.read_csv(reference_file)
                ref_col = params.get('reference_column', column)
                if ref_col in ref_df.columns:
                    reference_values = set(ref_df[ref_col].dropna().unique())
            except Exception as e:
                return {'is_valid': False, 'error': f"加载参考文件失败: {e}"}
        
        if not reference_values:
            return {'is_valid': True, 'message': '没有参考值需要验证'}
        
        series = data[column].dropna()
        invalid_values = series[~series.isin(reference_values)]
        
        if len(invalid_values) > 0:
            return {
                'is_valid': False,
                'error': f"有 {len(invalid_values)} 个值不在参考值列表中",
                'invalid_count': len(invalid_values),
                'invalid_values': invalid_values.unique().tolist()[:10]
            }
        
        return {'is_valid': True, 'message': '所有值都在参考值列表中'}
    
    def _validate_custom(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """自定义检查"""
        column = params.get('column')
        condition = params.get('condition')
        error_message = params.get('error_message', '自定义验证失败')
        
        if column not in data.columns:
            return {'is_valid': False, 'error': f"列 '{column}' 不存在"}
        
        try:
            # 解析条件函数
            if isinstance(condition, str):
                condition_func = eval(condition)
            else:
                condition_func = condition
            
            violations = ~data[column].apply(condition_func)
            violation_count = violations.sum()
            
            if violation_count > 0:
                return {
                    'is_valid': False,
                    'error': f"{error_message} (违反条件: {violation_count} 条记录)",
                    'violation_count': violation_count,
                    'violation_indices': data[violations].index.tolist()[:10]
                }
            
            return {'is_valid': True, 'message': '自定义验证通过'}
        
        except Exception as e:
            return {'is_valid': False, 'error': f"自定义条件执行失败: {str(e)}"}
    
    def _validate_consistency(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """一致性检查"""
        column1 = params.get('column1')
        column2 = params.get('column2')
        relationship = params.get('relationship')
        tolerance = params.get('tolerance', 0)
        
        if column1 not in data.columns or column2 not in data.columns:
            return {'is_valid': False, 'error': f"列 '{column1}' 或 '{column2}' 不存在"}
        
        violations = []
        
        for idx in data.index:
            val1 = data.loc[idx, column1]
            val2 = data.loc[idx, column2]
            
            if pd.isna(val1) or pd.isna(val2):
                continue
            
            if relationship == 'greater_than':
                if not (val1 > val2 - tolerance):
                    violations.append(idx)
            elif relationship == 'less_than':
                if not (val1 < val2 + tolerance):
                    violations.append(idx)
            elif relationship == 'equal':
                if pd.api.types.is_numeric_dtype(data[column1]):
                    if not abs(val1 - val2) <= tolerance:
                        violations.append(idx)
                else:
                    if val1 != val2:
                        violations.append(idx)
            elif relationship == 'not_equal':
                if val1 == val2:
                    violations.append(idx)
        
        if violations:
            return {
                'is_valid': False,
                'error': f"在 {len(violations)} 行中不满足 '{relationship}' 关系",
                'violation_count': len(violations),
                'violation_indices': violations[:10]
            }
        
        return {'is_valid': True, 'message': f"列 '{column1}' 和 '{column2}' 满足 '{relationship}' 关系"}
    
    def _validate_uniqueness(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """唯一性检查"""
        columns = params.get('columns', [])
        
        if not columns:
            return {'is_valid': True, 'message': '没有指定列'}
        
        missing_cols = [col for col in columns if col not in data.columns]
        if missing_cols:
            return {'is_valid': False, 'error': f"列不存在: {missing_cols}"}
        
        duplicates = data.duplicated(subset=columns, keep=False)
        duplicate_count = duplicates.sum()
        
        if duplicate_count > 0:
            return {
                'is_valid': False,
                'error': f"存在 {duplicate_count} 条重复记录",
                'duplicate_count': duplicate_count,
                'duplicate_indices': data[duplicates].index.tolist()[:10]
            }
        
        return {'is_valid': True, 'message': '所有记录都是唯一的'}
    
    def _validate_completeness(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """完整性检查"""
        columns = params.get('columns', [])
        threshold = params.get('threshold', 100.0)
        
        if not columns:
            columns = data.columns.tolist()
        
        missing_cols = [col for col in columns if col not in data.columns]
        if missing_cols:
            return {'is_valid': False, 'error': f"列不存在: {missing_cols}"}
        
        completeness_results = {}
        all_complete = True
        
        for col in columns:
            non_null_count = data[col].count()
            completeness = (non_null_count / len(data)) * 100
            
            completeness_results[col] = {
                'completeness': completeness,
                'missing_count': len(data) - non_null_count
            }
            
            if completeness < threshold:
                all_complete = False
        
        if not all_complete:
            return {
                'is_valid': False,
                'error': f"存在完整性低于 {threshold}% 的列",
                'completeness_results': completeness_results
            }
        
        return {'is_valid': True, 'message': '所有列完整性达标'}
    
    def _validate_dependency(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """依赖关系检查"""
        if_column = params.get('if_column')
        if_value = params.get('if_value')
        then_column = params.get('then_column')
        then_condition = params.get('then_condition')
        
        if if_column not in data.columns or then_column not in data.columns:
            return {'is_valid': False, 'error': f"列 '{if_column}' 或 '{then_column}' 不存在"}
        
        violations = []
        
        for idx in data.index:
            if data.loc[idx, if_column] == if_value:
                then_value = data.loc[idx, then_column]
                
                if isinstance(then_condition, dict):
                    # 范围条件
                    min_val = then_condition.get('min')
                    max_val = then_condition.get('max')
                    
                    if min_val is not None and then_value < min_val:
                        violations.append(idx)
                    if max_val is not None and then_value > max_val:
                        violations.append(idx)
                else:
                    # 等于条件
                    if then_value != then_condition:
                        violations.append(idx)
        
        if violations:
            return {
                'is_valid': False,
                'error': f"有 {len(violations)} 行违反依赖关系",
                'violation_count': len(violations),
                'violation_indices': violations[:10]
            }
        
        return {'is_valid': True, 'message': '所有依赖关系都满足'}
    
    def _validate_threshold(self, data: pd.DataFrame, params: Dict) -> Dict[str, Any]:
        """阈值检查"""
        column = params.get('column')
        threshold = params.get('threshold')
        operator = params.get('operator', 'lt')
        
        if column not in data.columns:
            return {'is_valid': False, 'error': f"列 '{column}' 不存在"}
        
        series = data[column].dropna()
        
        if operator == 'lt':
            violations = series[series >= threshold]
        elif operator == 'le':
            violations = series[series > threshold]
        elif operator == 'gt':
            violations = series[series <= threshold]
        elif operator == 'ge':
            violations = series[series < threshold]
        elif operator == 'eq':
            violations = series[series != threshold]
        elif operator == 'ne':
            violations = series[series == threshold]
        else:
            return {'is_valid': False, 'error': f"不支持的运算符: {operator}"}
        
        violation_count = len(violations)
        
        if violation_count > 0:
            return {
                'is_valid': False,
                'error': f"有 {violation_count} 个值违反阈值条件 {operator} {threshold}",
                'violation_count': violation_count,
                'violation_indices': violations.index.tolist()[:10]
            }
        
        return {'is_valid': True, 'message': '所有值都满足阈值条件'}
    
    def get_rule_results(self) -> Dict[str, Any]:
        """获取规则验证结果"""
        return self.rule_results


class QualityValidator:
    """数据质量验证器"""
    
    def __init__(self):
        self.quality_scores = {}
    
    def validate(self, data: pd.DataFrame) -> Dict[str, Any]:
        """验证数据质量
        
        Args:
            data: 输入数据
            
        Returns:
            质量验证结果
        """
        results = {
            'is_valid': True,
            'quality_score': 0.0,
            'dimensions': {},
            'issues': []
        }
        
        # 完整性验证
        completeness = self._check_completeness(data)
        results['dimensions']['completeness'] = completeness
        if completeness['score'] < 90:
            results['is_valid'] = False
            results['issues'].append(f"完整性较低: {completeness['score']:.1f}%")
        
        # 唯一性验证
        uniqueness = self._check_uniqueness(data)
        results['dimensions']['uniqueness'] = uniqueness
        if uniqueness['score'] < 95:
            results['is_valid'] = False
            results['issues'].append(f"唯一性较低: {uniqueness['score']:.1f}%")
        
        # 有效性验证
        validity = self._check_validity(data)
        results['dimensions']['validity'] = validity
        if validity['score'] < 90:
            results['is_valid'] = False
            results['issues'].append(f"有效性较低: {validity['score']:.1f}%")
        
        # 一致性验证
        consistency = self._check_consistency(data)
        results['dimensions']['consistency'] = consistency
        if consistency['score'] < 90:
            results['is_valid'] = False
            results['issues'].append(f"一致性较低: {consistency['score']:.1f}%")
        
        # 准确性验证
        accuracy = self._check_accuracy(data)
        results['dimensions']['accuracy'] = accuracy
        
        # 计算综合质量分数
        weights = {
            'completeness': 0.25,
            'uniqueness': 0.20,
            'validity': 0.25,
            'consistency': 0.15,
            'accuracy': 0.15
        }
        
        total_score = 0
        for dim, weight in weights.items():
            total_score += results['dimensions'][dim]['score'] * weight
        
        results['quality_score'] = total_score
        results['quality_grade'] = self._get_quality_grade(total_score)
        
        self.quality_scores = results
        return results
    
    def _check_completeness(self, data: pd.DataFrame) -> Dict[str, Any]:
        """检查完整性"""
        total_cells = data.shape[0] * data.shape[1]
        non_null_cells = data.count().sum()
        completeness = (non_null_cells / total_cells) * 100
        
        return {
            'score': completeness,
            'total_cells': total_cells,
            'non_null_cells': non_null_cells,
            'missing_cells': total_cells - non_null_cells,
            'missing_percentage': 100 - completeness
        }
    
    def _check_uniqueness(self, data: pd.DataFrame) -> Dict[str, Any]:
        """检查唯一性"""
        duplicate_rows = data.duplicated().sum()
        uniqueness = ((len(data) - duplicate_rows) / len(data)) * 100
        
        return {
            'score': uniqueness,
            'total_rows': len(data),
            'duplicate_rows': duplicate_rows,
            'duplicate_percentage': (duplicate_rows / len(data)) * 100
        }
    
    def _check_validity(self, data: pd.DataFrame) -> Dict[str, Any]:
        """检查有效性"""
        validity_scores = []
        
        for col in data.columns:
            if pd.api.types.is_numeric_dtype(data[col]):
                # 检查异常值
                Q1 = data[col].quantile(0.25)
                Q3 = data[col].quantile(0.75)
                IQR = Q3 - Q1
                outliers = ((data[col] < (Q1 - 1.5 * IQR)) | (data[col] > (Q3 + 1.5 * IQR))).sum()
                validity = ((len(data) - outliers) / len(data)) * 100
            else:
                # 检查空字符串
                empty_count = (data[col].astype(str).str.strip() == '').sum()
                validity = ((len(data) - empty_count) / len(data)) * 100
            
            validity_scores.append(validity)
        
        avg_validity = np.mean(validity_scores) if validity_scores else 100
        
        return {
            'score': avg_validity,
            'column_scores': dict(zip(data.columns, validity_scores))
        }
    
    def _check_consistency(self, data: pd.DataFrame) -> Dict[str, Any]:
        """检查一致性"""
        consistency_scores = []
        
        for col in data.columns:
            if pd.api.types.is_numeric_dtype(data[col]):
                # 检查数据类型一致性
                expected_type = str(data[col].dtype)
                try:
                    pd.to_numeric(data[col], errors='raise')
                    consistency = 100
                except:
                    consistency = 50
            else:
                # 检查长度一致性
                lengths = data[col].astype(str).str.len()
                length_std = lengths.std()
                if length_std > 0:
                    consistency = min(100, 100 / (1 + length_std))
                else:
                    consistency = 100
            
            consistency_scores.append(consistency)
        
        avg_consistency = np.mean(consistency_scores) if consistency_scores else 100
        
        return {
            'score': avg_consistency,
            'column_scores': dict(zip(data.columns, consistency_scores))
        }
    
    def _check_accuracy(self, data: pd.DataFrame) -> Dict[str, Any]:
        """检查准确性（基于基本统计）"""
        accuracy_scores = []
        
        for col in data.select_dtypes(include=[np.number]).columns:
            # 基于正态分布检查
            mean = data[col].mean()
            std = data[col].std()
            
            if std > 0:
                # 检查是否在3个标准差内
                within_3sigma = ((data[col] >= mean - 3 * std) & (data[col] <= mean + 3 * std)).sum()
                accuracy = (within_3sigma / len(data)) * 100
                accuracy_scores.append(accuracy)
        
        avg_accuracy = np.mean(accuracy_scores) if accuracy_scores else 100
        
        return {
            'score': avg_accuracy,
            'note': '基于3σ原则的准确性评估'
        }
    
    def _get_quality_grade(self, score: float) -> str:
        """获取质量等级"""
        if score >= 95:
            return "优秀"
        elif score >= 85:
            return "良好"
        elif score >= 75:
            return "中等"
        elif score >= 60:
            return "及格"
        else:
            return "不及格"
    
    def get_quality_scores(self) -> Dict[str, Any]:
        """获取质量分数"""
        return self.quality_scores


class CrossReferenceValidator:
    """交叉引用验证器"""
    
    def __init__(self):
        self.reference_stats = {}
    
    def validate(self, source_df: pd.DataFrame, target_df: pd.DataFrame,
                source_column: str, target_column: str) -> Dict[str, Any]:
        """验证交叉引用
        
        Args:
            source_df: 源数据
            target_df: 目标数据
            source_column: 源列名
            target_column: 目标列名
            
        Returns:
            验证结果
        """
        if source_column not in source_df.columns:
            return {'is_valid': False, 'error': f"源列 '{source_column}' 不存在"}
        
        if target_column not in target_df.columns:
            return {'is_valid': False, 'error': f"目标列 '{target_column}' 不存在"}
        
        source_values = set(source_df[source_column].dropna().unique())
        target_values = set(target_df[target_column].dropna().unique())
        
        missing_in_target = source_values - target_values
        missing_in_source = target_values - source_values
        
        overlap = source_values & target_values
        
        results = {
            'is_valid': len(missing_in_target) == 0,
            'source_count': len(source_values),
            'target_count': len(target_values),
            'overlap_count': len(overlap),
            'overlap_percentage': (len(overlap) / len(source_values)) * 100 if source_values else 0,
            'missing_in_target': list(missing_in_target)[:20],
            'missing_in_target_count': len(missing_in_target),
            'missing_in_source': list(missing_in_source)[:20],
            'missing_in_source_count': len(missing_in_source)
        }
        
        self.reference_stats = results
        return results
    
    def validate_foreign_key(self, source_df: pd.DataFrame, target_df: pd.DataFrame,
                            source_column: str, target_column: str) -> Dict[str, Any]:
        """验证外键关系"""
        result = self.validate(source_df, target_df, source_column, target_column)
        
        if result['missing_in_target_count'] > 0:
            result['is_valid'] = False
            result['error'] = f"存在 {result['missing_in_target_count']} 个外键值在目标表中不存在"
        
        return result
    
    def get_reference_stats(self) -> Dict[str, Any]:
        """获取引用统计"""
        return self.reference_stats


class DataValidator:
    """综合数据验证器"""
    
    def __init__(self):
        self.schema_validator = SchemaValidator()
        self.business_validator = BusinessRuleValidator()
        self.quality_validator = QualityValidator()
        self.reference_validator = CrossReferenceValidator()
        
        self.validation_log = []
        self.validation_results = {}
    
    def validate(self, data: pd.DataFrame,
                schema: Optional[Dict] = None,
                business_rules: Optional[List[Dict]] = None,
                reference_data: Optional[Tuple[pd.DataFrame, str, str]] = None) -> Dict[str, Any]:
        """综合验证数据
        
        Args:
            data: 输入数据
            schema: JSON Schema格式的模式定义
            business_rules: 业务规则列表
            reference_data: 参考数据元组 (ref_df, source_col, target_col)
            
        Returns:
            验证结果
        """
        self._log("开始数据验证")
        
        results = {
            'is_valid': True,
            'schema_validation': {},
            'business_validation': {},
            'quality_validation': {},
            'reference_validation': {},
            'errors': [],
            'warnings': []
        }
        
        # 模式验证
        if schema:
            self._log("执行模式验证")
            schema_result = self.schema_validator.validate_schema(data, schema)
            results['schema_validation'] = schema_result
            
            if not schema_result['is_valid']:
                results['is_valid'] = False
                results['errors'].extend(schema_result.get('errors', []))
            results['warnings'].extend(schema_result.get('warnings', []))
        
        # 业务规则验证
        if business_rules:
            self._log("执行业务规则验证")
            business_result = self.business_validator.validate(data, business_rules)
            results['business_validation'] = business_result
            
            if not business_result['is_valid']:
                results['is_valid'] = False
                results['errors'].extend(business_result.get('errors', []))
            results['warnings'].extend(business_result.get('warnings', []))
        
        # 数据质量验证
        self._log("执行数据质量验证")
        quality_result = self.quality_validator.validate(data)
        results['quality_validation'] = quality_result
        
        if quality_result['quality_score'] < 80:
            results['warnings'].append(f"数据质量分数较低: {quality_result['quality_score']:.1f}")
        
        # 交叉引用验证
        if reference_data:
            ref_df, source_col, target_col = reference_data
            self._log("执行交叉引用验证")
            ref_result = self.reference_validator.validate(data, ref_df, source_col, target_col)
            results['reference_validation'] = ref_result
            
            if not ref_result['is_valid']:
                results['is_valid'] = False
                results['errors'].append(f"交叉引用验证失败: 缺失 {ref_result['missing_in_target_count']} 个引用")
        
        self.validation_results = results
        self._log("数据验证完成")
        
        return results
    
    def _log(self, message: str):
        """记录日志"""
        log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.validation_log.append(log_entry)
        logger.info(log_entry)
    
    def get_log(self) -> List[str]:
        """获取日志"""
        return self.validation_log
    
    def get_validation_results(self) -> Dict[str, Any]:
        """获取验证结果"""
        return self.validation_results
    
    def generate_report(self) -> str:
        """生成验证报告"""
        if not self.validation_results:
            return "尚未执行验证"
        
        results = self.validation_results
        report = []
        report.append("=" * 60)
        report.append("数据验证报告")
        report.append("=" * 60)
        report.append(f"验证通过: {'是' if results['is_valid'] else '否'}")
        report.append("")
        
        # 模式验证
        if results['schema_validation']:
            report.append("模式验证:")
            schema_res = results['schema_validation']
            report.append(f"  状态: {'通过' if schema_res['is_valid'] else '失败'}")
            if schema_res.get('errors'):
                report.append(f"  错误: {len(schema_res['errors'])}")
                for err in schema_res['errors'][:5]:
                    report.append(f"    - {err}")
        
        # 业务规则验证
        if results['business_validation']:
            report.append("业务规则验证:")
            biz_res = results['business_validation']
            report.append(f"  通过规则: {biz_res.get('rules_passed', 0)}")
            report.append(f"  失败规则: {biz_res.get('rules_failed', 0)}")
            if biz_res.get('errors'):
                for err in biz_res['errors'][:5]:
                    report.append(f"    - {err}")
        
        # 质量验证
        if results['quality_validation']:
            report.append("数据质量验证:")
            qual_res = results['quality_validation']
            report.append(f"  质量分数: {qual_res.get('quality_score', 0):.2f}")
            report.append(f"  质量等级: {qual_res.get('quality_grade', '未知')}")
            
            for dim, dim_res in qual_res.get('dimensions', {}).items():
                report.append(f"    {dim}: {dim_res.get('score', 0):.2f}")
        
        # 交叉引用验证
        if results['reference_validation']:
            report.append("交叉引用验证:")
            ref_res = results['reference_validation']
            report.append(f"  重叠率: {ref_res.get('overlap_percentage', 0):.2f}%")
            report.append(f"  缺失引用: {ref_res.get('missing_in_target_count', 0)}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)


# 便捷函数
def validate_email_format(email_series: pd.Series) -> Dict[str, Any]:
    """验证邮箱格式"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    valid_emails = email_series.astype(str).apply(lambda x: bool(re.match(email_pattern, x)))
    invalid_count = (~valid_emails).sum()
    
    return {
        'is_valid': invalid_count == 0,
        'total': len(email_series),
        'valid': valid_emails.sum(),
        'invalid': invalid_count,
        'valid_rate': (valid_emails.sum() / len(email_series)) * 100,
        'invalid_indices': email_series[~valid_emails].index.tolist()[:10]
    }


def validate_phone_format(phone_series: pd.Series,
                         country_code: str = 'CN') -> Dict[str, Any]:
    """验证手机号格式"""
    patterns = {
        'CN': r'^1[3-9]\d{9}$',
        'US': r'^\+?1?\d{10}$',
        'UK': r'^\+?44\d{10}$',
        'JP': r'^\+?81\d{9,10}$'
    }
    
    phone_pattern = patterns.get(country_code, patterns['CN'])
    
    valid_phones = phone_series.astype(str).apply(
        lambda x: bool(re.match(phone_pattern, re.sub(r'[\s\-\(\)]', '', x)))
    )
    invalid_count = (~valid_phones).sum()
    
    return {
        'is_valid': invalid_count == 0,
        'total': len(phone_series),
        'valid': valid_phones.sum(),
        'invalid': invalid_count,
        'valid_rate': (valid_phones.sum() / len(phone_series)) * 100,
        'invalid_indices': phone_series[~valid_phones].index.tolist()[:10]
    }


def validate_url_format(url_series: pd.Series) -> Dict[str, Any]:
    """验证URL格式"""
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    
    valid_urls = url_series.astype(str).apply(lambda x: bool(re.match(url_pattern, x)))
    invalid_count = (~valid_urls).sum()
    
    return {
        'is_valid': invalid_count == 0,
        'total': len(url_series),
        'valid': valid_urls.sum(),
        'invalid': invalid_count,
        'valid_rate': (valid_urls.sum() / len(url_series)) * 100,
        'invalid_indices': url_series[~valid_urls].index.tolist()[:10]
    }


def validate_date_range(date_series: pd.Series,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> Dict[str, Any]:
    """验证日期范围"""
    parsed_dates = pd.to_datetime(date_series, errors='coerce')
    invalid_dates = parsed_dates.isnull()
    
    if invalid_dates.sum() > 0:
        return {
            'is_valid': False,
            'error': f"有 {invalid_dates.sum()} 个无效日期",
            'invalid_count': invalid_dates.sum(),
            'invalid_indices': date_series[invalid_dates].index.tolist()[:10]
        }
    
    violations = []
    
    if start_date:
        start = pd.to_datetime(start_date)
        before_start = parsed_dates < start
        violations.extend(date_series[before_start].index.tolist())
    
    if end_date:
        end = pd.to_datetime(end_date)
        after_end = parsed_dates > end
        violations.extend(date_series[after_end].index.tolist())
    
    if violations:
        return {
            'is_valid': False,
            'error': f"有 {len(violations)} 个日期超出范围",
            'violation_count': len(violations),
            'violation_indices': violations[:10]
        }
    
    return {
        'is_valid': True,
        'min_date': str(parsed_dates.min()),
        'max_date': str(parsed_dates.max())
    }


def validate_numeric_range(numeric_series: pd.Series,
                          min_val: Optional[float] = None,
                          max_val: Optional[float] = None) -> Dict[str, Any]:
    """验证数值范围"""
    series = numeric_series.dropna()
    violations = []
    
    if min_val is not None:
        below_min = series < min_val
        violations.extend(series[below_min].index.tolist())
    
    if max_val is not None:
        above_max = series > max_val
        violations.extend(series[above_max].index.tolist())
    
    if violations:
        return {
            'is_valid': False,
            'violation_count': len(violations),
            'violation_indices': violations[:10],
            'min': float(series.min()),
            'max': float(series.max())
        }
    
    return {
        'is_valid': True,
        'min': float(series.min()),
        'max': float(series.max()),
        'mean': float(series.mean())
    }


def validate_categorical_values(cat_series: pd.Series,
                               allowed_values: List[Any]) -> Dict[str, Any]:
    """验证分类值"""
    series = cat_series.dropna()
    invalid_values = series[~series.isin(allowed_values)]
    
    if len(invalid_values) > 0:
        return {
            'is_valid': False,
            'invalid_count': len(invalid_values),
            'invalid_values': invalid_values.unique().tolist()[:10],
            'invalid_indices': invalid_values.index.tolist()[:10]
        }
    
    return {
        'is_valid': True,
        'unique_count': series.nunique()
    }


def validate_data_types(df: pd.DataFrame,
                       expected_types: Dict[str, str]) -> Dict[str, Any]:
    """验证数据类型"""
    results = {
        'is_valid': True,
        'type_matches': {},
        'errors': []
    }
    
    for col, expected_type in expected_types.items():
        if col not in df.columns:
            results['errors'].append(f"列 '{col}' 不存在")
            results['is_valid'] = False
            continue
        
        actual_type = str(df[col].dtype)
        
        if expected_type == 'numeric' and 'int' in actual_type or 'float' in actual_type:
            results['type_matches'][col] = True
        elif expected_type == 'string' and actual_type == 'object':
            results['type_matches'][col] = True
        elif expected_type == 'datetime' and 'datetime' in actual_type:
            results['type_matches'][col] = True
        elif expected_type in actual_type:
            results['type_matches'][col] = True
        else:
            results['type_matches'][col] = False
            results['errors'].append(f"列 '{col}' 类型错误: 期望 {expected_type}, 实际 {actual_type}")
            results['is_valid'] = False
    
    return results


def validate_completeness(df: pd.DataFrame,
                         columns: Optional[List[str]] = None) -> Dict[str, Any]:
    """验证数据完整性"""
    if columns is None:
        columns = df.columns.tolist()
    
    results = {}
    all_complete = True
    
    for col in columns:
        if col not in df.columns:
            results[col] = {'is_complete': False, 'missing_count': len(df)}
            all_complete = False
            continue
        
        missing_count = df[col].isnull().sum()
        completeness = ((len(df) - missing_count) / len(df)) * 100
        
        results[col] = {
            'is_complete': missing_count == 0,
            'completeness': completeness,
            'missing_count': missing_count
        }
        
        if missing_count > 0:
            all_complete = False
    
    return {
        'is_valid': all_complete,
        'column_results': results
    }


def validate_uniqueness(df: pd.DataFrame,
                       columns: Optional[List[str]] = None) -> Dict[str, Any]:
    """验证数据唯一性"""
    if columns is None:
        columns = df.columns.tolist()
    
    duplicates = df.duplicated(subset=columns, keep=False)
    duplicate_count = duplicates.sum()
    
    return {
        'is_valid': duplicate_count == 0,
        'duplicate_count': duplicate_count,
        'duplicate_percentage': (duplicate_count / len(df)) * 100,
        'duplicate_indices': df[duplicates].index.tolist()[:10]
    }


def validate_consistency(df: pd.DataFrame,
                        column_pairs: List[Tuple[str, str, str]]) -> Dict[str, Any]:
    """验证数据一致性"""
    results = {
        'is_valid': True,
        'inconsistencies': []
    }
    
    for col1, col2, relationship in column_pairs:
        if col1 not in df.columns or col2 not in df.columns:
            results['inconsistencies'].append(f"列 '{col1}' 或 '{col2}' 不存在")
            results['is_valid'] = False
            continue
        
        mask = df[col1].notna() & df[col2].notna()
        inconsistent_indices = []
        
        for idx in df[mask].index:
            val1 = df.loc[idx, col1]
            val2 = df.loc[idx, col2]
            
            if relationship == 'greater' and val1 <= val2:
                inconsistent_indices.append(idx)
            elif relationship == 'less' and val1 >= val2:
                inconsistent_indices.append(idx)
            elif relationship == 'equal' and val1 != val2:
                inconsistent_indices.append(idx)
        
        if inconsistent_indices:
            results['inconsistencies'].append({
                'columns': [col1, col2],
                'relationship': relationship,
                'count': len(inconsistent_indices),
                'indices': inconsistent_indices[:10]
            })
            results['is_valid'] = False
    
    return results


def generate_validation_report(validator: DataValidator) -> str:
    """生成验证报告"""
    return validator.generate_report()