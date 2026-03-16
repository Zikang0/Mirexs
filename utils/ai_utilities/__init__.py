"""
AI工具模块

提供人工智能和机器学习相关的工具函数和类，包括模型管理、数据预处理、训练、推理、评估、可视化等。
"""

from .model_utils import (
    ModelRegistry, ModelLoader, ModelSaver, ModelVersionManager,
    ModelValidator, ModelMetrics, ModelComparison, ModelDeployment,
    ModelInfo, ModelArchitecture, ModelConverter, ModelOptimizer,
    create_model_summary, get_model_size, count_parameters
)

from .preprocessing_utils import (
    TextPreprocessor, ImagePreprocessor, NumericalPreprocessor,
    CategoricalPreprocessor, FeatureEngineering, DataCleaner,
    PipelinePreprocessor, DataNormalizer, DataEncoder,
    FeatureSelector, DimensionalityReducer, OutlierDetector,
    MissingValueHandler, create_preprocessing_pipeline,
    DataSplitter, DataBalancer, SequencePreprocessor,
    AudioPreprocessor, TimeSeriesPreprocessor
)

from .training_utils import (
    TorchTrainer, TensorFlowTrainer, EarlyStopping,
    LearningRateScheduler, ModelCheckpoint, TrainingMonitor,
    GradientClipper, LearningRateWarmup, CyclicLR,
    create_data_loader, save_training_config, load_training_config,
    TrainingHistory, ExperimentTracker, HyperparameterTuner
)

from .inference_utils import (
    ModelWrapper, BatchPredictor, InferenceOptimizer,
    ModelProfiler, ModelQuantizer, ModelCompiler,
    create_model_from_config, ONNXInferenceEngine,
    TensorRTInferenceEngine, OpenVINOInferenceEngine,
    PredictionExplainer, ModelServer, InferencePipeline
)

from .evaluation_utils import (
    ModelEvaluator, CrossValidator, ModelComparison,
    ClassificationEvaluator, RegressionEvaluator,
    ClusteringEvaluator, RankingEvaluator,
    TimeSeriesEvaluator, generate_evaluation_report,
    plot_confusion_matrix, plot_roc_curve, plot_precision_recall_curve,
    calculate_bias_metrics, calculate_fairness_metrics
)

from .visualization_utils import (
    ModelVisualizer, DataVisualizer, InteractiveVisualizer,
    FeatureVisualizer, PredictionVisualizer, TrainingVisualizer,
    create_dashboard, plot_learning_curves, plot_feature_importance,
    plot_correlation_matrix, plot_pca_variance, plot_tsne,
    plot_umap, plot_shap_values, plot_lime_explanation
)

from .hyperparameter_utils import (
    HyperparameterOptimizer, ParameterSpaceBuilder,
    OptimizationAnalyzer, GridSearchOptimizer, RandomSearchOptimizer,
    BayesianOptimizer, GeneticOptimizer, create_common_param_spaces,
    HyperbandOptimizer, BOHBOptimizer, TPEOptimizer
)

from .data_augmentation import (
    ImageAugmentation, TextAugmentation, AudioAugmentation,
    TimeSeriesAugmentation, TabularAugmentation,
    DataAugmentationPipeline, MixupAugmentation, CutmixAugmentation,
    create_augmentation_pipeline
)

from .ai_metrics import (
    AIMetrics, ModelPerformanceMetrics, DataQualityMetrics,
    ClassificationMetrics, RegressionMetrics, ClusteringMetrics,
    RankingMetrics, FairnessMetrics, BiasMetrics,
    calculate_model_drift, calculate_data_drift,
    calculate_concept_drift, calculate_feature_importance
)

__all__ = [
    # Model utilities
    'ModelRegistry', 'ModelLoader', 'ModelSaver', 'ModelVersionManager',
    'ModelValidator', 'ModelMetrics', 'ModelComparison', 'ModelDeployment',
    'ModelInfo', 'ModelArchitecture', 'ModelConverter', 'ModelOptimizer',
    'create_model_summary', 'get_model_size', 'count_parameters',
    
    # Preprocessing utilities
    'TextPreprocessor', 'ImagePreprocessor', 'NumericalPreprocessor',
    'CategoricalPreprocessor', 'FeatureEngineering', 'DataCleaner',
    'PipelinePreprocessor', 'DataNormalizer', 'DataEncoder',
    'FeatureSelector', 'DimensionalityReducer', 'OutlierDetector',
    'MissingValueHandler', 'create_preprocessing_pipeline',
    'DataSplitter', 'DataBalancer', 'SequencePreprocessor',
    'AudioPreprocessor', 'TimeSeriesPreprocessor',
    
    # Training utilities
    'TorchTrainer', 'TensorFlowTrainer', 'EarlyStopping',
    'LearningRateScheduler', 'ModelCheckpoint', 'TrainingMonitor',
    'GradientClipper', 'LearningRateWarmup', 'CyclicLR',
    'create_data_loader', 'save_training_config', 'load_training_config',
    'TrainingHistory', 'ExperimentTracker', 'HyperparameterTuner',
    
    # Inference utilities
    'ModelWrapper', 'BatchPredictor', 'InferenceOptimizer',
    'ModelProfiler', 'ModelQuantizer', 'ModelCompiler',
    'create_model_from_config', 'ONNXInferenceEngine',
    'TensorRTInferenceEngine', 'OpenVINOInferenceEngine',
    'PredictionExplainer', 'ModelServer', 'InferencePipeline',
    
    # Evaluation utilities
    'ModelEvaluator', 'CrossValidator', 'ModelComparison',
    'ClassificationEvaluator', 'RegressionEvaluator',
    'ClusteringEvaluator', 'RankingEvaluator',
    'TimeSeriesEvaluator', 'generate_evaluation_report',
    'plot_confusion_matrix', 'plot_roc_curve', 'plot_precision_recall_curve',
    'calculate_bias_metrics', 'calculate_fairness_metrics',
    
    # Visualization utilities
    'ModelVisualizer', 'DataVisualizer', 'InteractiveVisualizer',
    'FeatureVisualizer', 'PredictionVisualizer', 'TrainingVisualizer',
    'create_dashboard', 'plot_learning_curves', 'plot_feature_importance',
    'plot_correlation_matrix', 'plot_pca_variance', 'plot_tsne',
    'plot_umap', 'plot_shap_values', 'plot_lime_explanation',
    
    # Hyperparameter utilities
    'HyperparameterOptimizer', 'ParameterSpaceBuilder',
    'OptimizationAnalyzer', 'GridSearchOptimizer', 'RandomSearchOptimizer',
    'BayesianOptimizer', 'GeneticOptimizer', 'create_common_param_spaces',
    'HyperbandOptimizer', 'BOHBOptimizer', 'TPEOptimizer',
    
    # Data augmentation
    'ImageAugmentation', 'TextAugmentation', 'AudioAugmentation',
    'TimeSeriesAugmentation', 'TabularAugmentation',
    'DataAugmentationPipeline', 'MixupAugmentation', 'CutmixAugmentation',
    'create_augmentation_pipeline',
    
    # AI Metrics
    'AIMetrics', 'ModelPerformanceMetrics', 'DataQualityMetrics',
    'ClassificationMetrics', 'RegressionMetrics', 'ClusteringMetrics',
    'RankingMetrics', 'FairnessMetrics', 'BiasMetrics',
    'calculate_model_drift', 'calculate_data_drift',
    'calculate_concept_drift', 'calculate_feature_importance'
]