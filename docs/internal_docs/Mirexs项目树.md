# 🌳 Mirexs 完整项目结构树 v2.0（详细版）

版本：2.0
更新日期：2026年3月
说明：完整包含多模型智能路由、知识图谱、情绪神经网络、实时知识更新、安全防护等所有2.0增强模块

📁 总项目结构树
text
Mirexs/
├── 🏗️  infrastructure/                # 基础设施层
├── 💾  data/                          # 数据持久层
├── 🧠  cognitive/                     # 认知核心层
├── 🛠️  capabilities/                  # 能力服务层
├── 🎭  interaction/                   # 交互呈现层
├── 🌐  application/                   # 应用接口层
├── 🔐  security/                      # 安全治理层
├── ⚙️  deployment/                    # 运维部署层
├── 📋  config/                        # 配置中心
├── 📚  docs/                          # 项目文档
├── 🔌  plugins/                       # 插件系统
├── 🧪  tests/                         # 测试套件
├── 🚀  launch/                        # 启动入口
└── 🔧  utils/                         # 工具函数库
🏗️ 基础设施层 (infrastructure/)
text
infrastructure/
├── __init__.py
├── compute_storage/                   # 计算与存储
│   ├── __init__.py
│   ├── model_serving_engine.py        # 模型服务引擎：统一管理AI模型加载和推理
│   ├── inference_optimizer.py         # 推理优化器：优化模型推理速度和资源占用
│   ├── vector_database.py             # 向量数据库：用于存储和检索向量数据
│   ├── time_series_db.py              # 时序数据库：存储时间序列数据，如日志和监控指标
│   ├── distributed_storage.py         # 分布式存储：管理分布式文件存储
│   ├── resource_manager.py            # 资源管理器：动态管理CPU、GPU、内存等资源
│   ├── gpu_accelerator.py             # GPU加速器：GPU资源管理和加速计算
│   ├── memory_allocator.py            # 内存分配器：智能内存分配和回收
│   ├── cache_manager.py               # 缓存管理器：多级缓存系统管理
│   ├── smart_model_router.py          # ⭐【新增】智能模型路由：根据硬件和任务自动切换Llama 3.1/Qwen/DeepSeek等
│   └── model_quantizer.py             # 模型量化器：模型量化优化
│
├── storage_migration/                  # ⭐ 新增：整体迁移模块
│   ├── __init__.py
│   ├── data_migrator.py                # 核心迁移引擎（一键迁移）
│   ├── migration_wizard.py             # 迁移向导：评估候选目标并生成执行计划
│   ├── storage_orchestrator.py         # 存储编排器：计划/执行/校验/联接/云镜像串联
│   ├── symlink_manager.py              # 符号链接管理器（无缝切换）
│   ├── migration_validator.py          # 迁移完整性校验
│   ├── cloud_sync_adapter.py           # 云盘适配器（OneDrive / 阿里云等）
│   └── migration_config.yaml           # 默认迁移策略配置
│
├── model_hub/                          # ⭐【新增目录】统一模型管理
│   ├── __init__.py
│   ├── model_manager.py                # ⭐【新增】模型管理器：统一加载、卸载、切换所有模型
│   ├── model_downloader.py             # ⭐【新增】模型下载器：按需下载GGUF量化模型
│   ├── model_registry.py               # ⭐【新增】模型注册表：管理可用模型列表
│   ├── model_configs.yaml              # ⭐【新增】模型配置文件：定义各模型的路径、参数
│   └── hardware_profile.py             # ⭐【新增】硬件配置文件：存储用户硬件信息
│
├── communication/                      # 通信与网络
│   ├── __init__.py
│   ├── message_bus.py                  # 消息总线：模块间的异步消息传递
│   ├── event_dispatcher.py             # 事件分发器：事件的注册和分发
│   ├── network_manager.py              # 网络管理器：管理网络连接和通信
│   ├── protocol_adapters.py            # 协议适配器：支持多种通信协议
│   ├── sync_engine.py                  # 同步引擎：多设备数据同步
│   ├── service_mesh.py                 # 服务网格：微服务之间的通信管理
│   ├── rpc_client.py                   # RPC客户端：远程过程调用客户端
│   ├── rpc_server.py                   # RPC服务端：远程过程调用服务端
│   └── load_balancer.py                # 负载均衡器：请求负载均衡
├── data_pipelines/                     # 数据处理管道
│   ├── __init__.py
│   ├── data_ingestion.py               # 数据摄入：从各种数据源收集数据
│   ├── data_cleaning.py                # 数据清洗：清洗和预处理数据
│   ├── etl_engine.py                   # ETL引擎：提取、转换、加载数据
│   ├── analytics_engine.py             # 分析引擎：数据分析功能
│   ├── feature_extractor.py            # 特征提取器：从数据中提取特征
│   ├── metrics_collector.py            # 指标收集器：收集系统运行指标
│   ├── stream_processor.py             # 流处理器：实时数据流处理
│   ├── batch_processor.py              # 批处理器：批量数据处理
│   └── data_validator.py               # 数据验证器：数据格式和完整性验证
│
└── platform_adapters/                  # 平台适配器
    ├── __init__.py
    ├── windows_adapter.py              # Windows平台适配器：Windows特定功能适配
    ├── linux_adapter.py                # Linux平台适配器：Linux特定功能适配
    ├── macos_adapter.py                # macOS平台适配器：macOS特定功能适配
    ├── mobile_adapter.py               # 移动端适配器：移动设备特定功能适配
    ├── audio_adapter.py                # 音频适配器：跨平台音频处理
    ├── graphics_adapter.py             # 图形适配器：跨平台图形渲染
    ├── file_system_adapter.py          # 文件系统适配器：跨平台文件操作
    └── hardware_detector.py            # 硬件检测器：自动检测硬件配置（显存、内存、CPU）
💾 数据持久层 (data/)
text
data/
├── __init__.py
├── models/                             # AI模型存储
│   ├── __init__.py
│   ├── speech/                         # 语音模型
│   │   ├── __init__.py
│   │   ├── asr/                        # 语音识别
│   │   │   ├── __init__.py
│   │   │   ├── chinese_asr_model.py    # 中文语音识别模型
│   │   │   ├── english_asr_model.py    # 英文语音识别模型
│   │   │   ├── multilingual_asr.py     # 多语言语音识别
│   │   │   ├── whisper_integration.py  # Whisper集成
│   │   │   └── speech_enhancement.py   # 语音增强
│   │   ├── tts/                        # 语音合成
│   │   │   ├── __init__.py
│   │   │   ├── chinese_tts_model.py    # 中文语音合成模型
│   │   │   ├── english_tts_model.py    # 英文语音合成模型
│   │   │   ├── emotional_tts.py        # 情感语音合成
│   │   │   ├── voice_cloning.py        # 语音克隆
│   │   │   ├── coqui_tts_integration.py # Coqui TTS集成
│   │   │   └── xtts_integration.py     # XTTS集成
│   │   └── wake_word/                  # 唤醒词
│   │       ├── __init__.py
│   │       ├── wake_word_model.py      # 唤醒词模型
│   │       ├── voice_activity.py       # 语音活动检测
│   │       ├── speaker_verification.py # 说话人验证
│   │       └── audio_preprocessor.py   # 音频预处理器
│   │
│   ├── vision/                         # 视觉模型
│   │   ├── __init__.py
│   │   ├── face_detection.py           # 人脸检测
│   │   ├── emotion_recognition.py      # 情绪识别（基础版）
│   │   ├── gesture_recognition.py      # 手势识别
│   │   ├── object_detection.py         # 物体检测
│   │   ├── scene_understanding.py      # 场景理解
│   │   ├── insightface_integration.py  # InsightFace集成
│   │   ├── mediapipe_integration.py    # MediaPipe集成
│   │   └── opencv_utils.py             # OpenCV工具
│   │
│   ├── nlp/                            # 自然语言处理模型
│   │   ├── __init__.py
│   │   ├── language_models.py          # 大语言模型管理
│   │   ├── embedding_models.py         # 嵌入模型
│   │   ├── knowledge_models.py         # 知识模型
│   │   ├── llama_integration.py        # LLaMA模型集成
│   │   ├── qwen_integration.py         # Qwen模型集成
│   │   ├── deepseek_integration.py     # ⭐【新增】DeepSeek模型集成
│   │   ├── mistral_integration.py      # Mistral模型集成
│   │   ├── sentence_transformers.py    # Sentence Transformers
│   │   ├── tokenizer_manager.py        # 分词器管理
│   │   └── model_quantizer.py          # 模型量化器
│   │
│   └── three_d/                        # 3D模型
│       ├── __init__.py
│       ├── cat_models.py               # 猫咪模型
│       ├── animations.py               # 动画数据
│       ├── textures.py                 # 纹理材质
│       ├── rigging_system.py           # 骨骼绑定系统
│       ├── blend_shapes.py             # 混合形状
│       ├── panda3d_integration.py      # Panda3D集成
│       ├── blender_exporter.py         # Blender导出器
│       └── model_optimizer.py          # 模型优化器
│
├── databases/                          # 数据库系统
│   ├── __init__.py
│   ├── vector_db/                      # 向量数据库
│   │   ├── __init__.py
│   │   ├── memory_vectors.py           # 记忆向量
│   │   ├── knowledge_vectors.py        # 知识向量
│   │   ├── chroma_integration.py       # Chroma集成
│   │   ├── faiss_integration.py        # FAISS集成
│   │   ├── vector_indexer.py           # 向量索引器
│   │   └── similarity_search.py        # 相似度搜索
│   │
│   ├── graph_db/                       # 图数据库 ⭐【强化】
│   │   ├── __init__.py
│   │   ├── knowledge_graph.py          # ⭐【实现】知识图谱：存储实体关系
│   │   ├── relationship_graph.py       # 关系图谱
│   │   ├── neo4j_integration.py        # Neo4j集成
│   │   ├── graph_traversal.py          # 图遍历算法
│   │   ├── graph_analyzer.py           # 图分析器
│   │   └── entity_extractor.py         # ⭐【新增】实体提取器：从对话中自动提取实体
│   │
│   ├── time_series/                    # 时序数据库
│   │   ├── __init__.py
│   │   ├── system_logs.py              # 系统日志
│   │   ├── performance_metrics.py      # 性能指标
│   │   ├── user_interactions.py        # 用户交互记录
│   │   ├── influxdb_integration.py     # InfluxDB集成
│   │   ├── metrics_aggregator.py       # 指标聚合器
│   │   └── anomaly_detector.py         # 异常检测器
│   │
│   └── relational/                      # 关系数据库
│       ├── __init__.py
│       ├── user_profiles.py            # 用户画像
│       ├── system_config.py            # 系统配置
│       ├── skill_registry.py           # 技能注册
│       ├── sqlite_integration.py       # SQLite集成
│       ├── postgresql_integration.py   # PostgreSQL集成
│       ├── schema_manager.py           # 模式管理器
│       └── migration_tool.py           # 迁移工具
│
├── user_data/                          # 用户数据
│   ├── __init__.py
│   ├── profiles.py                     # 用户画像
│   ├── preferences.py                  # 用户偏好
│   ├── history.py                      # 交互历史
│   ├── documents.py                    # 用户文档
│   ├── conversations.py                # 对话记录
│   ├── learning_data.py                # 学习数据
│   ├── customization.py                # 个性化设置
│   └── backup_manager.py               # 备份管理器
│
└── system/                             # 系统数据
    ├── __init__.py
    ├── logs/                           # 日志系统
    │   ├── __init__.py
    │   ├── system_logs.py              # 系统日志
    │   ├── security_logs.py            # 安全日志
    │   ├── performance_logs.py         # 性能日志
    │   ├── interaction_logs.py         # 交互日志
    │   ├── error_logs.py               # 错误日志
    │   ├── audit_logs.py               # 审计日志
    │   ├── log_rotator.py              # 日志轮转
    │   └── log_analyzer.py             # 日志分析器
    │
    ├── cache/                          # 缓存系统
    │   ├── __init__.py
    │   ├── memory_cache.py             # 内存缓存
    │   ├── disk_cache.py               # 磁盘缓存
    │   ├── redis_integration.py        # Redis集成
    │   ├── cache_policy.py             # 缓存策略
    │   └── cache_validator.py          # 缓存验证器
    │
    └── temp/                           # 临时文件
        ├── __init__.py
        ├── temp_file_manager.py        # 临时文件管理
        ├── session_data.py             # 会话数据
        └── cleanup_scheduler.py        # 清理调度器
🧠 认知核心层 (cognitive/) ⭐【2.0核心增强】
text
cognitive/
├── __init__.py
├── reasoning/                         # 推理与规划系统 ⭐【增强】
│   ├── __init__.py
│   ├── task_decomposer.py             # 任务分解器
│   ├── hierarchical_planner.py        # 分层规划器
│   ├── problem_analyzer.py            # 问题分析器
│   ├── goal_recognizer.py             # 目标识别器
│   ├── state_tracker.py               # 状态跟踪器
│   ├── execution_monitor.py           # 执行监控器
│   ├── causal_reasoner.py             # 因果推理器
│   ├── logical_reasoner.py            # 逻辑推理器
│   ├── constraint_solver.py           # 约束求解器
│   ├── plan_validator.py              # 计划验证器
│   ├── chain_of_thought.py            # ⭐【新增】思维链推理：逐步思考复杂问题
│   ├── self_reflection.py             # ⭐【新增】自我反思：回答后自我检查一致性
│   ├── reasoning_metrics.py           # 推理指标
│   └── smart_router_integration.py    # ⭐【新增】与模型路由的接口
│
├── fact_checker/                      # ⭐【新增】事实核查模块
│   ├── __init__.py
│   ├── credibility_scorer.py          # 综合可信度评分
│   ├── source_analyzer.py             # 信源分析
│   ├── cross_validator.py             # 多源交叉验证
│   ├── consistency_checker.py         # 与知识图谱一致性检查
│   ├── claim_extractor.py             # 主张提取
│   ├── evidence_ranker.py             # 证据排序
│   ├── logic_checker.py               # 逻辑谬误检测
│   └── bias_detector.py               # 广告/偏见识别
│
├── learning/                          # 学习与适应系统 ⭐【2.0核心】
│   ├── __init__.py
│   ├── meta_learner.py                # 元学习器
│   ├── skill_acquisition.py           # 技能获取
│   ├── experience_replayer.py         # 经验回放
│   ├── pattern_recognizer.py          # 模式识别
│   ├── knowledge_curator.py           # 知识管理
│   ├── performance_optimizer.py       # 性能优化
│   ├── transfer_learning.py           # 迁移学习
│   ├── reinforcement_learner.py       # ⭐【实现】强化学习：基于Q-learning优化行为
│   ├── curriculum_learning.py         # 课程学习
│   ├── adaptation_engine.py           # 适应引擎
│   ├── emotion_nn.py                  # ⭐【新增】情绪识别神经网络：LSTM识别6种情绪
│   ├── emotion_trainer.py             # ⭐【新增】情绪模型训练器
│   ├── feedback_collector.py          # ⭐【新增】用户反馈收集器（点赞/点踩）
│   └── learning_evaluator.py          # 学习评估器
│
├── memory/                            # 记忆管理系统 ⭐【增强】
│   ├── __init__.py
│   ├── episodic_memory.py             # 情景记忆
│   ├── semantic_memory.py             # 语义记忆
│   ├── procedural_memory.py           # 程序记忆
│   ├── working_memory.py              # 工作记忆
│   ├── attention_mechanism.py         # 注意力机制
│   ├── memory_retrieval.py            # 记忆检索
│   ├── memory_consolidation.py        # 记忆巩固
│   ├── memory_forgetting.py           # 记忆遗忘
│   ├── memory_organization.py         # 记忆组织
│   ├── associative_memory.py          # 关联记忆
│   ├── smart_memory.py                # ⭐【新增】智能记忆巩固：记忆分级+自动巩固
│   ├── memory_graph_bridge.py         # ⭐【新增】记忆与知识图谱的桥接
│   └── memory_metrics.py              # 记忆指标
│
└── agents/                            # 多智能体系统
    ├── __init__.py
    ├── coordinator.py                 # 主协调器
    ├── creative_agent.py              # 创意智能体
    ├── technical_agent.py             # 技术智能体
    ├── personal_agent.py              # 个人助理智能体
    ├── security_agent.py              # 安全智能体
    ├── swarm_orchestrator.py          # 群体协调器
    ├── collaboration_engine.py        # 协作引擎
    ├── agent_communication.py         # 智能体通信
    ├── role_specializer.py            # 角色特化器
    ├── task_allocator.py              # 任务分配器
    ├── conflict_resolver.py           # 冲突解决器
    └── agent_monitor.py               # 智能体监控器
🛠️ 能力服务层 (capabilities/) ⭐【2.0增强】
text
capabilities/
├── __init__.py
├── creative_suite/                    # 创意内容生成套件
│   ├── __init__.py
│   ├── document_generator.py          # 文档生成器
│   ├── presentation_generator.py      # PPT生成器
│   ├── spreadsheet_generator.py       # 表格生成器
│   ├── image_generator.py             # 图像生成器
│   ├── music_generator.py             # 音乐生成器
│   ├── content_refiner.py             # 内容精炼器
│   ├── revision_manager.py            # 修订管理器
│   ├── template_engine.py             # 模板引擎
│   ├── style_transfer.py              # 风格迁移
│   ├── creative_constraints.py        # 创意约束
│   ├── quality_evaluator.py           # 质量评估器
│   └── creative_metrics.py            # 创意指标
│
├── software_control/                  # 软件控制系统
│   ├── __init__.py
│   ├── application_launcher.py        # 应用启动器
│   ├── process_manager.py             # 进程管理器
│   ├── file_association.py            # 文件关联
│   ├── automation_engine.py           # 自动化引擎
│   ├── workflow_integrator.py         # 工作流集成器
│   ├── operation_recorder.py          # 操作记录器
│   ├── macro_builder.py               # 宏构建器
│   ├── ui_automation.py               # UI自动化
│   ├── api_integration.py             # API集成
│   ├── script_executor.py             # 脚本执行器
│   └── automation_validator.py        # 自动化验证器
│
├── system_management/                  # 系统管理系统
│   ├── __init__.py
│   ├── threat_detector.py             # 威胁检测器
│   ├── security_scanner.py            # 安全扫描器
│   ├── performance_monitor.py         # 性能监控器
│   ├── maintenance_manager.py         # 维护管理器
│   ├── storage_optimizer.py           # 存储优化器
│   ├── network_manager.py             # 网络管理器
│   ├── update_manager.py              # 更新管理器
│   ├── resource_optimizer.py          # 资源优化器
│   ├── health_checker.py              # 健康检查器
│   ├── diagnostic_tool.py             # 诊断工具
│   └── recovery_manager.py            # 恢复管理器
│
├── knowledge/                          # ⭐【新增目录】知识管理
│   ├── __init__.py
│   ├── real_time_knowledge.py          # ⭐【新增】实时知识更新：Agentic RAG + 联网搜索
│   ├── auto_knowledge_ingestion.py     # ⭐【新增】主动知识摄取：定时抓取用户兴趣领域
│   ├── web_search.py                   # ⭐【新增】网页搜索工具
│   ├── rss_reader.py                   # ⭐【新增】RSS订阅阅读器
│   ├── news_extractor.py               # ⭐【新增】新闻提取器
│   ├── knowledge_summarizer.py         # ⭐【新增】知识摘要生成器
│   └── interest_extractor.py           # ⭐【新增】用户兴趣提取器
│
├── avatar/                             # ⭐【新增目录】形象自定义
│   ├── __init__.py
│   ├── avatar_customizer.py            # ⭐【新增】形象自定义器：捏人系统
│   ├── ai_avatar_generator.py          # ⭐【新增】AI形象生成器：根据描述生成
│   ├── texture_editor.py               # ⭐【新增】纹理编辑器
│   ├── accessory_library.py            # ⭐【新增】饰品库
│   └── avatar_exporter.py              # ⭐【新增】形象导出器
│
└── tool_integration/                   # 工具集成框架
    ├── __init__.py
    ├── web_browser.py                  # 网页浏览器控制
    ├── office_tools.py                 # Office工具集成
    ├── development_tools.py            # 开发环境工具集成
    ├── creative_tools.py               # 创意设计软件集成
    ├── system_tools.py                 # 系统管理工具集成
    ├── custom_tools.py                 # 自定义工具集成
    ├── tool_discovery.py               # 工具发现
    ├── tool_wrapper.py                 # 工具包装器
    ├── tool_registry.py                # 工具注册表
    ├── dependency_manager.py           # 依赖管理器
    ├── compatibility_checker.py        # 兼容性检查器
    └── tool_metrics.py                 # 工具指标
🎭 交互呈现层 (interaction/)
text
interaction/
├── __init__.py
├── threed_avatar/                      # 3D虚拟猫咪核心系统
│   ├── __init__.py
│   ├── render_engine/                  # 渲染引擎
│   │   ├── __init__.py
│   │   ├── realtime_renderer.py        # 实时渲染器
│   │   ├── lighting_system.py          # 光照系统
│   │   ├── material_manager.py         # 材质管理器
│   │   ├── shader_compiler.py          # 着色器编译器
│   │   ├── texture_loader.py           # 纹理加载器
│   │   ├── post_processor.py           # 后处理器
│   │   ├── render_optimizer.py         # 渲染优化器
│   │   └── quality_settings.py         # 质量设置
│   │
│   ├── character_system/               # 角色系统
│   │   ├── __init__.py
│   │   ├── model_manager.py            # 模型管理器
│   │   ├── skeleton_animation.py       # 骨骼动画
│   │   ├── physics_simulator.py        # 物理模拟器
│   │   ├── collision_detector.py       # 碰撞检测器
│   │   ├── ragdoll_system.py           # 布娃娃系统
│   │   ├── inverse_kinematics.py       # 逆向运动学
│   │   ├── character_loader.py         # 角色加载器
│   │   ├── asset_pipeline.py           # 资源管道
│   │   └── avatar_custom_bridge.py     # ⭐【新增】与形象自定义模块的桥接
│   │
│   ├── behavior_system/                # 行为系统
│   │   ├── __init__.py
│   │   ├── emotion_engine.py           # 情感引擎
│   │   ├── expression_control.py       # 表情控制
│   │   ├── gesture_library.py          # 手势库
│   │   ├── gaze_system.py              # 视线系统
│   │   ├── personality_model.py        # 性格模型
│   │   ├── behavior_planner.py         # 行为规划器
│   │   ├── state_machine.py            # 状态机
│   │   ├── context_awareness.py        # 情境感知
│   │   ├── emotion_nn_bridge.py        # ⭐【新增】与情绪神经网络的桥接
│   │   └── behavior_metrics.py         # 行为指标
│   │
│   └── speech_sync/                    # 语音同步系统
│       ├── __init__.py
│       ├── lip_sync_engine.py          # 嘴唇同步引擎
│       ├── voice_animation_map.py      # 语音动画映射
│       ├── emotional_tts.py            # 情感语音合成
│       ├── phoneme_analyzer.py         # 音素分析器
│       ├── viseme_generator.py         # 视素生成器
│       ├── sync_optimizer.py           # 同步优化器
│       ├── audio_visualizer.py         # 音频可视化
│       └── sync_metrics.py             # 同步指标
│
├── input_systems/                      # 输入系统
│   ├── __init__.py
│   ├── speech_recognizer/              # 语音识别
│   │   ├── __init__.py
│   │   ├── bilingual_asr.py            # 双语语音识别
│   │   ├── wake_word_detector.py       # 唤醒词检测器
│   │   ├── voiceprint_auth.py          # 声纹认证
│   │   ├── speech_enhancer.py          # 语音增强
│   │   ├── noise_suppressor.py         # 噪声抑制
│   │   ├── accent_adaptation.py        # 口音适应
│   │   ├── realtime_transcriber.py     # 实时转录器
│   │   └── speech_metrics.py           # 语音指标
│   │
│   ├── computer_vision/                # 计算机视觉
│   │   ├── __init__.py
│   │   ├── face_recognition.py         # 人脸识别
│   │   ├── emotion_detection.py        # 情绪检测（视觉）
│   │   ├── gesture_recognizer.py       # 手势识别
│   │   ├── pose_estimation.py          # 姿态估计
│   │   ├── gaze_tracker.py             # 视线追踪
│   │   ├── object_interaction.py       # 物体交互检测
│   │   ├── scene_analyzer.py           # 场景分析器
│   │   ├── motion_detector.py          # 运动检测器
│   │   └── vision_metrics.py           # 视觉指标
│   │
│   └── text_input/                     # 文本输入
│       ├── __init__.py
│       ├── keyboard_handler.py         # 键盘处理
│       ├── handwriting_recog.py        # 手写识别
│       ├── voice_typing.py             # 语音打字
│       ├── predictive_text.py          # 预测文本
│       ├── auto_correction.py          # 自动校正
│       ├── input_method.py             # 输入法
│       ├── shortcut_manager.py         # 快捷键管理
│       └── input_metrics.py            # 输入指标
│
└── output_systems/                     # 输出系统
    ├── __init__.py
    ├── speech_output/                  # 语音输出
    │   ├── __init__.py
    │   ├── multilingual_tts.py         # 多语言语音合成
    │   ├── emotional_voice.py          # 情感语音
    │   ├── audio_effects.py            # 音效处理
    │   ├── voice_customization.py      # 语音定制
    │   ├── speech_synthesizer.py       # 语音合成器
    │   ├── audio_mixer.py              # 音频混合器
    │   ├── spatial_audio.py            # 空间音频
    │   └── speech_metrics.py           # 语音指标
    │
    ├── visual_feedback/                # 视觉反馈
    │   ├── __init__.py
    │   ├── ui_renderer.py              # UI渲染器
    │   ├── notification_engine.py      # 通知引擎
    │   ├── expression_display.py       # 表情显示
    │   ├── progress_indicator.py       # 进度指示器
    │   ├── status_display.py           # 状态显示
    │   ├── theme_manager.py            # 主题管理
    │   ├── layout_engine.py            # 布局引擎
    │   └── visual_metrics.py           # 视觉指标
    │
    └── dialogue_manager/               # 对话管理
        ├── __init__.py
        ├── context_manager.py          # 上下文管理器
        ├── intent_recognizer.py        # 意图识别器
        ├── response_generator.py       # 响应生成器
        ├── conversation_flow.py        # 对话流程
        ├── topic_tracker.py            # 话题追踪器
        ├── sentiment_analyzer.py       # 情感分析器
        ├── dialogue_history.py         # 对话历史
        ├── personality_adaptation.py   # 个性化适应
        └── dialogue_metrics.py         # 对话指标
🌐 应用接口层 (application/)
text
application/
├── __init__.py
├── desktop_app/                        # 桌面应用程序
│   ├── __init__.py
│   ├── windows_client.py               # Windows客户端
│   ├── macos_client.py                 # macOS客户端
│   ├── linux_client.py                 # Linux客户端
│   ├── main_window.py                  # 主窗口
│   ├── taskbar_integration.py          # 任务栏集成
│   ├── system_tray.py                  # 系统托盘
│   ├── window_manager.py               # 窗口管理
│   ├── theme_selector.py               # 主题选择器
│   ├── shortcut_handler.py             # 快捷方式处理
│   └── desktop_metrics.py              # 桌面指标
│
├── mobile_app/                         # 移动应用程序
│   ├── __init__.py
│   ├── ios_app.py                      # iOS应用
│   ├── android_app.py                  # Android应用
│   ├── mobile_ui.py                    # 移动UI
│   ├── touch_gestures.py               # 触摸手势
│   ├── mobile_notifications.py         # 移动通知
│   ├── offline_support.py              # 离线支持
│   ├── battery_optimizer.py            # 电池优化
│   ├── mobile_sensors.py               # 移动传感器
│   └── mobile_metrics.py               # 移动指标
│
├── web_interface/                      # Web界面
│   ├── __init__.py
│   ├── web_app.py                      # Web应用
│   ├── browser_extension.py            # 浏览器扩展
│   ├── progressive_web_app.py          # PWA应用
│   ├── web_components.py               # Web组件
│   ├── service_worker.py               # Service Worker
│   ├── web_sockets.py                  # WebSocket
│   ├── responsive_design.py            # 响应式设计
│   ├── web_storage.py                  # Web存储
│   └── web_metrics.py                  # Web指标
│
├── device_connector/                   # 设备连接器
│   ├── __init__.py
│   ├── protocol_adapters/              # 协议适配器
│   │   ├── __init__.py
│   │   ├── bluetooth_handler.py        # 蓝牙处理
│   │   ├── wifi_handler.py             # WiFi处理
│   │   ├── usb_handler.py              # USB处理
│   │   ├── cloud_sync.py               # 云同步
│   │   ├── mqtt_adapter.py             # MQTT适配器
│   │   ├── websocket_adapter.py        # WebSocket适配器
│   │   ├── http_adapter.py             # HTTP适配器
│   │   └── protocol_metrics.py         # 协议指标
│   │
│   ├── mobile_integration/             # 移动设备集成
│   │   ├── __init__.py
│   │   ├── sensor_data.py              # 传感器数据
│   │   ├── notification_sync.py        # 通知同步
│   │   ├── cross_device_cont.py        # 跨设备连续性
│   │   ├── location_sharing.py         # 位置共享
│   │   ├── mobile_remote.py            # 移动远程
│   │   ├── data_sync_mobile.py         # 数据同步移动端
│   │   └── mobile_integration_metrics.py # 移动集成指标
│   │
│   ├── smart_home/                     # 智能家居集成
│   │   ├── __init__.py
│   │   ├── iot_device_mgr.py           # IoT设备管理
│   │   ├── scene_automation.py         # 场景自动化
│   │   ├── environment_sensing.py      # 环境感知
│   │   ├── home_assistant.py           # 家庭助理
│   │   ├── energy_management.py        # 能源管理
│   │   ├── security_systems.py         # 安全系统
│   │   └── smart_home_metrics.py       # 智能家居指标
│   │
│   └── data_sync/                      # 数据同步系统
│       ├── __init__.py
│       ├── multi_device_sync.py        # 多设备同步
│       ├── conflict_resolution.py      # 冲突解决
│       ├── offline_operation.py        # 离线操作
│       ├── sync_scheduler.py           # 同步调度器
│       ├── data_consistency.py         # 数据一致性
│       ├── sync_encryption.py          # 同步加密
│       └── sync_metrics.py             # 同步指标
│
└── api_gateway/                        # API网关
    ├── __init__.py
    ├── rest_api.py                     # RESTful API
    ├── webhook_handler.py              # Webhook处理
    ├── plugin_system.py                # 插件系统
    ├── sdk_development.py              # SDK开发
    ├── documentation.py                # API文档
    ├── rate_limiter.py                 # 速率限制器
    ├── api_authenticator.py            # API认证器
    ├── request_validator.py            # 请求验证器
    ├── response_formatter.py           # 响应格式化器
    ├── api_monitor.py                  # API监控器
    └── api_metrics.py                  # API指标
🔐 安全治理层 (security/) ⭐【2.0增强】
text
security/
├── __init__.py
├── access_control/                     # 访问控制系统
│   ├── __init__.py
│   ├── biometric_auth.py               # 生物认证
│   ├── multi_factor_auth.py            # 多因素认证
│   ├── permission_manager.py           # 权限管理
│   ├── key_management.py               # 密钥管理
│   ├── identity_verifier.py            # 身份验证器
│   ├── access_logger.py                # 访问日志
│   ├── session_manager.py              # 会话管理
│   ├── role_based_access.py            # 基于角色的访问控制
│   ├── attribute_based_access.py       # 基于属性的访问控制
│   ├── access_policy.py                # 访问策略
│   └── access_metrics.py               # 访问指标
│
├── privacy_protection/                 # 隐私保护系统
│   ├── __init__.py
│   ├── data_encryption.py              # 数据加密
│   ├── differential_privacy.py         # 差分隐私
│   ├── consent_manager.py              # 同意管理
│   ├── anonymization_engine.py         # 匿名化引擎
│   ├── privacy_auditor.py              # 隐私审计
│   ├── secure_enclave.py               # 安全飞地
│   ├── data_masking.py                 # 数据脱敏
│   ├── privacy_policy.py               # 隐私策略
│   ├── data_retention.py               # 数据保留
│   ├── gdpr_compliance.py              # GDPR合规
│   └── privacy_metrics.py              # 隐私指标
│
├── guardian/                            # ⭐【新增目录】输入防护
│   ├── __init__.py
│   ├── input_filter.py                  # ⭐【新增】敏感词过滤 + 意图检测
│   ├── keyword_blocklist.py             # ⭐【新增】敏感词库
│   ├── intent_classifier.py             # ⭐【新增】恶意意图分类器
│   ├── jailbreak_detector.py            # ⭐【新增】越狱提示检测
│   └── content_safe_check.py            # ⭐【新增】内容安全校验
│
├── audit/                                # ⭐【新增目录】审计日志
│   ├── __init__.py
│   ├── audit_logger.py                   # ⭐【新增】区块链式审计日志
│   ├── log_hasher.py                     # ⭐【新增】日志哈希计算
│   ├── chain_verifier.py                 # ⭐【新增】日志链验证器
│   ├── audit_viewer.py                   # ⭐【新增】审计日志查看器
│   └── evidence_preserver.py             # ⭐【新增】证据保全
│
├── incident/                             # ⭐【新增目录】事件响应
│   ├── __init__.py
│   ├── incident_response.py               # ⭐【新增】事件响应器：分级处理高危行为
│   ├── response_levels.py                 # ⭐【新增】响应等级定义
│   ├── user_restrictor.py                 # ⭐【新增】用户限制器
│   ├── evidence_collector.py              # ⭐【新增】证据收集器
│   └── alert_dispatcher.py                # ⭐【新增】告警分发器
│
└── security_monitoring/                  # 安全监控系统
    ├── __init__.py
    ├── threat_detection.py               # 威胁检测
    ├── behavior_analysis.py              # 行为分析
    ├── compliance_checker.py             # 合规检查
    ├── security_policy.py                # 安全策略
    ├── vulnerability_scanner.py          # 漏洞扫描
    ├── intrusion_detection.py            # 入侵检测
    ├── malware_protection.py             # 恶意软件防护
    ├── security_awareness.py             # 安全意识
    ├── risk_assessment.py                # 风险评估
    └── security_metrics.py               # 安全指标
⚙️ 运维部署层 (deployment/)
text
deployment/
├── __init__.py
├── containerization/                    # 容器化部署
│   ├── __init__.py
│   ├── docker_configs/                  # Docker配置
│   │   ├── __init__.py
│   │   ├── dockerfile_generator.py      # Dockerfile生成器
│   │   ├── docker_compose.py            # Docker Compose配置
│   │   ├── image_builder.py             # 镜像构建器
│   │   ├── container_optimizer.py       # 容器优化器
│   │   ├── security_hardening.py        # 安全加固
│   │   └── docker_metrics.py            # Docker指标
│   │
│   ├── kubernetes_manifests/            # Kubernetes清单
│   │   ├── __init__.py
│   │   ├── deployment_manifests.py      # 部署清单
│   │   ├── service_manifests.py         # 服务清单
│   │   ├── ingress_manifests.py         # Ingress清单
│   │   ├── config_maps.py               # 配置映射
│   │   ├── secrets_manager.py           # 密钥管理
│   │   ├── helm_charts.py               # Helm图表
│   │   └── k8s_metrics.py               # K8s指标
│   │
│   ├── orchestration_tools/             # 编排工具
│   │   ├── __init__.py
│   │   ├── scheduler.py                 # 调度器
│   │   ├── resource_allocator.py        # 资源分配器
│   │   ├── service_discovery.py         # 服务发现
│   │   ├── health_checker.py            # 健康检查
│   │   ├── auto_scaler.py               # 自动扩缩容
│   │   └── orchestration_metrics.py     # 编排指标
│   │
│   ├── package_managers/                # 包管理器
│   │   ├── __init__.py
│   │   ├── pip_manager.py               # Pip管理
│   │   ├── conda_manager.py             # Conda管理
│   │   ├── npm_manager.py               # NPM管理
│   │   ├── dependency_resolver.py       # 依赖解析器
│   │   ├── version_manager.py           # 版本管理
│   │   └── package_metrics.py           # 包管理指标
│   │
│   ├── service_mesh_configs/            # 服务网格配置
│   │   ├── __init__.py
│   │   ├── istio_config.py              # Istio配置
│   │   ├── linkerd_config.py            # Linkerd配置
│   │   ├── traffic_management.py        # 流量管理
│   │   ├── security_policies.py         # 安全策略
│   │   ├── observability.py             # 可观测性
│   │   └── mesh_metrics.py              # 网格指标
│   │
│   └── auto_scaling/                    # 自动扩缩容
│       ├── __init__.py
│       ├── horizontal_scaling.py        # 水平扩缩容
│       ├── vertical_scaling.py          # 垂直扩缩容
│       ├── scaling_policies.py          # 扩缩容策略
│       ├── metrics_collector.py         # 指标收集器
│       ├── predictive_scaling.py        # 预测性扩缩容
│       └── scaling_metrics.py           # 扩缩容指标
│
├── monitoring_ops/                      # 监控运维
│   ├── __init__.py
│   ├── monitoring_system/               # 监控系统
│   │   ├── __init__.py
│   │   ├── system_monitor.py            # 系统监控
│   │   ├── application_monitor.py       # 应用监控
│   │   ├── network_monitor.py           # 网络监控
│   │   ├── database_monitor.py          # 数据库监控
│   │   ├── log_monitor.py               # 日志监控
│   │   ├── performance_monitor.py       # 性能监控
│   │   └── monitoring_metrics.py        # 监控指标
│   │
│   ├── alert_manager/                   # 告警管理
│   │   ├── __init__.py
│   │   ├── alert_rules.py               # 告警规则
│   │   ├── notification_system.py       # 通知系统
│   │   ├── escalation_policies.py       # 升级策略
│   │   ├── alert_aggregation.py         # 告警聚合
│   │   ├── silence_manager.py           # 静默管理
│   │   └── alert_metrics.py             # 告警指标
│   │
│   ├── performance_dashboard/           # 性能仪表板
│   │   ├── __init__.py
│   │   ├── realtime_dashboard.py        # 实时仪表板
│   │   ├── historical_analysis.py       # 历史分析
│   │   ├── trend_analyzer.py            # 趋势分析器
│   │   ├── report_generator.py          # 报告生成器
│   │   ├── visualization_engine.py      # 可视化引擎
│   │   └── dashboard_metrics.py         # 仪表板指标
│   │
│   ├── maintenance_tools/               # 维护工具
│   │   ├── __init__.py
│   │   ├── backup_tool.py               # 备份工具
│   │   ├── recovery_tool.py             # 恢复工具
│   │   ├── cleanup_utility.py           # 清理工具
│   │   ├── update_manager.py            # 更新管理
│   │   ├── diagnostic_tool.py           # 诊断工具
│   │   └── maintenance_metrics.py       # 维护指标
│   │
│   ├── logging_system/                  # 日志系统
│   │   ├── __init__.py
│   │   ├── log_collector.py             # 日志收集器
│   │   ├── log_aggregator.py            # 日志聚合器
│   │   ├── log_analyzer.py              # 日志分析器
│   │   ├── log_visualization.py         # 日志可视化
│   │   ├── log_retention.py             # 日志保留
│   │   └── logging_metrics.py           # 日志指标
│   │
│   └── backup_recovery/                 # 备份恢复
│       ├── __init__.py
│       ├── backup_scheduler.py          # 备份调度器
│       ├── incremental_backup.py        # 增量备份
│       ├── full_backup.py               # 全量备份
│       ├── recovery_planner.py          # 恢复规划器
│       ├── disaster_recovery.py         # 灾难恢复
│       ├── backup_verification.py       # 备份验证
│       └── recovery_metrics.py          # 恢复指标
│
├── ci_cd/                               # 持续集成/持续部署
│   ├── __init__.py
│   ├── build_pipelines/                 # 构建流水线
│   │   ├── __init__.py
│   │   ├── jenkins_integration.py       # Jenkins集成
│   │   ├── gitlab_ci.py                 # GitLab CI
│   │   ├── github_actions.py            # GitHub Actions
│   │   ├── build_automation.py          # 构建自动化
│   │   ├── artifact_manager.py          # 制品管理
│   │   └── build_metrics.py             # 构建指标
│   │
│   ├── test_automation/                 # 自动化测试
│   │   ├── __init__.py
│   │   ├── unit_tests.py                # 单元测试
│   │   ├── integration_tests.py         # 集成测试
│   │   ├── performance_tests.py         # 性能测试
│   │   ├── security_tests.py            # 安全测试
│   │   ├── test_reports.py              # 测试报告
│   │   └── test_metrics.py              # 测试指标
│   │
│   ├── deployment_strategies/           # 部署策略
│   │   ├── __init__.py
│   │   ├── blue_green.py                # 蓝绿部署
│   │   ├── canary_release.py            # 金丝雀发布
│   │   ├── rolling_update.py            # 滚动更新
│   │   ├── feature_flags.py             # 功能标志
│   │   ├── deployment_automation.py     # 部署自动化
│   │   └── deployment_metrics.py        # 部署指标
│   │
│   └── release_management/              # 发布管理
│       ├── __init__.py
│       ├── version_control.py           # 版本控制
│       ├── release_notes.py             # 发布说明
│       ├── rollback_manager.py          # 回滚管理
│       ├── release_automation.py        # 发布自动化
│       ├── quality_gates.py             # 质量门禁
│       └── release_metrics.py           # 发布指标
│
└── platform_specific/                   # 平台特定部署
    ├── __init__.py
    ├── windows_deployment/              # Windows部署
    │   ├── __init__.py
    │   ├── windows_installer.py         # Windows安装器
    │   ├── windows_service.py            # Windows服务
    │   ├── registry_config.py           # 注册表配置
    │   ├── windows_firewall.py          # Windows防火墙
    │   ├── active_directory.py          # Active Directory
    │   └── windows_metrics.py           # Windows指标
    │
    ├── linux_deployment/                # Linux部署
    │   ├── __init__.py
    │   ├── debian_package.py            # Debian包
    │   ├── rpm_package.py               # RPM包
    │   ├── systemd_service.py           # Systemd服务
    │   ├── linux_firewall.py            # Linux防火墙
    │   ├── selinux_config.py            # SELinux配置
    │   └── linux_metrics.py             # Linux指标
    │
    ├── macos_deployment/                # macOS部署
    │   ├── __init__.py
    │   ├── macos_app.py                 # macOS应用
    │   ├── dmg_installer.py             # DMG安装器
    │   ├── launchd_service.py           # Launchd服务
    │   ├── macos_security.py            # macOS安全
    │   ├── app_notarization.py          # 应用公证
    │   └── macos_metrics.py             # macOS指标
    │
    └── mobile_deployment/               # 移动端部署
        ├── __init__.py
        ├── android_apk/                 # Android APK
        │   ├── __init__.py
        │   ├── apk_builder.py           # APK构建器
        │   ├── android_manifest.py      # Android清单
        │   ├── google_play.py           # Google Play
        │   ├── android_permissions.py   # Android权限
        │   └── android_metrics.py       # Android指标
        └── ios_ipa/                     # iOS IPA
            ├── __init__.py
            ├── ipa_builder.py           # IPA构建器
            ├── ios_plist.py             # iOS配置
            ├── app_store.py             # App Store
            ├── ios_provisioning.py      # iOS配置
            └── ios_metrics.py           # iOS指标
📋 配置中心 (config/)
text
config/
├── __init__.py
├── system/                             # 系统配置
│   ├── __init__.py
│   ├── main_config.yaml                # 主配置文件
│   ├── component_configs/              # ⭐【v2】组件/子系统配置（get_config 统一入口）
│   │   ├── text_input_config.yaml      # 文本输入系统配置
│   │   ├── input_config.yaml           # 键盘输入配置
│   │   ├── shortcuts.yaml              # 系统快捷键映射
│   │   ├── shortcuts_config.yaml       # 快捷键管理策略配置
│   │   ├── handwriting_config.yaml     # 手写识别配置
│   │   ├── voice_typing_config.yaml    # 语音打字配置
│   │   ├── predictive_text_config.yaml # 预测文本配置
│   │   ├── auto_correction_config.yaml # 自动校正配置
│   │   ├── input_method_config.yaml    # 输入法配置
│   │   └── input_metrics_config.yaml   # 输入指标配置
│   ├── model_configs/                  # 模型配置 ⭐【增强】
│   │   ├── __init__.py
│   │   ├── speech_models.yaml          # 语音模型配置
│   │   ├── vision_models.yaml          # 视觉模型配置
│   │   ├── nlp_models.yaml             # NLP模型配置（包含组合模型）
│   │   ├── router_config.yaml          # ⭐【新增】智能路由配置
│   │   ├── 3d_models.yaml              # 3D模型配置
│   │   └── model_optimization.yaml     # 模型优化配置
│   │
│   ├── service_configs/                # 服务配置
│   │   ├── __init__.py
│   │   ├── api_config.yaml             # API配置
│   │   ├── database_config.yaml        # 数据库配置
│   │   ├── cache_config.yaml           # 缓存配置
│   │   ├── network_config.yaml         # 网络配置
│   │   └── service_discovery.yaml      # 服务发现配置
│   │
│   └── platform_configs/               # 平台配置
│       ├── __init__.py
│       ├── windows_config.yaml         # Windows配置
│       ├── linux_config.yaml           # Linux配置
│       ├── macos_config.yaml           # macOS配置
│       ├── mobile_config.yaml          # 移动端配置
│       └── cross_platform.yaml         # 跨平台配置
│
├── user/                               # 用户配置
│   ├── __init__.py
│   ├── personalization/                # 个性化设置
│   │   ├── __init__.py
│   │   ├── appearance.yaml             # 外观设置
│   │   ├── behavior.yaml               # 行为设置
│   │   ├── shortcuts.yaml              # 快捷键设置
│   │   ├── themes.yaml                 # 主题设置
│   │   └── accessibility.yaml          # 无障碍设置
│   │
│   ├── preferences/                    # 用户偏好
│   │   ├── __init__.py
│   │   ├── language.yaml               # 语言偏好
│   │   ├── interaction.yaml            # 交互偏好
│   │   ├── content.yaml                # 内容偏好
│   │   ├── privacy.yaml                # 隐私偏好
│   │   └── notifications.yaml          # 通知偏好
│   │
│   └── profiles/                       # 用户画像配置
│       ├── __init__.py
│       ├── learning_style.yaml         # 学习风格
│       ├── skill_level.yaml            # 技能水平
│       ├── interest_areas.yaml         # 兴趣领域
│       ├── usage_patterns.yaml         # 使用模式
│       └── adaptation_history.yaml     # 适应历史
│
└── runtime/                            # 运行时配置
    ├── __init__.py
    ├── dynamic_config/                 # 动态配置
    │   ├── __init__.py
    │   ├── performance_tuning.yaml     # 性能调优
    │   ├── resource_allocation.yaml    # 资源分配
    │   ├── adaptive_learning.yaml      # 自适应学习
    │   ├── realtime_optimization.yaml  # 实时优化
    │   └── dynamic_scaling.yaml        # 动态扩缩容
    │
    ├── performance_tuning/             # 性能调优
    │   ├── __init__.py
    │   ├── cache_strategies.yaml       # 缓存策略
    │   ├── memory_management.yaml      # 内存管理
    │   ├── cpu_optimization.yaml       # CPU优化
    │   ├── gpu_optimization.yaml       # GPU优化
    │   └── network_optimization.yaml   # 网络优化
    │
    └── hot_reload/                     # 热重载配置
        ├── __init__.py
        ├── config_reload.yaml          # 配置重载
        ├── model_reload.yaml           # 模型重载
        ├── service_reload.yaml         # 服务重载
        ├── plugin_reload.yaml          # 插件重载
        └── hot_reload_metrics.yaml     # 热重载指标
🚀 启动入口 (launch/) ⭐【2.0增强】
text
launch/
├── __init__.py
├── startup_manager.py                  # ⭐【新增】统一启动管理器：硬件检测→模型选择→初始化
├── model_downloader.py                 # ⭐【新增】模型按需下载器
├── first_run_wizard.py                 # ⭐【新增】首次运行引导（新手教程）
├── dependency_checker.py               # ⭐【新增】依赖检查器
├── init_storage.py                     # 初始化存储
│
├── windows/                            # Windows启动
│   ├── __init__.py
│   ├── start_mirexs.bat                # 批处理启动
│   ├── mirexs_service.exe              # 服务程序
│   ├── installer/                      # 安装程序
│   │   ├── __init__.py
│   │   ├── setup_wizard.py             # 安装向导
│   │   ├── silent_install.py           # 静默安装
│   │   ├── uninstaller.py              # 卸载程序
│   │   └── installer_metrics.py        # 安装指标
│   ├── autostart/                      # 自动启动
│   │   ├── __init__.py
│   │   ├── registry_entries.py         # 注册表项
│   │   ├── startup_folder.py           # 启动文件夹
│   │   ├── task_scheduler.py           # 任务计划
│   │   └── autostart_metrics.py        # 自动启动指标
│   └── windows_metrics.py              # Windows指标
│
├── linux/                              # Linux启动
│   ├── __init__.py
│   ├── start_mirexs.sh                 # Shell启动脚本
│   ├── systemd_service/                # Systemd服务
│   │   ├── __init__.py
│   │   ├── service_file.py             # 服务文件
│   │   ├── service_manager.py          # 服务管理
│   │   ├── log_rotation.py             # 日志轮转
│   │   ├── dependency_management.py    # 依赖管理
│   │   └── systemd_metrics.py          # Systemd指标
│   ├── debian_package/                 # Debian包
│   │   ├── __init__.py
│   │   ├── control_file.py             # 控制文件
│   │   ├── postinst_script.py          # 安装后脚本
│   │   ├── prerm_script.py             # 卸载前脚本
│   │   ├── package_builder.py          # 包构建器
│   │   └── debian_metrics.py           # Debian指标
│   ├── init_scripts/                   # Init脚本
│   │   ├── __init__.py
│   │   ├── sysvinit_script.py          # SysVinit脚本
│   │   ├── upstart_script.py           # Upstart脚本
│   │   ├── runit_script.py             # Runit脚本
│   │   └── init_metrics.py             # Init指标
│   └── linux_metrics.py                # Linux指标
│
├── macos/                              # macOS启动
│   ├── __init__.py
│   ├── start_mirexs.command             # 命令行启动
│   ├── app_bundle/                      # 应用包
│   │   ├── __init__.py
│   │   ├── info_plist.py                # Info.plist
│   │   ├── bundle_structure.py          # 包结构
│   │   ├── code_signing.py              # 代码签名
│   │   ├── entitlements.py              # 权限配置
│   │   └── bundle_metrics.py            # 应用包指标
│   ├── dmg_installer/                   # DMG安装包
│   │   ├── __init__.py
│   │   ├── dmg_creator.py               # DMG创建器
│   │   ├── background_image.py          # 背景图片
│   │   ├── volume_icon.py               # 卷图标
│   │   ├── macos_license_handler.py     # 许可协议
│   │   └── dmg_metrics.py               # DMG指标
│   ├── launchd/                         # Launchd配置
│   │   ├── __init__.py
│   │   ├── plist_generator.py           # Plist生成器
│   │   ├── daemon_manager.py            # 守护进程管理
│   │   ├── startup_items.py             # 启动项
│   │   └── launchd_metrics.py           # Launchd指标
│   └── macos_metrics.py                 # macOS指标
│
└── mobile/                             # 移动端启动
    ├── __init__.py
    ├── android_apk/                     # Android APK
    │   ├── __init__.py
    │   ├── apk_builder.py               # APK构建器
    │   ├── android_manifest.py          # Android清单
    │   ├── google_play.py               # Google Play
    │   ├── android_permissions.py       # Android权限
    │   ├── splash_screen.py             # 启动屏幕
    │   ├── app_icons.py                 # 应用图标
    │   └── android_metrics.py           # Android指标
    └── ios_ipa/                         # iOS IPA
        ├── __init__.py
        ├── ipa_builder.py               # IPA构建器
        ├── ios_plist.py                 # iOS配置
        ├── app_store.py                 # App Store
        ├── ios_provisioning.py          # iOS配置
        ├── launch_images.py             # 启动图片
        ├── app_icons_ios.py             # 应用图标
        └── ios_metrics.py               # iOS指标
📚 文档系统 (docs/)
text
docs/
├── __init__.py
├── Mirexs技术设计补充计划.md
├── api_reference/                       # API参考文档
│   ├── __init__.py
│   ├── rest_api.md                      # REST API文档
│   ├── sdk_documentation.md             # SDK使用文档
│   ├── plugin_development.md            # 插件开发指南
│   ├── fact_checker_api.md              # ⭐【新增】事实核查相关的REST·API接口
│   ├── api_examples/                    # API示例代码
│   │   ├── __init__.py
│   │   ├── basic_usage.py               # 基础使用示例
│   │   ├── advanced_features.py         # 高级功能示例
│   │   ├── error_handling.py            # 错误处理示例
│   │   └── integration_examples.py      # 集成示例
│   └── api_changelog.md                 # API变更日志
│
├── architecture/                        # 架构设计
│   ├── __init__.py
│   ├── overview.md                      # 架构概览
│   ├── multi_model_routing.md           # ⭐【新增】多模型路由设计
│   ├── knowledge_graph.md               # ⭐【新增】知识图谱设计
│   ├── emotion_nn.md                    # ⭐【新增】情绪神经网络设计
│   ├── reinforcement_learner.md         # ⭐【新增】强化学习
│   ├── proactive_behavior.md            # ⭐【新增】主动行为引擎
│   ├── fact_checker.md                  # ⭐【新增】事实核查器的设计
│   ├── big_data_models.md               # ⭐【新增】模型并行推理机制
│   ├── deep_thinking_engine.md          # ⭐【新增】深度思考机制
│   ├── neural_networks_detail.md        # ⭐【新增】情绪识别神经网络
│   ├── ai_algorithms_handbook.md        # ⭐【新增】核心决策逻辑
│   └── security_architecture.md         # 安全架构
│
├── security/                            # 安全合规
│   ├── __init__.py
│   ├── privacy_policy.md                # 隐私政策
│   ├── compliance.md                    # 合规性文档
│   ├── incident_response_plan.md        # ⭐【新增】事件响应计划
│   └── audit_guide.md                   # ⭐【新增】审计指南
│
├── marketing/                           # 市场材料
│   ├── __init__.py
│   ├── product_brief.md                 # 产品简介
│   ├── feature_comparison.md            # 功能对比
│   ├── user_personas.md                 # 用户画像
│   └── pricing_model.md                 # 定价模型
│
├── business/                            # 商业文档
│   ├── __init__.py
│   ├── business_plan.md                 # 商业计划书
│   ├── investor_pitch.md                # 投资人演示
│   └── roadmap.md                       # 路线图
│
├── legal/                               # 法律专利
│   ├── __init__.py
│   ├── license_agreement.md             # 许可协议
│   ├── terms_of_service.md              # 服务条款
│   ├── eula.md                          # 最终用户许可协议
│   └── patent_filing.md                 # 专利申请
│
├── user_manual/                         # 用户手册
│   ├── __init__.py
│   ├── getting_started.md               # 快速开始
│   ├── installation_guide.md            # 安装指南
│   ├── user_interface.md                # 用户界面说明
│   ├── features_guide.md                # 功能特性指南
│   ├── avatar_customization.md          # ⭐【新增】形象自定义指南
│   ├── knowledge_management.md          # ⭐【新增】知识管理指南
│   ├── fact_checker_usage.md            # ⭐【新增】可信度评分指南
│   ├── troubleshooting.md               # 故障排除
│   ├── faq.md                           # 常见问题
│   └── video_tutorials/                 # 视频教程
│       ├── __init__.py
│       ├── basic_operations.mp4         # 基础操作
│       ├── advanced_features.mp4        # 高级功能
│       └── tutorial_scripts.md          # 教程脚本
│
├── developer_guide/                      # 开发者指南
│   ├── __init__.py
│   ├── architecture_overview.md          # 架构概述
│   ├── development_setup.md              # 开发环境设置
│   ├── coding_standards.md               # 编码规范
│   ├── testing_guide.md                  # 测试指南
│   ├── deployment_guide.md               # 部署指南
│   ├── contribution_guide.md             # 贡献指南
│   ├── code_review_process.md            # 代码审查流程
│   ├── fact_checker_development.md       # ⭐【新增】信源分级事实核查逻辑谬误检测规则
│   ├── model_integration.md              # ⭐【新增】模型集成指南
│   ├── knowledge_graph_api.md            # ⭐【新增】知识图谱API
│   └── emotion_nn_training.md            # ⭐【新增】情绪模型训练
│
├── technical_specifications/             # 技术规范文档
│   ├── __init__.py
│   ├── system_requirements.md            # 系统需求
│   ├── api_specification.md              # API规范
│   ├── database_schema.md                # 数据库设计
│   ├── security_specification.md         # 安全规范
│   ├── performance_benchmarks.md         # 性能基准
│   ├── data_pipeline_design.md           # ⭐【新增】大数据处理链路
│   ├── distributed_inference_spec.md     # ⭐【新增】分布式推理规范
│   └── compatibility_matrix.md           # 兼容性矩阵
│
└── internal_docs/                     v  # 内部文档
    ├── __init__.py
    ├── design_decisions.md               # 设计决策记录
    ├── meeting_notes/                    # 会议记录
    │   ├── __init__.py
    │   ├── architecture_review.md        # 架构评审
    │   ├── sprint_planning.md            # 迭代计划
    │   └── design_reviews.md             # 设计评审
    ├── research_papers/                  # 研究论文
    │   ├── __init__.py
    │   ├── ai_architecture.md            # AI架构研究
    │   ├── memory_management.md          # 记忆管理研究
    │   ├── multimodal_fusion.md          # 多模态融合
    │   ├── multi_model_routing_research.md # ⭐【新增】多模型路由研究
    │   └── emotion_recognition.md         # ⭐【新增】情绪识别研究
    └── knowledge_base/                   # 知识库
        ├── __init__.py
        ├── best_practices.md             # 最佳实践
        ├── lessons_learned.md            # 经验教训
        ├── incident_reports.md           # 事件报告
        └── knowledge_articles.md         # 知识文章
🔌 插件系统 (plugins/)
text
plugins/
├── __init__.py
├── core/                                # 核心插件系统
│   ├── __init__.py
│   ├── plugin_manager.py                # 插件管理器
│   ├── plugin_loader.py                 # 插件加载器
│   ├── plugin_registry.py               # 插件注册表
│   ├── dependency_resolver.py           # 依赖解析器
│   ├── version_compatibility.py         # 版本兼容性
│   ├── security_validator.py            # 安全验证器
│   ├── lifecycle_manager.py             # 生命周期管理
│   └── plugin_metrics.py                # 插件指标
│
├── official/                            # 官方插件
│   ├── __init__.py
│   ├── productivity/                    # 生产力插件
│   │   ├── __init__.py
│   │   ├── calendar_integration/       # 日历集成
│   │   │   ├── __init__.py
│   │   │   ├── google_calendar.py      # Google日历
│   │   │   ├── outlook_calendar.py     # Outlook日历
│   │   │   ├── event_scheduler.py      # 事件调度器
│   │   │   └── reminder_system.py      # 提醒系统
│   │   ├── email_assistant/            # 邮件助手
│   │   │   ├── __init__.py
│   │   │   ├── gmail_integration.py    # Gmail
│   │   │   ├── outlook_integration.py  # Outlook
│   │   │   ├── email_analyzer.py       # 邮件分析
│   │   │   ├── smart_reply.py          # 智能回复
│   │   │   └── spam_filter.py          # 垃圾过滤
│   │   ├── document_management/        # 文档管理
│   │   │   ├── __init__.py
│   │   │   ├── file_organizer.py       # 文件整理
│   │   │   ├── search_enhancer.py      # 搜索增强
│   │   │   ├── backup_automation.py    # 备份自动化
│   │   │   └── version_control.py      # 版本控制
│   │   └── task_automation/            # 任务自动化
│   │       ├── __init__.py
│   │       ├── workflow_builder.py     # 工作流构建
│   │       ├── macro_recorder.py       # 宏录制
│   │       ├── batch_processor.py      # 批处理
│   │       └── automation_library.py   # 自动化库
│   │
│   ├── creative/                        # 创意插件
│   │   ├── __init__.py
│   │   ├── image_generation/           # 图像生成
│   │   │   ├── __init__.py
│   │   │   ├── art_generator.py        # 艺术生成
│   │   │   ├── style_transfer.py       # 风格迁移
│   │   │   ├── photo_enhancement.py    # 照片增强
│   │   │   └── design_tools.py         # 设计工具
│   │   ├── music_composition/          # 音乐创作
│   │   │   ├── __init__.py
│   │   │   ├── melody_generator.py     # 旋律生成
│   │   │   ├── chord_progressions.py   # 和弦进行
│   │   │   ├── audio_mixing.py         # 音频混音
│   │   │   └── instrument_library.py   # 乐器库
│   │   ├── writing_assistant/          # 写作助手
│   │   │   ├── __init__.py
│   │   │   ├── grammar_checker.py      # 语法检查
│   │   │   ├── style_analyzer.py       # 风格分析
│   │   │   ├── content_optimizer.py    # 内容优化
│   │   │   └── plagiarism_checker.py   # 抄袭检测
│   │   └── video_editing/              # 视频编辑
│   │       ├── __init__.py
│   │       ├── video_processor.py      # 视频处理
│   │       ├── effect_library.py       # 特效库
│   │       ├── subtitle_generator.py   # 字幕生成
│   │       └── timeline_editor.py      # 时间线编辑
│   │
│   ├── development/                     # 开发工具插件
│   │   ├── __init__.py
│   │   ├── code_assistant/             # 代码助手
│   │   │   ├── __init__.py
│   │   │   ├── code_completion.py      # 代码补全
│   │   │   ├── bug_detector.py         # 错误检测
│   │   │   ├── refactoring_tools.py    # 重构工具
│   │   │   └── documentation_generator.py # 文档生成
│   │   ├── devops_tools/               # DevOps工具
│   │   │   ├── __init__.py
│   │   │   ├── deployment_automation.py # 部署自动化
│   │   │   ├── monitoring_integration.py # 监控集成
│   │   │   ├── log_analyzer.py         # 日志分析
│   │   │   └── performance_profiler.py # 性能分析
│   │   ├── database_tools/             # 数据库工具
│   │   │   ├── __init__.py
│   │   │   ├── query_optimizer.py      # 查询优化
│   │   │   ├── schema_designer.py      # 模式设计
│   │   │   ├── data_migration.py       # 数据迁移
│   │   │   └── backup_manager.py       # 备份管理
│   │   └── testing_framework/          # 测试框架
│   │       ├── __init__.py
│   │       ├── test_generator.py       # 测试生成
│   │       ├── coverage_analyzer.py    # 覆盖率分析
│   │       ├── performance_tester.py   # 性能测试
│   │       └── security_scanner.py     # 安全扫描
│   │
│   └── entertainment/                   # 娱乐插件
│       ├── __init__.py
│       ├── games/                       # 游戏
│       │   ├── __init__.py
│       │   ├── puzzle_games.py          # 益智游戏
│       │   ├── trivia_engine.py         # 知识问答
│       │   ├── storytelling.py          # 故事讲述
│       │   └── interactive_fiction.py   # 互动小说
│       ├── media_player/                # 媒体播放器
│       │   ├── __init__.py
│       │   ├── music_player.py          # 音乐播放
│       │   ├── video_player.py          # 视频播放
│       │   ├── playlist_manager.py      # 播放列表
│       │   └── recommendation_engine.py # 推荐引擎
│       ├── social_interaction/          # 社交互动
│       │   ├── __init__.py
│       │   ├── chat_companion.py        # 聊天伴侣
│       │   ├── emotion_simulator.py     # 情感模拟
│       │   ├── personality_engine.py    # 性格引擎
│       │   └── conversation_topics.py   # 对话话题
│       └── educational/                 # 教育娱乐
│           ├── __init__.py
│           ├── language_learning.py     # 语言学习
│           ├── knowledge_quizzes.py     # 知识问答
│           ├── skill_builder.py         # 技能构建
│           └── interactive_lessons.py   # 互动课程
│
├── community/                           # 社区插件
│   ├── __init__.py
│   ├── third_party/                     # 第三方插件
│   │   ├── __init__.py
│   │   ├── social_media/                # 社交媒体
│   │   │   ├── __init__.py
│   │   │   ├── twitter_integration.py   # Twitter
│   │   │   ├── facebook_integration.py  # Facebook
│   │   │   ├── linkedin_integration.py  # LinkedIn
│   │   │   └── wechat_integration.py    # 微信
│   │   ├── ecommerce/                   # 电子商务
│   │   │   ├── __init__.py
│   │   │   ├── amazon_integration.py    # 亚马逊
│   │   │   ├── shopify_integration.py   # Shopify
│   │   │   ├── payment_processor.py     # 支付处理
│   │   │   └── inventory_manager.py     # 库存管理
│   │   ├── finance/                     # 金融理财
│   │   │   ├── __init__.py
│   │   │   ├── stock_tracker.py         # 股票追踪
│   │   │   ├── budget_planner.py        # 预算规划
│   │   │   ├── expense_tracker.py       # 支出追踪
│   │   │   └── investment_advisor.py    # 投资顾问
│   │   └── health_fitness/              # 健康健身
│   │       ├── __init__.py
│   │       ├── fitness_tracker.py       # 健身追踪
│   │       ├── nutrition_advisor.py     # 营养顾问
│   │       ├── meditation_guide.py      # 冥想指导
│   │       └── sleep_analyzer.py        # 睡眠分析
│   │
│   ├── user_created/                     # 用户创建插件
│   │   ├── __init__.py
│   │   ├── template_library/             # 模板库
│   │   │   ├── __init__.py
│   │   │   ├── basic_plugin_template.py # 基础模板
│   │   │   ├── ai_plugin_template.py    # AI插件模板
│   │   │   ├── integration_template.py  # 集成模板
│   │   │   └── utility_template.py      # 工具模板
│   │   ├── plugin_marketplace/          # 插件市场
│   │   │   ├── __init__.py
│   │   │   ├── plugin_discovery.py      # 插件发现
│   │   │   ├── rating_system.py         # 评分系统
│   │   │   ├── review_system.py         # 评论系统
│   │   │   └── download_manager.py      # 下载管理
│   │   └── collaboration_tools/         # 协作工具
│   │       ├── __init__.py
│   │       ├── plugin_sharing.py        # 插件分享
│   │       ├── version_control.py       # 版本控制
│   │       ├── code_review.py           # 代码审查
│   │       └── issue_tracker.py         # 问题追踪
│   │
│   └── experimental/                     # 实验性插件
│       ├── __init__.py
│       ├── research_prototypes/         # 研究原型
│       │   ├── __init__.py
│       │   ├── advanced_ai/             # 高级AI
│       │   │   ├── __init__.py
│       │   │   ├── neural_architecture.py # 神经架构
│       │   │   ├── cognitive_models.py  # 认知模型
│       │   │   └── emergent_behavior.py # 涌现行为
│       │   ├── new_paradigms/           # 新范式
│       │   │   ├── __init__.py
│       │   │   ├── quantum_computing.py # 量子计算
│       │   │   ├── neuromorphic_chips.py # 神经形态芯片
│       │   │   └── biological_computing.py # 生物计算
│       │   └── futuristic_interfaces/   # 未来界面
│       │       ├── __init__.py
│       │       ├── brain_computer_interface.py # 脑机接口
│       │       ├── holographic_display.py # 全息显示
│       │       └── tactile_feedback.py  # 触觉反馈
│       │
│       └── beta_features/               # Beta功能
│           ├── __init__.py
│           ├── unstable_apis/           # 不稳定API
│           │   ├── __init__.py
│           │   ├── experimental_ai.py   # 实验性AI
│           │   ├── bleeding_edge.py     # 前沿功能
│           │   └── prototype_features.py # 原型功能
│           ├── performance_testing/     # 性能测试
│           │   ├── __init__.py
│           │   ├── stress_tester.py     # 压力测试
│           │   ├── benchmark_tools.py   # 基准测试
│           │   └── profiling_utilities.py # 性能分析
│           └── compatibility_layers/    # 兼容层
│               ├── __init__.py
│               ├── legacy_support.py    # 传统系统支持
│               ├── cross_platform.py    # 跨平台兼容
│               └── emulation_layer.py   # 模拟层
│
└── development_tools/                   # 开发工具
    ├── __init__.py
    ├── plugin_sdk/                      # 插件SDK
    │   ├── __init__.py
    │   ├── api_library/                 # API库
    │   │   ├── __init__.py
    │   │   ├── core_apis.py             # 核心API
    │   │   ├── extension_apis.py        # 扩展API
    │   │   ├── utility_functions.py     # 工具函数
    │   │   └── type_definitions.py      # 类型定义
    │   ├── development_templates/       # 开发模板
    │   │   ├── __init__.py
    │   │   ├── basic_plugin/            # 基础插件模板
    │   │   │   ├── __init__.py
    │   │   │   ├── plugin_structure.py  # 插件结构
    │   │   │   ├── manifest_template.py # 清单模板
    │   │   │   └── example_code.py      # 示例代码
    │   │   ├── ai_plugin/               # AI插件模板
    │   │   │   ├── __init__.py
    │   │   │   ├── model_integration.py # 模型集成
    │   │   │   ├── training_pipeline.py # 训练流水线
    │   │   │   └── inference_engine.py  # 推理引擎
    │   │   └── integration_plugin/      # 集成插件模板
    │   │       ├── __init__.py
    │   │       ├── api_wrapper.py       # API包装器
    │   │       ├── data_adapter.py      # 数据适配器
    │   │       └── protocol_handler.py  # 协议处理器
    │   ├── testing_framework/           # 测试框架
    │   │   ├── __init__.py
    │   │   ├── unit_testing.py          # 单元测试
    │   │   ├── integration_testing.py   # 集成测试
    │   │   ├── performance_testing.py   # 性能测试
    │   │   └── security_testing.py      # 安全测试
    │   └── deployment_tools/            # 部署工具
    │       ├── __init__.py
    │       ├── packaging_tool.py        # 打包工具
    │       ├── signing_utility.py       # 签名工具
    │       ├── distribution_tool.py     # 分发工具
    │       └── update_manager.py        # 更新管理
    │
    ├── debug_tools/                     # 调试工具
    │   ├── __init__.py
    │   ├── plugin_debugger.py           # 插件调试器
    │   ├── performance_profiler.py      # 性能分析器
    │   ├── memory_analyzer.py           # 内存分析器
    │   ├── log_analyzer.py              # 日志分析器
    │   └── diagnostic_tools.py          # 诊断工具
    │
    └── documentation_tools/             # 文档工具
        ├── __init__.py
        ├── api_documentation_generator.py # API文档生成器
        ├── code_documentation.py        # 代码文档工具
        ├── tutorial_generator.py        # 教程生成器
        ├── example_code_generator.py    # 示例代码生成器
        └── documentation_validator.py   # 文档验证器
🧪 测试套件 (tests/)
text
tests/
├── __init__.py
├── unit_tests/                          # 单元测试
│   ├── __init__.py
│   ├── infrastructure/                  # 基础设施层测试
│   │   ├── __init__.py
│   │   ├── test_model_serving.py        # 模型服务测试
│   │   ├── test_message_bus.py          # 消息总线测试
│   │   ├── test_vector_database.py      # 向量数据库测试
│   │   ├── test_resource_manager.py     # 资源管理器测试
│   │   ├── test_cache_manager.py        # 缓存管理器测试
│   │   ├── test_network_manager.py      # 网络管理器测试
│   │   ├── test_data_pipelines.py       # 数据管道测试
│   │   ├── test_platform_adapters.py    # 平台适配器测试
│   │   ├── test_hardware_detector.py    # 硬件检测测试
│   │   ├── test_model_manager.py        # ⭐【新增】模型管理器测试
│   │   └── test_smart_router.py         # ⭐【新增】智能路由测试
│   │
│   ├── data/                            # 数据层测试
│   │   ├── __init__.py
│   │   ├── test_speech_models.py        # 语音模型测试
│   │   ├── test_vision_models.py        # 视觉模型测试
│   │   ├── test_nlp_models.py           # NLP模型测试
│   │   ├── test_3d_models.py            # 3D模型测试
│   │   ├── test_vector_db.py            # 向量数据库测试
│   │   ├── test_graph_db                # 图数据库测试 ⭐【强化】
│   │   │   ├── __init__.py
│   │   │   ├── test_knowledge_graph.py  # 知识图谱测试
│   │   │   └── test_neo4j_integration.py # Neo4j集成测试
│   │   ├── test_time_series_db.py       # 时序数据库测试
│   │   ├── test_relational_db.py        # 关系数据库测试
│   │   ├── test_user_data.py            # 用户数据测试
│   │   └── test_system_data.py          # 系统数据测试
│   │
│   ├── cognitive/                       # 认知层测试 ⭐【强化】
│   │   ├── __init__.py
│   │   ├── test_task_decomposer.py      # 任务分解器测试
│   │   ├── test_hierarchical_planner.py # 分层规划器测试
│   │   ├── test_problem_analyzer.py     # 问题分析器测试
│   │   ├── test_meta_learner.py         # 元学习器测试
│   │   ├── test_skill_acquisition.py    # 技能获取测试
│   │   ├── test_episodic_memory.py      # 情景记忆测试
│   │   ├── test_semantic_memory.py      # 语义记忆测试
│   │   ├── test_procedural_memory.py    # 程序记忆测试
│   │   ├── test_coordinator.py          # 协调器测试
│   │   ├── test_creative_agent.py       # 创意智能体测试
│   │   ├── test_technical_agent.py      # 技术智能体测试
│   │   ├── test_personal_agent.py       # 个人助理测试
│   │   ├── test_chain_of_thought.py     # ⭐【新增】思维链测试
│   │   ├── test_self_reflection.py      # ⭐【新增】自我反思测试
│   │   ├── test_emotion_nn.py           # ⭐【新增】情绪神经网络测试
│   │   ├── test_reinforcement_learner.py # ⭐【新增】强化学习测试
│   │   └── test_smart_memory.py         # ⭐【新增】智能记忆测试
│   │
│   ├── capabilities/                    # 能力层测试 ⭐【强化】
│   │   ├── __init__.py
│   │   ├── test_document_generator.py   # 文档生成器测试
│   │   ├── test_presentation_generator.py # PPT生成器测试
│   │   ├── test_image_generator.py      # 图像生成器测试
│   │   ├── test_application_launcher.py # 应用启动器测试
│   │   ├── test_automation_engine.py    # 自动化引擎测试
│   │   ├── test_ui_automation.py        # UI自动化测试
│   │   ├── test_threat_detector.py      # 威胁检测器测试
│   │   ├── test_performance_monitor.py  # 性能监控器测试
│   │   ├── test_web_browser.py          # 网页浏览器测试
│   │   ├── test_office_tools.py         # Office工具测试
│   │   ├── test_development_tools.py    # 开发工具测试
│   │   ├── test_real_time_knowledge.py  # ⭐【新增】实时知识更新测试
│   │   ├── test_auto_ingestion.py       # ⭐【新增】主动知识摄取测试
│   │   └── test_avatar_customizer.py    # ⭐【新增】形象自定义测试
│   │
│   ├── interaction/                     # 交互层测试
│   │   ├── __init__.py
│   │   ├── test_realtime_renderer.py    # 实时渲染器测试
│   │   ├── test_character_system.py     # 角色系统测试
│   │   ├── test_behavior_system.py      # 行为系统测试
│   │   ├── test_lip_sync_engine.py      # 嘴唇同步引擎测试
│   │   ├── test_speech_recognizer.py    # 语音识别测试
│   │   ├── test_computer_vision.py      # 计算机视觉测试
│   │   ├── test_text_input.py           # 文本输入测试
│   │   ├── test_speech_output.py        # 语音输出测试
│   │   ├── test_visual_feedback.py      # 视觉反馈测试
│   │   └── test_dialogue_manager.py     # 对话管理器测试
│   │
│   ├── application/                     # 应用层测试
│   │   ├── __init__.py
│   │   ├── test_desktop_app.py          # 桌面应用测试
│   │   ├── test_mobile_app.py           # 移动应用测试
│   │   ├── test_web_interface.py        # Web界面测试
│   │   ├── test_device_connector.py     # 设备连接器测试
│   │   ├── test_protocol_adapters.py    # 协议适配器测试
│   │   ├── test_smart_home.py           # 智能家居测试
│   │   ├── test_data_sync.py            # 数据同步测试
│   │   ├── test_rest_api.py             # REST API测试
│   │   ├── test_plugin_system.py        # 插件系统测试
│   │   └── test_sdk_development.py      # SDK开发测试
│   │
│   ├── security/                        # 安全层测试 ⭐【强化】
│   │   ├── __init__.py
│   │   ├── test_biometric_auth.py       # 生物认证测试
│   │   ├── test_multi_factor_auth.py    # 多因素认证测试
│   │   ├── test_permission_manager.py   # 权限管理测试
│   │   ├── test_data_encryption.py      # 数据加密测试
│   │   ├── test_differential_privacy.py # 差分隐私测试
│   │   ├── test_consent_manager.py      # 同意管理测试
│   │   ├── test_threat_detection.py     # 威胁检测测试
│   │   ├── test_behavior_analysis.py    # 行为分析测试
│   │   ├── test_compliance_checker.py   # 合规检查测试
│   │   ├── test_incident_response.py    # ⭐【新增】事件响应测试
│   │   ├── test_input_filter.py         # ⭐【新增】输入过滤测试
│   │   └── test_audit_logger.py         # ⭐【新增】审计日志测试
│   │
│   └── deployment/                      # 部署层测试
│       ├── __init__.py
│       ├── test_docker_configs.py       # Docker配置测试
│       ├── test_kubernetes_manifests.py # Kubernetes清单测试
│       ├── test_monitoring_system.py    # 监控系统测试
│       ├── test_alert_manager.py        # 告警管理测试
│       ├── test_performance_dashboard.py # 性能仪表板测试
│       ├── test_backup_recovery.py      # 备份恢复测试
│       ├── test_ci_cd_pipelines.py      # CI/CD流水线测试
│       ├── test_deployment_strategies.py # 部署策略测试
│       └── test_platform_specific.py    # 平台特定部署测试
│
├── integration_tests/                   # 集成测试
│   ├── __init__.py
│   ├── end_to_end/                      # 端到端测试
│   │   ├── __init__.py
│   │   ├── test_user_journey.py         # 用户旅程测试
│   │   ├── test_complex_tasks.py        # 复杂任务测试
│   │   ├── test_multi_modal_interaction.py # 多模态交互测试
│   │   ├── test_memory_retrieval.py     # 记忆检索测试
│   │   ├── test_learning_adaptation.py  # 学习适应测试
│   │   ├── test_security_scenarios.py   # 安全场景测试
│   │   ├── test_multi_model_routing.py  # ⭐【新增】多模型路由集成测试
│   │   ├── test_knowledge_graph_flow.py # ⭐【新增】知识图谱流程测试
│   │   └── test_emotion_recognition_flow.py # ⭐【新增】情绪识别流程测试
│   │
│   ├── system_integration/              # 系统集成测试
│   │   ├── __init__.py
│   │   ├── test_infrastructure_integration.py # 基础设施集成测试
│   │   ├── test_data_flow.py            # 数据流测试
│   │   ├── test_cognitive_workflow.py   # 认知工作流测试
│   │   ├── test_capability_integration.py # 能力集成测试
│   │   ├── test_interaction_flow.py     # 交互流程测试
│   │   ├── test_application_integration.py # 应用集成测试
│   │   ├── test_security_integration.py # 安全集成测试
│   │   └── test_deployment_integration.py # 部署集成测试
│   │
│   ├── api_integration/                 # API集成测试
│   │   ├── __init__.py
│   │   ├── test_rest_api_integration.py # REST API集成测试
│   │   ├── test_plugin_api_integration.py # 插件API集成测试
│   │   ├── test_sdk_integration.py      # SDK集成测试
│   │   ├── test_third_party_integration.py # 第三方集成测试
│   │   └── test_webhook_integration.py  # Webhook集成测试
│   │
│   └── performance_integration/         # 性能集成测试
│       ├── __init__.py
│       ├── test_system_performance.py   # 系统性能测试
│       ├── test_concurrent_users.py     # 并发用户测试
│       ├── test_memory_usage.py         # 内存使用测试
│       ├── test_response_times.py       # 响应时间测试
│       ├── test_scalability.py          # 可扩展性测试
│       ├── test_stress_conditions.py    # 压力条件测试
│       ├── test_model_switch_latency.py # ⭐【新增】模型切换延迟测试
│       └── test_knowledge_query_perf.py # ⭐【新增】知识图谱查询性能测试
│
├── performance_tests/                   # 性能测试
│   ├── __init__.py
│   ├── load_testing/                    # 负载测试
│   │   ├── __init__.py
│   │   ├── test_concurrent_requests.py  # 并发请求测试
│   │   ├── test_throughput.py           # 吞吐量测试
│   │   ├── test_resource_utilization.py # 资源利用率测试
│   │   ├── test_memory_leaks.py         # 内存泄漏测试
│   │   ├── test_cpu_usage.py            # CPU使用测试
│   │   └── test_network_bandwidth.py    # 网络带宽测试
│   │
│   ├── stress_testing/                  # 压力测试
│   │   ├── __init__.py
│   │   ├── test_peak_load.py            # 峰值负载测试
│   │   ├── test_endurance.py            # 耐久性测试
│   │   ├── test_failure_recovery.py     # 故障恢复测试
│   │   ├── test_degradation.py          # 性能降级测试
│   │   └── test_breakpoint.py           # 断点测试
│   │
│   ├── benchmark_tests/                 # 基准测试
│   │   ├── __init__.py
│   │   ├── test_ai_model_performance.py # AI模型性能测试
│   │   ├── test_database_performance.py # 数据库性能测试
│   │   ├── test_rendering_performance.py # 渲染性能测试
│   │   ├── test_network_performance.py  # 网络性能测试
│   │   ├── test_storage_performance.py  # 存储性能测试
│   │   ├── test_computation_performance.py # 计算性能测试
│   │   ├── benchmark_llama_70b.py       # ⭐【新增】Llama 70B基准测试
│   │   ├── benchmark_qwen_32b.py        # ⭐【新增】Qwen 32B基准测试
│   │   └── benchmark_deepseek.py        # ⭐【新增】DeepSeek基准测试
│   │
│   └── scalability_tests/               # 可扩展性测试
│       ├── __init__.py
│       ├── test_horizontal_scaling.py   # 水平扩展测试
│       ├── test_vertical_scaling.py     # 垂直扩展测试
│       ├── test_cluster_performance.py  # 集群性能测试
│       ├── test_distributed_systems.py  # 分布式系统测试
│       └── test_failover.py             # 故障转移测试
│
├── security_tests/                      # 安全测试 ⭐【强化】
│   ├── __init__.py
│   ├── penetration_testing/             # 渗透测试
│   │   ├── __init__.py
│   │   ├── test_network_security.py     # 网络安全测试
│   │   ├── test_application_security.py # 应用安全测试
│   │   ├── test_api_security.py         # API安全测试
│   │   ├── test_data_security.py        # 数据安全测试
│   │   ├── test_authentication_security.py # 认证安全测试
│   │   ├── test_authorization_security.py # 授权安全测试
│   │   ├── test_input_injection.py      # ⭐【新增】输入注入测试
│   │   └── test_jailbreak_attempts.py   # ⭐【新增】越狱尝试测试
│   │
│   ├── vulnerability_assessment/        # 漏洞评估
│   │   ├── __init__.py
│   │   ├── test_code_vulnerabilities.py # 代码漏洞测试
│   │   ├── test_configuration_vulnerabilities.py # 配置漏洞测试
│   │   ├── test_dependency_vulnerabilities.py # 依赖漏洞测试
│   │   ├── test_infrastructure_vulnerabilities.py # 基础设施漏洞测试
│   │   └── test_human_factors.py        # 人为因素测试
│   │
│   ├── compliance_testing/              # 合规性测试
│   │   ├── __init__.py
│   │   ├── test_gdpr_compliance.py      # GDPR合规测试
│   │   ├── test_hipaa_compliance.py     # HIPAA合规测试
│   │   ├── test_pci_compliance.py       # PCI合规测试
│   │   ├── test_iso_compliance.py       # ISO合规测试
│   │   └── test_industry_standards.py   # 行业标准测试
│   │
│   └── privacy_testing/                 # 隐私测试
│       ├── __init__.py
│       ├── test_data_protection.py      # 数据保护测试
│       ├── test_anonymization.py        # 匿名化测试
│       ├── test_consent_management.py   # 同意管理测试
│       ├── test_data_retention.py       # 数据保留测试
│       └── test_privacy_policies.py     # 隐私策略测试
│
├── usability_tests/                     # 可用性测试
│   ├── __init__.py
│   ├── user_experience/                 # 用户体验测试
│   │   ├── __init__.py
│   │   ├── test_interface_design.py     # 界面设计测试
│   │   ├── test_interaction_flow.py     # 交互流程测试
│   │   ├── test_accessibility.py        # 可访问性测试
│   │   ├── test_responsiveness.py       # 响应性测试
│   │   ├── test_error_handling.py       # 错误处理测试
│   │   ├── test_first_run_experience.py # ⭐【新增】首次运行体验测试
│   │   └── test_avatar_customization_ux.py # ⭐【新增】形象自定义体验测试
│   │
│   ├── accessibility_testing/           # 可访问性测试
│   │   ├── __init__.py
│   │   ├── test_screen_reader.py        # 屏幕阅读器测试
│   │   ├── test_keyboard_navigation.py  # 键盘导航测试
│   │   ├── test_contrast_ratio.py       # 对比度测试
│   │   ├── test_font_size.py            # 字体大小测试
│   │   └── test_voice_control.py        # 语音控制测试
│   │
│   └── localization_testing/            # 本地化测试
│       ├── __init__.py
│       ├── test_language_support.py     # 语言支持测试
│       ├── test_cultural_adaptation.py  # 文化适应测试
│       ├── test_date_time_format.py     # 日期时间格式测试
│       ├── test_currency_support.py     # 货币支持测试
│       └── test_regional_settings.py    # 区域设置测试
│
├── test_utilities/                      # 测试工具
│   ├── __init__.py
│   ├── test_data_generators/            # 测试数据生成器
│   │   ├── __init__.py
│   │   ├── user_data_generator.py       # 用户数据生成器
│   │   ├── conversation_data_generator.py # 对话数据生成器
│   │   ├── task_data_generator.py       # 任务数据生成器
│   │   ├── performance_data_generator.py # 性能数据生成器
│   │   ├── security_data_generator.py   # 安全数据生成器
│   │   ├── knowledge_graph_generator.py # ⭐【新增】知识图谱数据生成器
│   │   └── emotion_data_generator.py    # ⭐【新增】情绪数据生成器
│   │
│   ├── mock_objects/                    # 模拟对象
│   │   ├── __init__.py
│   │   ├── mock_ai_models.py            # AI模型模拟
│   │   ├── mock_databases.py            # 数据库模拟
│   │   ├── mock_services.py             # 服务模拟
│   │   ├── mock_hardware.py             # 硬件模拟
│   │   ├── mock_networks.py             # 网络模拟
│   │   ├── mock_neo4j.py                # ⭐【新增】Neo4j模拟
│   │   └── mock_llm_responses.py        # ⭐【新增】LLM响应模拟
│   │
│   ├── test_fixtures/                   # 测试夹具
│   │   ├── __init__.py
│   │   ├── setup_fixtures.py            # 设置夹具
│   │   ├── teardown_fixtures.py         # 清理夹具
│   │   ├── database_fixtures.py         # 数据库夹具
│   │   ├── user_fixtures.py             # 用户夹具
│   │   ├── system_fixtures.py           # 系统夹具
│   │   ├── model_fixtures.py            # ⭐【新增】模型夹具
│   │   └── knowledge_graph_fixtures.py  # ⭐【新增】知识图谱夹具
│   │
│   └── test_helpers/                    # 测试辅助工具
│       ├── __init__.py
│       ├── assertion_helpers.py         # 断言辅助工具
│       ├── comparison_helpers.py        # 比较辅助工具
│       ├── validation_helpers.py        # 验证辅助工具
│       ├── performance_helpers.py       # 性能辅助工具
│       └── security_helpers.py          # 安全辅助工具
│
└── test_reports/                        # 测试报告
    ├── __init__.py
    ├── report_generators/               # 报告生成器
    │   ├── __init__.py
    │   ├── unit_test_reporter.py        # 单元测试报告生成器
    │   ├── integration_test_reporter.py # 集成测试报告生成器
    │   ├── performance_test_reporter.py # 性能测试报告生成器
    │   ├── security_test_reporter.py    # 安全测试报告生成器
    │   └── usability_test_reporter.py   # 可用性测试报告生成器
    │
    ├── analytics_tools/                 # 分析工具
    │   ├── __init__.py
    │   ├── test_coverage_analyzer.py    # 测试覆盖率分析器
    │   ├── performance_analyzer.py      # 性能分析器
    │   ├── trend_analyzer.py            # 趋势分析器
    │   ├── defect_analyzer.py           # 缺陷分析器
    │   └── quality_metrics.py           # 质量指标分析器
    │
    ├── visualization_tools/             # 可视化工具
    │   ├── __init__.py
    │   ├── dashboard_generator.py       # 仪表板生成器
    │   ├── chart_generator.py           # 图表生成器
    │   ├── heatmap_generator.py         # 热图生成器
    │   ├── timeline_visualizer.py       # 时间线可视化器
    │   └── comparison_visualizer.py     # 比较可视化器
    │
    └── export_tools/                    # 导出工具
        ├── __init__.py
        ├── html_exporter.py             # HTML导出器
        ├── pdf_exporter.py              # PDF导出器
        ├── json_exporter.py             # JSON导出器
        ├── csv_exporter.py              # CSV导出器
        └── xml_exporter.py              # XML导出器
🔧 工具函数库 (utils/)
text
utils/
├── __init__.py
├── common_utilities/                    # 通用工具
│   ├── __init__.py
│   ├── file_utils.py                    # 文件操作工具
│   ├── string_utils.py                  # 字符串工具
│   ├── date_utils.py                    # 日期时间工具
│   ├── math_utils.py                    # 数学工具
│   ├── collection_utils.py               # 集合工具
│   ├── validation_utils.py               # 验证工具
│   ├── conversion_utils.py               # 转换工具
│   ├── encoding_utils.py                 # 编码工具
│   ├── compression_utils.py              # 压缩工具
│   └── common_metrics.py                 # 通用指标
│
├── ai_utilities/                         # AI工具 ⭐【强化】
│   ├── __init__.py
│   ├── model_utils.py                    # 模型工具：加载、保存、转换
│   ├── preprocessing_utils.py            # 预处理工具
│   ├── inference_utils.py                # 推理工具
│   ├── training_utils.py                 # 训练工具
│   ├── evaluation_utils.py               # 评估工具
│   ├── visualization_utils.py            # 可视化工具
│   ├── data_augmentation.py              # 数据增强
│   ├── hyperparameter_utils.py           # 超参数工具
│   ├── quantization_utils.py             # 量化工具
│   ├── gguf_utils.py                     # ⭐【新增】GGUF格式处理
│   ├── model_router_utils.py             # ⭐【新增】模型路由辅助
│   └── ai_metrics.py                     # AI指标
│
├── data_processing/                      # 数据处理工具
│   ├── __init__.py
│   ├── data_cleaning.py                  # 数据清洗
│   ├── data_transformation.py            # 数据转换
│   ├── feature_engineering.py            # 特征工程
│   ├── data_sampling.py                  # 数据采样
│   ├── data_validation.py                # 数据验证
│   ├── data_serialization.py             # 数据序列化
│   ├── data_formatting.py                # 数据格式化
│   ├── data_analysis.py                  # 数据分析
│   └── data_metrics.py                   # 数据指标
│
├── network_utilities/                    # 网络工具
│   ├── __init__.py
│   ├── http_utils.py                     # HTTP工具
│   ├── websocket_utils.py                # WebSocket工具
│   ├── socket_utils.py                    # Socket工具
│   ├── protocol_utils.py                  # 协议工具
│   ├── network_monitoring.py              # 网络监控
│   ├── tcp_utils.py                       # TCP协议工具
│   ├── udp_utils.py                       # UDP协议工具
│   ├── security_utils.py                  # 网络安全工具
│   ├── proxy_utils.py                     # 代理工具
│   ├── dns_utils.py                       # DNS工具
│   └── network_metrics.py                 # 网络指标
│
├── system_utilities/                     # 系统工具
│   ├── __init__.py
│   ├── process_utils.py                  # 进程工具
│   ├── memory_utils.py                    # 内存工具
│   ├── cpu_utils.py                       # CPU工具
│   ├── disk_utils.py                      # 磁盘工具
│   ├── system_info.py                     # 系统信息
│   ├── performance_utils.py               # 性能工具
│   ├── logging_utils.py                   # 日志工具
│   ├── configuration_utils.py             # 配置工具
│   └── system_metrics.py                  # 系统指标
│
├── security_utilities/                   # 安全工具 ⭐【强化】
│   ├── __init__.py
│   ├── encryption_utils.py                # 加密工具
│   ├── authentication_utils.py            # 认证工具
│   ├── authorization_utils.py             # 授权工具
│   ├── token_utils.py                     # 令牌工具
│   ├── hash_utils.py                      # 哈希工具
│   ├── certificate_utils.py               # 证书工具
│   ├── security_scanning.py               # 安全扫描
│   ├── audit_utils.py                     # 审计工具
│   ├── input_sanitizer.py                 # ⭐【新增】输入清洗
│   ├── jailbreak_detection.py             # ⭐【新增】越狱检测
│   └── security_metrics.py                 # 安全指标
│
├── ui_utilities/                         # UI工具
│   ├── __init__.py
│   ├── layout_utils.py                    # 布局工具
│   ├── styling_utils.py                   # 样式工具
│   ├── animation_utils.py                 # 动画工具
│   ├── event_utils.py                     # 事件工具
│   ├── responsive_utils.py                 # 响应式工具
│   ├── accessibility_utils.py             # 可访问性工具
│   ├── localization_utils.py               # 本地化工具
│   ├── theme_utils.py                     # 主题工具
│   └── ui_metrics.py                      # UI指标
│
├── database_utilities/                    # 数据库工具 ⭐【强化】
│   ├── __init__.py
│   ├── connection_utils.py                # 连接工具
│   ├── query_utils.py                     # 查询工具
│   ├── migration_utils.py                  # 迁移工具
│   ├── backup_utils.py                    # 备份工具
│   ├── performance_utils.py                # 性能工具
│   ├── security_utils.py                   # 安全工具
│   ├── replication_utils.py                # 复制工具
│   ├── monitoring_utils.py                 # 监控工具
│   ├── neo4j_utils.py                      # ⭐【新增】Neo4j辅助工具
│   ├── graph_query_utils.py                # ⭐【新增】图查询工具
│   └── database_metrics.py                 # 数据库指标
│
├── testing_utilities/                     # 测试工具
│   ├── __init__.py
│   ├── test_data_utils.py                 # 测试数据工具
│   ├── assertion_utils.py                  # 断言工具
│   ├── mock_utils.py                       # 模拟工具
│   ├── fixture_utils.py                    # 夹具工具
│   ├── coverage_utils.py                   # 覆盖率工具
│   ├── performance_utils.py                # 性能工具
│   ├── security_utils.py                   # 安全工具
│   ├── report_utils.py                     # 报告工具
│   └── testing_metrics.py                  # 测试指标
│
└── deployment_utilities/                  # 部署工具
    ├── __init__.py
    ├── container_utils.py                  # 容器工具
    ├── orchestration_utils.py              # 编排工具
    ├── monitoring_utils.py                 # 监控工具
    ├── logging_utils.py                    # 日志工具
    ├── backup_utils.py                     # 备份工具
    ├── scaling_utils.py                    # 扩缩容工具
    ├── security_utils.py                   # 安全工具
    ├── configuration_utils.py              # 配置工具
    └── deployment_metrics.py               # 部署指标
