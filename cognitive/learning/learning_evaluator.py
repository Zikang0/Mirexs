# cognitive/learning/learning_evaluator.py
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import json
import os
from datetime import datetime, timedelta
import logging
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns

class LearningMetrics:
    """学习指标收集器"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.timestamps = defaultdict(list)
        
    def record_metric(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """记录指标"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.metrics[metric_name].append(value)
        self.timestamps[metric_name].append(timestamp)
    
    def get_metric_stats(self, metric_name: str, window_hours: int = 24) -> Dict[str, Any]:
        """获取指标统计"""
        if metric_name not in self.metrics:
            return {'error': f'指标 {metric_name} 不存在'}
        
        # 过滤时间窗口内的数据
        cutoff_time = datetime.now() - timedelta(hours=window_hours)
        values = []
        timestamps = []
        
        for i, ts in enumerate(self.timestamps[metric_name]):
            if ts > cutoff_time:
                values.append(self.metrics[metric_name][i])
                timestamps.append(ts)
        
        if not values:
            return {'count': 0, 'message': '指定时间窗口内无数据'}
        
        return {
            'count': len(values),
            'mean': np.mean(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values),
            'percentile_25': np.percentile(values, 25),
            'percentile_75': np.percentile(values, 75),
            'trend': self._calculate_trend(values),
            'latest_value': values[-1],
            'latest_timestamp': timestamps[-1].isoformat()
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return 'insufficient_data'
        
        # 简单线性趋势
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        if slope > 0.01:
            return 'improving'
        elif slope < -0.01:
            return 'declining'
        else:
            return 'stable'

class LearningEvaluator:
    """学习评估器：评估学习效果"""
    
    def __init__(self, evaluation_dir: str = "data/learning_evaluation"):
        self.evaluation_dir = evaluation_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = self._setup_logger()
        
        # 学习指标
        self.metrics = LearningMetrics()
        
        # 评估标准
        self.evaluation_criteria = {
            'accuracy_threshold': 0.8,
            'efficiency_threshold': 0.7,
            'adaptability_threshold': 0.6,
            'consistency_threshold': 0.75,
            'learning_speed_threshold': 0.5
        }
        
        # 评估历史
        self.evaluation_history: List[Dict] = []
        
        # 基准性能
        self.performance_baselines: Dict[str, float] = {}
        
        # 加载评估数据
        self._load_evaluation_data()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('learning_evaluator')
        if not logger.handlers:
            handler = logging.FileHandler('logs/learning_evaluation.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _load_evaluation_data(self):
        """加载评估数据"""
        criteria_file = os.path.join(self.evaluation_dir, "evaluation_criteria.json")
        history_file = os.path.join(self.evaluation_dir, "evaluation_history.json")
        baselines_file = os.path.join(self.evaluation_dir, "performance_baselines.json")
        
        try:
            os.makedirs(self.evaluation_dir, exist_ok=True)
            
            if os.path.exists(criteria_file):
                with open(criteria_file, 'r', encoding='utf-8') as f:
                    loaded_criteria = json.load(f)
                    self.evaluation_criteria.update(loaded_criteria)
            
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.evaluation_history = json.load(f)
            
            if os.path.exists(baselines_file):
                with open(baselines_file, 'r', encoding='utf-8') as f:
                    self.performance_baselines = json.load(f)
            
            self.logger.info("学习评估数据加载成功")
            
        except Exception as e:
            self.logger.error(f"加载学习评估数据失败: {e}")
    
    def save_evaluation_data(self):
        """保存评估数据"""
        try:
            os.makedirs(self.evaluation_dir, exist_ok=True)
            
            # 保存评估标准
            criteria_file = os.path.join(self.evaluation_dir, "evaluation_criteria.json")
            with open(criteria_file, 'w', encoding='utf-8') as f:
                json.dump(self.evaluation_criteria, f, ensure_ascii=False, indent=2)
            
            # 保存评估历史
            history_file = os.path.join(self.evaluation_dir, "evaluation_history.json")
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.evaluation_history, f, ensure_ascii=False, indent=2)
            
            # 保存性能基准
            baselines_file = os.path.join(self.evaluation_dir, "performance_baselines.json")
            with open(baselines_file, 'w', encoding='utf-8') as f:
                json.dump(self.performance_baselines, f, ensure_ascii=False, indent=2)
            
            self.logger.info("学习评估数据保存成功")
            
        except Exception as e:
            self.logger.error(f"保存学习评估数据失败: {e}")
    
    def record_learning_metric(self, metric_type: str, value: float, 
                             context: Dict[str, Any] = None):
        """
        记录学习指标
        
        Args:
            metric_type: 指标类型
            value: 指标值
            context: 上下文信息
        """
        self.metrics.record_metric(metric_type, value)
        
        # 记录详细上下文（如果提供）
        if context:
            metric_record = {
                'metric_type': metric_type,
                'value': value,
                'context': context,
                'timestamp': datetime.now().isoformat()
            }
            # 这里可以保存到详细记录中
    
    def evaluate_learning_performance(self, learning_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估学习性能
        
        Args:
            learning_data: 学习数据
            
        Returns:
            性能评估结果
        """
        try:
            # 提取性能指标
            performance_metrics = self._extract_performance_metrics(learning_data)
            
            # 计算综合评分
            overall_score = self._calculate_overall_score(performance_metrics)
            
            # 评估各项能力
            capability_assessment = self._assess_learning_capabilities(performance_metrics)
            
            # 生成改进建议
            improvement_recommendations = self._generate_improvement_recommendations(
                performance_metrics, capability_assessment)
            
            # 与基准比较
            benchmark_comparison = self._compare_with_benchmarks(performance_metrics)
            
            evaluation_result = {
                'evaluation_id': f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'timestamp': datetime.now().isoformat(),
                'overall_score': overall_score,
                'performance_metrics': performance_metrics,
                'capability_assessment': capability_assessment,
                'improvement_recommendations': improvement_recommendations,
                'benchmark_comparison': benchmark_comparison,
                'learning_stage': self._determine_learning_stage(overall_score, performance_metrics)
            }
            
            # 记录评估历史
            self.evaluation_history.append(evaluation_result)
            
            self.logger.info(f"学习性能评估完成: 综合评分 {overall_score:.3f}")
            return evaluation_result
            
        except Exception as e:
            self.logger.error(f"学习性能评估失败: {e}")
            return self._get_fallback_evaluation()
    
    def _extract_performance_metrics(self, learning_data: Dict[str, Any]) -> Dict[str, float]:
        """提取性能指标"""
        metrics = {}
        
        # 准确性指标
        metrics['accuracy'] = learning_data.get('accuracy', 0.0)
        metrics['precision'] = learning_data.get('precision', 0.0)
        metrics['recall'] = learning_data.get('recall', 0.0)
        metrics['f1_score'] = learning_data.get('f1_score', 0.0)
        
        # 效率指标
        metrics['learning_speed'] = learning_data.get('learning_speed', 0.0)
        metrics['response_time'] = 1.0 - min(learning_data.get('avg_response_time', 10.0) / 10.0, 1.0)
        metrics['resource_efficiency'] = learning_data.get('resource_efficiency', 0.5)
        
        # 适应性指标
        metrics['adaptability'] = learning_data.get('adaptability', 0.5)
        metrics['generalization'] = learning_data.get('generalization', 0.5)
        metrics['robustness'] = learning_data.get('robustness', 0.5)
        
        # 一致性指标
        metrics['consistency'] = learning_data.get('consistency', 0.5)
        metrics['stability'] = learning_data.get('stability', 0.5)
        
        return metrics
    
    def _calculate_overall_score(self, performance_metrics: Dict[str, float]) -> float:
        """计算综合评分"""
        weights = {
            'accuracy': 0.25,
            'f1_score': 0.15,
            'learning_speed': 0.15,
            'adaptability': 0.15,
            'consistency': 0.15,
            'resource_efficiency': 0.10,
            'generalization': 0.05
        }
        
        overall_score = 0.0
        for metric, weight in weights.items():
            if metric in performance_metrics:
                overall_score += performance_metrics[metric] * weight
        
        return min(overall_score, 1.0)
    
    def _assess_learning_capabilities(self, performance_metrics: Dict[str, float]) -> Dict[str, Any]:
        """评估学习能力"""
        capabilities = {}
        
        # 知识获取能力
        knowledge_acquisition = (
            performance_metrics.get('accuracy', 0.0) * 0.6 +
            performance_metrics.get('learning_speed', 0.0) * 0.4
        )
        capabilities['knowledge_acquisition'] = {
            'score': knowledge_acquisition,
            'level': self._get_capability_level(knowledge_acquisition),
            'strengths': ['快速学习'] if performance_metrics.get('learning_speed', 0.0) > 0.7 else [],
            'weaknesses': ['学习缓慢'] if performance_metrics.get('learning_speed', 0.0) < 0.3 else []
        }
        
        # 问题解决能力
        problem_solving = (
            performance_metrics.get('f1_score', 0.0) * 0.5 +
            performance_metrics.get('precision', 0.0) * 0.3 +
            performance_metrics.get('recall', 0.0) * 0.2
        )
        capabilities['problem_solving'] = {
            'score': problem_solving,
            'level': self._get_capability_level(problem_solving),
            'strengths': ['精确分析'] if performance_metrics.get('precision', 0.0) > 0.8 else [],
            'weaknesses': ['召回率低'] if performance_metrics.get('recall', 0.0) < 0.5 else []
        }
        
        # 适应能力
        adaptability = (
            performance_metrics.get('adaptability', 0.0) * 0.6 +
            performance_metrics.get('generalization', 0.0) * 0.4
        )
        capabilities['adaptability'] = {
            'score': adaptability,
            'level': self._get_capability_level(adaptability),
            'strengths': ['强泛化能力'] if performance_metrics.get('generalization', 0.0) > 0.7 else [],
            'weaknesses': ['适应慢'] if performance_metrics.get('adaptability', 0.0) < 0.4 else []
        }
        
        # 稳定性
        stability = (
            performance_metrics.get('consistency', 0.0) * 0.5 +
            performance_metrics.get('stability', 0.0) * 0.5
        )
        capabilities['stability'] = {
            'score': stability,
            'level': self._get_capability_level(stability),
            'strengths': ['表现稳定'] if performance_metrics.get('consistency', 0.0) > 0.8 else [],
            'weaknesses': ['波动大'] if performance_metrics.get('stability', 0.0) < 0.4 else []
        }
        
        return capabilities
    
    def _get_capability_level(self, score: float) -> str:
        """获取能力等级"""
        if score >= 0.9:
            return '专家级'
        elif score >= 0.8:
            return '熟练级'
        elif score >= 0.7:
            return '胜任级'
        elif score >= 0.5:
            return '初级'
        else:
            return '新手级'
    
    def _generate_improvement_recommendations(self, performance_metrics: Dict[str, float],
                                           capability_assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成改进建议"""
        recommendations = []
        
        # 准确性改进
        if performance_metrics.get('accuracy', 0.0) < self.evaluation_criteria['accuracy_threshold']:
            recommendations.append({
                'area': '准确性',
                'priority': 'high',
                'suggestion': '增加训练数据多样性，改进特征工程',
                'expected_improvement': '准确性提高10-15%',
                'implementation_difficulty': '中等'
            })
        
        # 效率改进
        if performance_metrics.get('learning_speed', 0.0) < self.evaluation_criteria['learning_speed_threshold']:
            recommendations.append({
                'area': '学习效率',
                'priority': 'medium',
                'suggestion': '优化学习算法参数，实现增量学习',
                'expected_improvement': '学习速度提高20-30%',
                'implementation_difficulty': '低'
            })
        
        # 适应性改进
        if performance_metrics.get('adaptability', 0.0) < self.evaluation_criteria['adaptability_threshold']:
            recommendations.append({
                'area': '适应性',
                'priority': 'high',
                'suggestion': '引入迁移学习和元学习技术',
                'expected_improvement': '适应新任务能力提高25%',
                'implementation_difficulty': '高'
            })
        
        # 如果没有明显问题，提供一般性建议
        if not recommendations:
            recommendations.append({
                'area': '整体优化',
                'priority': 'low',
                'suggestion': '持续监控性能，定期进行模型优化',
                'expected_improvement': '维持当前性能水平',
                'implementation_difficulty': '低'
            })
        
        return recommendations
    
    def _compare_with_benchmarks(self, performance_metrics: Dict[str, float]) -> Dict[str, Any]:
        """与基准比较"""
        comparison = {}
        
        for metric, value in performance_metrics.items():
            baseline = self.performance_baselines.get(metric, 0.5)
            difference = value - baseline
            percentage_diff = (difference / baseline) * 100 if baseline > 0 else 0
            
            comparison[metric] = {
                'current_value': value,
                'baseline_value': baseline,
                'difference': difference,
                'percentage_difference': percentage_diff,
                'status': 'above_baseline' if difference > 0 else 'below_baseline' if difference < 0 else 'at_baseline'
            }
        
        return comparison
    
    def _determine_learning_stage(self, overall_score: float, 
                                performance_metrics: Dict[str, float]) -> str:
        """确定学习阶段"""
        if overall_score >= 0.9:
            return '专家阶段'
        elif overall_score >= 0.8:
            return '熟练阶段'
        elif overall_score >= 0.7:
            return '进阶阶段'
        elif overall_score >= 0.5:
            return '学习阶段'
        else:
            return '初始阶段'
    
    def _get_fallback_evaluation(self) -> Dict[str, Any]:
        """获取回退评估结果"""
        return {
            'evaluation_id': 'fallback',
            'timestamp': datetime.now().isoformat(),
            'overall_score': 0.5,
            'performance_metrics': {},
            'capability_assessment': {},
            'improvement_recommendations': [{
                'area': '系统诊断',
                'priority': 'high',
                'suggestion': '需要完整的性能数据来进行准确评估',
                'expected_improvement': '确定评估方法',
                'implementation_difficulty': '未知'
            }],
            'benchmark_comparison': {},
            'learning_stage': '未知',
            'fallback': True
        }
    
    def set_performance_baseline(self, baseline_name: str, metrics: Dict[str, float]):
        """
        设置性能基准
        
        Args:
            baseline_name: 基准名称
            metrics: 指标数据
        """
        self.performance_baselines.update(metrics)
        self.save_evaluation_data()
        self.logger.info(f"性能基准已设置: {baseline_name}")
    
    def track_learning_progress(self, time_period: str = "7d") -> Dict[str, Any]:
        """
        跟踪学习进度
        
        Args:
            time_period: 时间周期 ('7d', '30d', '90d')
            
        Returns:
            进度跟踪结果
        """
        # 根据时间周期确定小时数
        hours_map = {'7d': 168, '30d': 720, '90d': 2160}
        hours = hours_map.get(time_period, 168)
        
        progress_data = {}
        
        # 获取关键指标的进度
        key_metrics = ['accuracy', 'learning_speed', 'adaptability', 'consistency']
        for metric in key_metrics:
            stats = self.metrics.get_metric_stats(metric, hours)
            progress_data[metric] = stats
        
        # 计算总体进度
        valid_metrics = [data for data in progress_data.values() 
                        if 'mean' in data and data['count'] > 0]
        
        if valid_metrics:
            overall_progress = np.mean([data['mean'] for data in valid_metrics])
            progress_trend = 'improving' if all(data.get('trend') in ['improving', 'stable'] 
                                              for data in valid_metrics) else 'mixed'
        else:
            overall_progress = 0.0
            progress_trend = 'insufficient_data'
        
        progress_report = {
            'time_period': time_period,
            'overall_progress': overall_progress,
            'progress_trend': progress_trend,
            'detailed_metrics': progress_data,
            'tracking_period': f"最近{time_period}",
            'report_generated': datetime.now().isoformat()
        }
        
        return progress_report
    
    def generate_learning_report(self, report_type: str = "comprehensive") -> Dict[str, Any]:
        """
        生成学习报告
        
        Args:
            report_type: 报告类型 ('comprehensive', 'summary', 'technical')
            
        Returns:
            学习报告
        """
        # 获取最近的评估结果
        recent_evaluations = self.evaluation_history[-5:] if self.evaluation_history else []
        
        # 获取进度跟踪
        progress_tracking = self.track_learning_progress("30d")
        
        # 根据报告类型组织内容
        if report_type == "summary":
            report = self._generate_summary_report(recent_evaluations, progress_tracking)
        elif report_type == "technical":
            report = self._generate_technical_report(recent_evaluations, progress_tracking)
        else:  # comprehensive
            report = self._generate_comprehensive_report(recent_evaluations, progress_tracking)
        
        report['report_id'] = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report['report_type'] = report_type
        report['generation_timestamp'] = datetime.now().isoformat()
        
        self.logger.info(f"学习报告生成完成: {report_type}")
        return report
    
    def _generate_summary_report(self, recent_evaluations: List[Dict], 
                               progress_tracking: Dict[str, Any]) -> Dict[str, Any]:
        """生成摘要报告"""
        summary = {
            'executive_summary': {
                'overall_performance': progress_tracking.get('overall_progress', 0.0),
                'performance_trend': progress_tracking.get('progress_trend', 'unknown'),
                'key_strengths': self._identify_key_strengths(recent_evaluations),
                'main_improvement_areas': self._identify_improvement_areas(recent_evaluations)
            },
            'key_metrics': {
                metric: data for metric, data in progress_tracking.get('detailed_metrics', {}).items()
                if 'mean' in data
            },
            'recommendations': self._get_priority_recommendations(recent_evaluations)
        }
        
        return summary
    
    def _generate_technical_report(self, recent_evaluations: List[Dict],
                                 progress_tracking: Dict[str, Any]) -> Dict[str, Any]:
        """生成技术报告"""
        technical = {
            'performance_analysis': {
                'metric_trends': progress_tracking.get('detailed_metrics', {}),
                'capability_assessment': recent_evaluations[-1].get('capability_assessment', {}) 
                                      if recent_evaluations else {},
                'benchmark_comparison': recent_evaluations[-1].get('benchmark_comparison', {}) 
                                      if recent_evaluations else {}
            },
            'learning_metrics': {
                'total_evaluations': len(self.evaluation_history),
                'evaluation_frequency': self._calculate_evaluation_frequency(),
                'performance_consistency': self._calculate_performance_consistency()
            },
            'detailed_recommendations': self._get_detailed_recommendations(recent_evaluations)
        }
        
        return technical
    
    def _generate_comprehensive_report(self, recent_evaluations: List[Dict],
                                     progress_tracking: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合报告"""
        comprehensive = {
            'executive_summary': self._generate_summary_report(recent_evaluations, progress_tracking)['executive_summary'],
            'technical_analysis': self._generate_technical_report(recent_evaluations, progress_tracking)['performance_analysis'],
            'progress_analytics': {
                'learning_velocity': self._calculate_learning_velocity(),
                'skill_acquisition_rate': self._calculate_skill_acquisition_rate(),
                'adaptation_efficiency': self._calculate_adaptation_efficiency()
            },
            'strategic_recommendations': self._get_strategic_recommendations(recent_evaluations),
            'appendix': {
                'evaluation_history_summary': self._summarize_evaluation_history(),
                'metric_definitions': self._get_metric_definitions()
            }
        }
        
        return comprehensive
    
    def _identify_key_strengths(self, recent_evaluations: List[Dict]) -> List[str]:
        """识别关键优势"""
        if not recent_evaluations:
            return ['需要更多评估数据']
        
        latest_eval = recent_evaluations[-1]
        capabilities = latest_eval.get('capability_assessment', {})
        
        strengths = []
        for cap_name, cap_data in capabilities.items():
            if cap_data.get('score', 0.0) > 0.8:
                strengths.append(f"{cap_name}能力突出")
        
        return strengths if strengths else ['表现均衡']
    
    def _identify_improvement_areas(self, recent_evaluations: List[Dict]) -> List[str]:
        """识别改进领域"""
        if not recent_evaluations:
            return ['需要更多评估数据']
        
        latest_eval = recent_evaluations[-1]
        capabilities = latest_eval.get('capability_assessment', {})
        
        improvements = []
        for cap_name, cap_data in capabilities.items():
            if cap_data.get('score', 0.0) < 0.6:
                improvements.append(f"{cap_name}需要提升")
        
        return improvements if improvements else ['维持当前水平']
    
    def _get_priority_recommendations(self, recent_evaluations: List[Dict]) -> List[Dict[str, Any]]:
        """获取优先级建议"""
        if not recent_evaluations:
            return []
        
        latest_eval = recent_evaluations[-1]
        recommendations = latest_eval.get('improvement_recommendations', [])
        
        # 只返回高优先级建议
        return [rec for rec in recommendations if rec.get('priority') == 'high']
    
    def _calculate_evaluation_frequency(self) -> str:
        """计算评估频率"""
        if len(self.evaluation_history) < 2:
            return 'low'
        
        # 计算平均评估间隔
        intervals = []
        for i in range(1, len(self.evaluation_history)):
            current_ts = datetime.fromisoformat(self.evaluation_history[i]['timestamp'])
            previous_ts = datetime.fromisoformat(self.evaluation_history[i-1]['timestamp'])
            interval_hours = (current_ts - previous_ts).total_seconds() / 3600
            intervals.append(interval_hours)
        
        avg_interval = np.mean(intervals)
        
        if avg_interval < 24:
            return 'high'
        elif avg_interval < 168:  # 一周
            return 'medium'
        else:
            return 'low'
    
    def _calculate_performance_consistency(self) -> float:
        """计算性能一致性"""
        if len(self.evaluation_history) < 3:
            return 0.5
        
        scores = [eval_data.get('overall_score', 0.0) for eval_data in self.evaluation_history]
        consistency = 1.0 - (np.std(scores) / 0.5)  # 标准化到0-1
        
        return max(0.0, min(consistency, 1.0))
    
    def _get_detailed_recommendations(self, recent_evaluations: List[Dict]) -> List[Dict[str, Any]]:
        """获取详细建议"""
        if not recent_evaluations:
            return []
        
        # 合并最近几次评估的建议
        all_recommendations = []
        for eval_data in recent_evaluations[-3:]:  # 最近3次评估
            recommendations = eval_data.get('improvement_recommendations', [])
            all_recommendations.extend(recommendations)
        
        # 去重并排序
        unique_recommendations = {}
        for rec in all_recommendations:
            area = rec.get('area')
            if area not in unique_recommendations or rec.get('priority') == 'high':
                unique_recommendations[area] = rec
        
        return list(unique_recommendations.values())
    
    def _calculate_learning_velocity(self) -> float:
        """计算学习速度"""
        if len(self.evaluation_history) < 2:
            return 0.5
        
        # 分析整体评分的变化率
        scores = [eval_data.get('overall_score', 0.0) for eval_data in self.evaluation_history]
        if len(scores) >= 2:
            improvement = scores[-1] - scores[0]
            time_span = len(scores)  # 用评估次数近似时间
            velocity = improvement / time_span
        else:
            velocity = 0.0
        
        return min(max(velocity, 0.0), 1.0)
    
    def _calculate_skill_acquisition_rate(self) -> float:
        """计算技能获取速率"""
        # 分析能力得分的提升速度
        if len(self.evaluation_history) < 2:
            return 0.5
        
        capability_improvements = []
        for i in range(1, len(self.evaluation_history)):
            current_caps = self.evaluation_history[i].get('capability_assessment', {})
            previous_caps = self.evaluation_history[i-1].get('capability_assessment', {})
            
            for cap_name in current_caps:
                if cap_name in previous_caps:
                    improvement = (current_caps[cap_name].get('score', 0.0) - 
                                 previous_caps[cap_name].get('score', 0.0))
                    capability_improvements.append(improvement)
        
        if capability_improvements:
            avg_improvement = np.mean(capability_improvements)
        else:
            avg_improvement = 0.0
        
        return min(max(avg_improvement * 10, 0.0), 1.0)  # 放大并标准化
    
    def _calculate_adaptation_efficiency(self) -> float:
        """计算适应效率"""
        # 分析适应新环境或任务的速度
        # 简化实现：使用学习速度作为代理指标
        speed_metric = self.metrics.get_metric_stats('learning_speed', 720)  # 30天
        if 'mean' in speed_metric:
            return speed_metric['mean']
        else:
            return 0.5
    
    def _get_strategic_recommendations(self, recent_evaluations: List[Dict]) -> List[Dict[str, Any]]:
        """获取战略性建议"""
        strategic_recs = []
        
        # 基于长期趋势的建议
        learning_velocity = self._calculate_learning_velocity()
        if learning_velocity < 0.1:
            strategic_recs.append({
                'type': 'learning_strategy',
                'timeframe': 'long_term',
                'recommendation': '考虑改变学习策略或增加训练资源',
                'rationale': f'当前学习速度较慢 ({learning_velocity:.3f})',
                'impact': 'high'
            })
        
        # 基于能力平衡的建议
        if recent_evaluations:
            latest_caps = recent_evaluations[-1].get('capability_assessment', {})
            cap_scores = [data.get('score', 0.0) for data in latest_caps.values()]
            if cap_scores and max(cap_scores) - min(cap_scores) > 0.3:
                strategic_recs.append({
                    'type': 'capability_balance',
                    'timeframe': 'medium_term',
                    'recommendation': '关注能力均衡发展，避免单一能力过度优化',
                    'rationale': '能力发展不均衡',
                    'impact': 'medium'
                })
        
        return strategic_recs
    
    def _summarize_evaluation_history(self) -> Dict[str, Any]:
        """总结评估历史"""
        if not self.evaluation_history:
            return {'message': '尚无评估历史'}
        
        scores = [eval_data.get('overall_score', 0.0) for eval_data in self.evaluation_history]
        
        return {
            'total_evaluations': len(self.evaluation_history),
            'average_score': np.mean(scores),
            'best_score': np.max(scores),
            'worst_score': np.min(scores),
            'score_trend': 'improving' if scores[-1] > scores[0] else 'declining' if scores[-1] < scores[0] else 'stable',
            'evaluation_period_days': self._get_evaluation_period_days()
        }
    
    def _get_evaluation_period_days(self) -> int:
        """获取评估周期天数"""
        if len(self.evaluation_history) < 2:
            return 0
        
        first_ts = datetime.fromisoformat(self.evaluation_history[0]['timestamp'])
        last_ts = datetime.fromisoformat(self.evaluation_history[-1]['timestamp'])
        
        return (last_ts - first_ts).days
    
    def _get_metric_definitions(self) -> Dict[str, str]:
        """获取指标定义"""
        return {
            'accuracy': '任务完成的精确程度',
            'learning_speed': '学习新知识或技能的速度',
            'adaptability': '适应新环境或变化的能力',
            'consistency': '性能表现的稳定程度',
            'generalization': '将学到的知识应用到新情境的能力',
            'resource_efficiency': '资源使用效率'
        }
    
    def update_evaluation_criteria(self, new_criteria: Dict[str, Any]):
        """更新评估标准"""
        self.evaluation_criteria.update(new_criteria)
        self.save_evaluation_data()
        self.logger.info("学习评估标准已更新")

# 全局学习评估器实例
_global_learning_evaluator: Optional[LearningEvaluator] = None

def get_learning_evaluator() -> LearningEvaluator:
    """获取全局学习评估器实例"""
    global _global_learning_evaluator
    if _global_learning_evaluator is None:
        _global_learning_evaluator = LearningEvaluator()
    return _global_learning_evaluator

