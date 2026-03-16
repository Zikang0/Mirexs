"""
ETL引擎：提取、转换、加载数据
负责完整的数据提取、转换和加载流程管理
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

class TransformationStep(Enum):
    """转换步骤枚举"""
    EXTRACT = "extract"
    TRANSFORM = "transform" 
    LOAD = "load"
    VALIDATE = "validate"
    ENRICH = "enrich"
    AGGREGATE = "aggregate"

@dataclass
class ETLPipeline:
    """ETL管道配置"""
    pipeline_id: str
    name: str
    description: str
    source_config: Dict[str, Any]
    transformation_steps: List[TransformationStep]
    destination_config: Dict[str, Any]
    schedule: str = "manual"  # cron表达式或manual
    enabled: bool = True

@dataclass
class ETLResult:
    """ETL执行结果"""
    pipeline_id: str
    execution_id: str
    start_time: datetime
    end_time: datetime
    records_processed: int
    records_successful: int
    records_failed: int
    execution_time: float
    status: str  # success, failed, partial
    errors: List[str]

class ETLEngine:
    """ETL引擎"""
    
    def __init__(self):
        self.pipelines: Dict[str, ETLPipeline] = {}
        self.execution_history: Dict[str, List[ETLResult]] = {}
        self.custom_transforms: Dict[str, Callable] = {}
        self.initialized = False
        
    async def initialize(self):
        """初始化ETL引擎"""
        if self.initialized:
            return
            
        logging.info("初始化ETL引擎...")
        
        # 注册内置转换函数
        await self._register_builtin_transforms()
        
        self.initialized = True
        logging.info("ETL引擎初始化完成")
    
    async def _register_builtin_transforms(self):
        """注册内置转换函数"""
        self.register_transform("lowercase", self._transform_lowercase)
        self.register_transform("uppercase", self._transform_uppercase)
        self.register_transform("trim", self._transform_trim)
        self.register_transform("date_format", self._transform_date_format)
        self.register_transform("numeric_cast", self._transform_numeric_cast)
    
    def register_pipeline(self, pipeline: ETLPipeline) -> bool:
        """注册ETL管道"""
        if pipeline.pipeline_id in self.pipelines:
            logging.warning(f"ETL管道已存在: {pipeline.pipeline_id}")
            return False
        
        self.pipelines[pipeline.pipeline_id] = pipeline
        self.execution_history[pipeline.pipeline_id] = []
        
        logging.info(f"ETL管道注册成功: {pipeline.name} ({pipeline.pipeline_id})")
        return True
    
    def register_transform(self, name: str, transform_func: Callable):
        """注册自定义转换函数"""
        self.custom_transforms[name] = transform_func
        logging.debug(f"转换函数注册: {name}")
    
    async def execute_pipeline(self, pipeline_id: str, data: List[Dict[str, Any]] = None) -> ETLResult:
        """执行ETL管道"""
        if pipeline_id not in self.pipelines:
            raise ValueError(f"ETL管道不存在: {pipeline_id}")
        
        pipeline = self.pipelines[pipeline_id]
        execution_id = f"{pipeline_id}_{int(datetime.now().timestamp())}"
        start_time = datetime.now()
        
        logging.info(f"开始执行ETL管道: {pipeline.name}")
        
        try:
            # 提取阶段
            if data is None:
                data = await self._extract_data(pipeline.source_config)
            
            extracted_count = len(data)
            logging.info(f"数据提取完成: {extracted_count} 条记录")
            
            # 转换阶段
            transformed_data = await self._transform_data(data, pipeline.transformation_steps, pipeline.source_config)
            transformed_count = len(transformed_data)
            logging.info(f"数据转换完成: {transformed_count} 条记录")
            
            # 加载阶段
            loaded_count = await self._load_data(transformed_data, pipeline.destination_config)
            logging.info(f"数据加载完成: {loaded_count} 条记录")
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            result = ETLResult(
                pipeline_id=pipeline_id,
                execution_id=execution_id,
                start_time=start_time,
                end_time=end_time,
                records_processed=extracted_count,
                records_successful=loaded_count,
                records_failed=extracted_count - loaded_count,
                execution_time=execution_time,
                status="success" if loaded_count == extracted_count else "partial",
                errors=[]
            )
            
        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            logging.error(f"ETL管道执行失败: {e}")
            
            result = ETLResult(
                pipeline_id=pipeline_id,
                execution_id=execution_id,
                start_time=start_time,
                end_time=end_time,
                records_processed=0,
                records_successful=0,
                records_failed=0,
                execution_time=execution_time,
                status="failed",
                errors=[str(e)]
            )
        
        # 保存执行结果
        self.execution_history[pipeline_id].append(result)
        
        # 限制历史记录大小
        if len(self.execution_history[pipeline_id]) > 100:
            self.execution_history[pipeline_id].pop(0)
        
        return result
    
    async def _extract_data(self, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取数据"""
        source_type = source_config.get("type", "memory")
        
        if source_type == "memory":
            return source_config.get("data", [])
        elif source_type == "file":
            return await self._extract_from_file(source_config)
        elif source_type == "api":
            return await self._extract_from_api(source_config)
        elif source_type == "database":
            return await self._extract_from_database(source_config)
        else:
            raise ValueError(f"不支持的数据源类型: {source_type}")
    
    async def _extract_from_file(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从文件提取数据"""
        file_path = config.get("path")
        file_format = config.get("format", "json")
        
        try:
            if file_format == "json":
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            elif file_format == "csv":
                import pandas as pd
                df = pd.read_csv(file_path)
                data = df.to_dict('records')
            else:
                raise ValueError(f"不支持的文件格式: {file_format}")
            
            return data if isinstance(data, list) else [data]
            
        except Exception as e:
            logging.error(f"文件数据提取失败: {e}")
            raise
    
    async def _extract_from_api(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从API提取数据"""
        # 使用data_ingestion模块
        from .data_ingestion import data_ingestion, IngestionConfig, DataSource
        
        ingestion_config = IngestionConfig(
            source_type=DataSource.API_REST,
            source_uri=config.get("url"),
            headers=config.get("headers"),
            timeout=config.get("timeout", 30)
        )
        
        result = await data_ingestion.ingest_data(ingestion_config)
        return result.data_sample if result.successful_records > 0 else []
    
    async def _extract_from_database(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从数据库提取数据"""
        # 模拟数据库查询
        query = config.get("query", "SELECT * FROM table")
        logging.info(f"执行数据库查询: {query}")
        
        # 返回模拟数据
        return [
            {"id": 1, "name": "数据库记录1", "value": 100},
            {"id": 2, "name": "数据库记录2", "value": 200},
            {"id": 3, "name": "数据库记录3", "value": 300}
        ]
    
    async def _transform_data(self, data: List[Dict[str, Any]], steps: List[TransformationStep], 
                            config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """转换数据"""
        transformed_data = data.copy()
        
        for step in steps:
            if step == TransformationStep.TRANSFORM:
                transformed_data = await self._apply_transformations(transformed_data, config)
            elif step == TransformationStep.VALIDATE:
                transformed_data = await self._validate_data(transformed_data, config)
            elif step == TransformationStep.ENRICH:
                transformed_data = await self._enrich_data(transformed_data, config)
            elif step == TransformationStep.AGGREGATE:
                transformed_data = await self._aggregate_data(transformed_data, config)
        
        return transformed_data
    
    async def _apply_transformations(self, data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """应用数据转换"""
        transformations = config.get("transformations", [])
        
        for transform_config in transformations:
            transform_type = transform_config.get("type")
            transform_params = transform_config.get("params", {})
            
            if transform_type in self.custom_transforms:
                transform_func = self.custom_transforms[transform_type]
                data = [transform_func(record, transform_params) for record in data]
            else:
                logging.warning(f"未知的转换类型: {transform_type}")
        
        return data
    
    async def _validate_data(self, data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """验证数据"""
        # 使用data_validator模块
        from .data_validator import data_validator, ValidationRule
        
        validation_rules = config.get("validation_rules", [])
        validated_data = []
        
        for record in data:
            is_valid = True
            for rule_config in validation_rules:
                rule = ValidationRule(
                    field=rule_config.get("field"),
                    rule_type=rule_config.get("type"),
                    condition=rule_config.get("condition")
                )
                
                validation_result = await data_validator.validate_record(record, [rule])
                if not validation_result.is_valid:
                    is_valid = False
                    break
            
            if is_valid:
                validated_data.append(record)
        
        return validated_data
    
    async def _enrich_data(self, data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """丰富数据"""
        enrichment_config = config.get("enrichment", {})
        
        for record in data:
            # 添加时间戳
            if enrichment_config.get("add_timestamp"):
                record["etl_timestamp"] = datetime.now().isoformat()
            
            # 添加计算字段
            calculated_fields = enrichment_config.get("calculated_fields", {})
            for field_name, expression in calculated_fields.items():
                # 简单的表达式计算（实际实现可能需要更复杂的表达式解析）
                try:
                    record[field_name] = eval(expression, {}, record)
                except:
                    record[field_name] = None
        
        return data
    
    async def _aggregate_data(self, data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """聚合数据"""
        aggregation_config = config.get("aggregation", {})
        group_by = aggregation_config.get("group_by", [])
        aggregates = aggregation_config.get("aggregates", {})
        
        if not group_by or not aggregates:
            return data
        
        # 使用pandas进行聚合
        import pandas as pd
        
        df = pd.DataFrame(data)
        
        # 分组
        grouped = df.groupby(group_by)
        
        # 应用聚合函数
        aggregation_functions = {}
        for target_field, agg_config in aggregates.items():
            agg_type = agg_config.get("type", "sum")
            source_field = agg_config.get("field", target_field)
            
            if agg_type == "sum":
                aggregation_functions[source_field] = 'sum'
            elif agg_type == "mean":
                aggregation_functions[source_field] = 'mean'
            elif agg_type == "count":
                aggregation_functions[source_field] = 'count'
            elif agg_type == "max":
                aggregation_functions[source_field] = 'max'
            elif agg_type == "min":
                aggregation_functions[source_field] = 'min'
        
        aggregated_df = grouped.agg(aggregation_functions).reset_index()
        return aggregated_df.to_dict('records')
    
    async def _load_data(self, data: List[Dict[str, Any]], destination_config: Dict[str, Any]) -> int:
        """加载数据"""
        destination_type = destination_config.get("type", "memory")
        
        if destination_type == "memory":
            # 数据已经在内存中，直接返回计数
            return len(data)
        elif destination_type == "file":
            return await self._load_to_file(data, destination_config)
        elif destination_type == "database":
            return await self._load_to_database(data, destination_config)
        else:
            raise ValueError(f"不支持的目标类型: {destination_type}")
    
    async def _load_to_file(self, data: List[Dict[str, Any]], config: Dict[str, Any]) -> int:
        """加载数据到文件"""
        file_path = config.get("path", "output.json")
        file_format = config.get("format", "json")
        
        try:
            if file_format == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            elif file_format == "csv":
                import pandas as pd
                df = pd.DataFrame(data)
                df.to_csv(file_path, index=False)
            else:
                raise ValueError(f"不支持的文件格式: {file_format}")
            
            logging.info(f"数据已保存到文件: {file_path}")
            return len(data)
            
        except Exception as e:
            logging.error(f"文件数据加载失败: {e}")
            raise
    
    async def _load_to_database(self, data: List[Dict[str, Any]], config: Dict[str, Any]) -> int:
        """加载数据到数据库"""
        # 模拟数据库插入
        table_name = config.get("table", "etl_results")
        logging.info(f"插入 {len(data)} 条记录到数据库表: {table_name}")
        
        # 模拟插入操作
        await asyncio.sleep(0.1)  # 模拟数据库操作时间
        
        return len(data)
    
    # 内置转换函数
    def _transform_lowercase(self, record: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """转换为小写"""
        field = params.get("field")
        if field in record and isinstance(record[field], str):
            record[field] = record[field].lower()
        return record
    
    def _transform_uppercase(self, record: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """转换为大写"""
        field = params.get("field")
        if field in record and isinstance(record[field], str):
            record[field] = record[field].upper()
        return record
    
    def _transform_trim(self, record: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """去除空格"""
        field = params.get("field")
        if field in record and isinstance(record[field], str):
            record[field] = record[field].strip()
        return record
    
    def _transform_date_format(self, record: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """格式化日期"""
        field = params.get("field")
        format_from = params.get("format_from", "%Y-%m-%d")
        format_to = params.get("format_to", "%Y/%m/%d")
        
        if field in record and record[field]:
            try:
                from datetime import datetime
                date_obj = datetime.strptime(str(record[field]), format_from)
                record[field] = date_obj.strftime(format_to)
            except ValueError:
                # 日期格式转换失败，保持原值
                pass
        
        return record
    
    def _transform_numeric_cast(self, record: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """数值类型转换"""
        field = params.get("field")
        target_type = params.get("type", "float")
        
        if field in record and record[field] is not None:
            try:
                if target_type == "int":
                    record[field] = int(record[field])
                elif target_type == "float":
                    record[field] = float(record[field])
            except (ValueError, TypeError):
                # 转换失败，设置为None
                record[field] = None
        
        return record
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """获取引擎统计"""
        total_pipelines = len(self.pipelines)
        enabled_pipelines = sum(1 for p in self.pipelines.values() if p.enabled)
        
        total_executions = 0
        successful_executions = 0
        total_records = 0
        
        for pipeline_id, executions in self.execution_history.items():
            total_executions += len(executions)
            successful_executions += sum(1 for e in executions if e.status == "success")
            total_records += sum(e.records_processed for e in executions)
        
        return {
            "total_pipelines": total_pipelines,
            "enabled_pipelines": enabled_pipelines,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": (successful_executions / total_executions * 100) if total_executions > 0 else 0,
            "total_records_processed": total_records,
            "custom_transforms": len(self.custom_transforms)
        }

# 全局ETL引擎实例
etl_engine = ETLEngine()
