"""
数据处理模块

提供数据处理相关的工具函数，包括数据清洗、转换、特征工程、采样、验证、格式化、序列化、分析等。
"""

from .data_cleaning import (
    DataCleaner, TextCleaner, DataValidator, DataProfiler,
    OutlierDetector, MissingValueHandler, DuplicateHandler,
    DataTypeConverter, DataStandardizer
)

from .data_transformation import (
    DataTransformer, DataNormalizer, DataEncoder,
    create_polynomial_features, create_interaction_features,
    create_aggregation_features, create_time_features,
    create_text_features, create_statistical_features,
    create_categorical_features, create_cluster_features,
    create_binning_features, transform_pipeline, inverse_transform
)

from .feature_engineering import (
    FeatureEngineer, FeatureGenerator, FeatureSelector,
    FeatureExtractor, FeatureScaler, FeatureTransformer,
    create_interaction_features as fe_create_interaction,
    create_polynomial_features as fe_create_polynomial,
    create_aggregation_features as fe_create_aggregation,
    create_time_features as fe_create_time,
    create_text_features as fe_create_text,
    create_statistical_features as fe_create_statistical,
    create_cluster_features as fe_create_cluster,
    create_binning_features as fe_create_binning,
    select_features_by_importance, select_features_by_correlation,
    select_features_by_variance, select_features_by_mutual_info,
    create_feature_pipeline
)

from .data_sampling import (
    DataSampler, RandomSampler, StratifiedSampler,
    SystematicSampler, ClusterSampler, ReservoirSampler,
    TimeBasedSampler, WeightedSampler, DiversitySampler,
    train_test_split_sample, bootstrap_sample,
    cross_validation_sample, progressive_sample,
    create_sample_weights, balance_dataset
)

from .data_validation import (
    DataValidator as DataValidatorMain,
    SchemaValidator, BusinessRuleValidator,
    QualityValidator, CrossReferenceValidator,
    validate_email_format, validate_phone_format,
    validate_url_format, validate_date_range,
    validate_numeric_range, validate_categorical_values,
    validate_data_types, validate_completeness,
    validate_uniqueness, validate_consistency,
    generate_validation_report
)

from .data_formatting import (
    DataFormatter, NumberFormatter, CurrencyFormatter,
    PercentageFormatter, DateFormatter, TextFormatter,
    CategoryFormatter, JSONFormatter, XMLFormatter,
    HTMLFormatter, ExcelFormatter, ReportFormatter,
    format_for_export, create_pivot_table,
    clean_and_format_data, format_report_data
)

from .data_serialization import (
    DataSerializer, JSONSerializer, XMLSerializer,
    YAMLSerializer, PickleSerializer, ParquetSerializer,
    CSVSerializer, Base64Serializer, save_data, load_data,
    compress_file, decompress_file, detect_format,
    serialize_to_bytes, deserialize_from_bytes
)

from .data_analysis import (
    DataAnalyzer, StatisticalAnalyzer, CorrelationAnalyzer,
    DistributionAnalyzer, TrendAnalyzer, SegmentAnalyzer,
    PatternDetector, OutlierAnalyzer, QualityAnalyzer,
    quick_analysis, analyze_data_quality, detect_data_patterns,
    compare_datasets, generate_analysis_report,
    calculate_summary_statistics, calculate_correlation_matrix,
    calculate_distribution_stats, detect_anomalies
)

from .data_metrics import (
    DataMetrics, QualityMetrics, CompletenessMetrics,
    UniquenessMetrics, ValidityMetrics, ConsistencyMetrics,
    AccuracyMetrics, TimelinessMetrics, calculate_data_quality_score,
    calculate_column_statistics, benchmark_data_quality,
    generate_quality_report, track_quality_over_time
)

__all__ = [
    # Data Cleaning
    'DataCleaner', 'TextCleaner', 'DataValidator', 'DataProfiler',
    'OutlierDetector', 'MissingValueHandler', 'DuplicateHandler',
    'DataTypeConverter', 'DataStandardizer',
    
    # Data Transformation
    'DataTransformer', 'DataNormalizer', 'DataEncoder',
    'create_polynomial_features', 'create_interaction_features',
    'create_aggregation_features', 'create_time_features',
    'create_text_features', 'create_statistical_features',
    'create_categorical_features', 'create_cluster_features',
    'create_binning_features', 'transform_pipeline', 'inverse_transform',
    
    # Feature Engineering
    'FeatureEngineer', 'FeatureGenerator', 'FeatureSelector',
    'FeatureExtractor', 'FeatureScaler', 'FeatureTransformer',
    'fe_create_interaction', 'fe_create_polynomial',
    'fe_create_aggregation', 'fe_create_time',
    'fe_create_text', 'fe_create_statistical',
    'fe_create_cluster', 'fe_create_binning',
    'select_features_by_importance', 'select_features_by_correlation',
    'select_features_by_variance', 'select_features_by_mutual_info',
    'create_feature_pipeline',
    
    # Data Sampling
    'DataSampler', 'RandomSampler', 'StratifiedSampler',
    'SystematicSampler', 'ClusterSampler', 'ReservoirSampler',
    'TimeBasedSampler', 'WeightedSampler', 'DiversitySampler',
    'train_test_split_sample', 'bootstrap_sample',
    'cross_validation_sample', 'progressive_sample',
    'create_sample_weights', 'balance_dataset',
    
    # Data Validation
    'DataValidatorMain', 'SchemaValidator', 'BusinessRuleValidator',
    'QualityValidator', 'CrossReferenceValidator',
    'validate_email_format', 'validate_phone_format',
    'validate_url_format', 'validate_date_range',
    'validate_numeric_range', 'validate_categorical_values',
    'validate_data_types', 'validate_completeness',
    'validate_uniqueness', 'validate_consistency',
    'generate_validation_report',
    
    # Data Formatting
    'DataFormatter', 'NumberFormatter', 'CurrencyFormatter',
    'PercentageFormatter', 'DateFormatter', 'TextFormatter',
    'CategoryFormatter', 'JSONFormatter', 'XMLFormatter',
    'HTMLFormatter', 'ExcelFormatter', 'ReportFormatter',
    'format_for_export', 'create_pivot_table',
    'clean_and_format_data', 'format_report_data',
    
    # Data Serialization
    'DataSerializer', 'JSONSerializer', 'XMLSerializer',
    'YAMLSerializer', 'PickleSerializer', 'ParquetSerializer',
    'CSVSerializer', 'Base64Serializer', 'save_data', 'load_data',
    'compress_file', 'decompress_file', 'detect_format',
    'serialize_to_bytes', 'deserialize_from_bytes',
    
    # Data Analysis
    'DataAnalyzer', 'StatisticalAnalyzer', 'CorrelationAnalyzer',
    'DistributionAnalyzer', 'TrendAnalyzer', 'SegmentAnalyzer',
    'PatternDetector', 'OutlierAnalyzer', 'QualityAnalyzer',
    'quick_analysis', 'analyze_data_quality', 'detect_data_patterns',
    'compare_datasets', 'generate_analysis_report',
    'calculate_summary_statistics', 'calculate_correlation_matrix',
    'calculate_distribution_stats', 'detect_anomalies',
    
    # Data Metrics
    'DataMetrics', 'QualityMetrics', 'CompletenessMetrics',
    'UniquenessMetrics', 'ValidityMetrics', 'ConsistencyMetrics',
    'AccuracyMetrics', 'TimelinessMetrics', 'calculate_data_quality_score',
    'calculate_column_statistics', 'benchmark_data_quality',
    'generate_quality_report', 'track_quality_over_time'
]