"""
创意内容生成套件
提供文档、演示文稿、表格、图像、音乐等内容的生成和优化功能
"""

from .document_generator import (
    DocumentGenerator, 
    DocumentConfig, 
    GeneratedDocument,
    get_document_generator
)

from .presentation_generator import (
    PresentationGenerator,
    PresentationConfig,
    GeneratedPresentation,
    SlideType,
    SlideLayout,
    get_presentation_generator
)

from .spreadsheet_generator import (
    SpreadsheetGenerator,
    SpreadsheetConfig,
    GeneratedSpreadsheet,
    DataType,
    ColumnDefinition,
    get_spreadsheet_generator
)

from .image_generator import (
    ImageGenerator,
    ImageGenerationConfig,
    GeneratedImage,
    ImageStyle,
    ImageSize,
    get_image_generator
)

from .music_generator import (
    MusicGenerator,
    MusicConfig,
    GeneratedMusic,
    MusicGenre,
    InstrumentType,
    get_music_generator
)

from .content_refiner import (
    ContentRefiner,
    RefinementConfig,
    RefinementResult,
    RefinementType,
    get_content_refiner
)

from .revision_manager import (
    RevisionManager,
    Revision,
    RevisionConfig,
    RevisionAction,
    RevisionStatus,
    get_revision_manager
)

from .template_engine import (
    TemplateEngine,
    Template,
    TemplateConfig,
    TemplateType,
    TemplateVariable,
    get_template_engine
)

from .style_transfer import (
    StyleTransfer,
    StyleTransferConfig,
    StyleTransferResult,
    WritingStyle,
    get_style_transfer
)

from .creative_constraints import (
    CreativeConstraints,
    ConstraintCheckResult,
    ConstraintType,
    ConstraintSeverity,
    BrandGuidelines,
    get_creative_constraints
)

from .quality_evaluator import (
    QualityEvaluator,
    QualityEvaluationResult,
    QualityDimension,
    QualityScore,
    get_quality_evaluator
)

from .creative_metrics import (
    CreativeMetrics,
    CreativeMetric,
    PerformanceReport,
    MetricType,
    get_creative_metrics
)

__all__ = [
    # 文档生成
    "DocumentGenerator",
    "DocumentConfig", 
    "GeneratedDocument",
    "get_document_generator",
    
    # 演示文稿生成
    "PresentationGenerator",
    "PresentationConfig",
    "GeneratedPresentation", 
    "SlideType",
    "SlideLayout",
    "get_presentation_generator",
    
    # 表格生成
    "SpreadsheetGenerator",
    "SpreadsheetConfig",
    "GeneratedSpreadsheet",
    "DataType", 
    "ColumnDefinition",
    "get_spreadsheet_generator",
    
    # 图像生成
    "ImageGenerator",
    "ImageGenerationConfig",
    "GeneratedImage",
    "ImageStyle",
    "ImageSize", 
    "get_image_generator",
    
    # 音乐生成
    "MusicGenerator",
    "MusicConfig",
    "GeneratedMusic",
    "MusicGenre",
    "InstrumentType",
    "get_music_generator",
    
    # 内容精炼
    "ContentRefiner",
    "RefinementConfig",
    "RefinementResult", 
    "RefinementType",
    "get_content_refiner",
    
    # 修订管理
    "RevisionManager",
    "Revision",
    "RevisionConfig",
    "RevisionAction",
    "RevisionStatus", 
    "get_revision_manager",
    
    # 模板引擎
    "TemplateEngine",
    "Template",
    "TemplateConfig",
    "TemplateType",
    "TemplateVariable",
    "get_template_engine",
    
    # 风格迁移
    "StyleTransfer", 
    "StyleTransferConfig",
    "StyleTransferResult",
    "WritingStyle",
    "get_style_transfer",
    
    # 创意约束
    "CreativeConstraints",
    "ConstraintCheckResult",
    "ConstraintType",
    "ConstraintSeverity",
    "BrandGuidelines",
    "get_creative_constraints",
    
    # 质量评估
    "QualityEvaluator",
    "QualityEvaluationResult", 
    "QualityDimension",
    "QualityScore",
    "get_quality_evaluator",
    
    # 创意指标
    "CreativeMetrics",
    "CreativeMetric",
    "PerformanceReport",
    "MetricType",
    "get_creative_metrics"
]

__version__ = "1.0.0"
__author__ = "Mirexs AI Team"
__description__ = "创意内容生成套件 - 提供全方位的AI驱动内容创作能力"
