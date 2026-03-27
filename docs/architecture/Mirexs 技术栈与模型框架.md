# Mirexs 技术栈与模型框架完整清单（v2.0）

## 🧠 AI 框架与推理引擎

### 核心AI框架
- **PyTorch 2.1+** - 主要深度学习框架（CUDA 12.1支持）
- **TensorFlow 2.15** - 辅助框架，用于特定预训练模型
- **Hugging Face Transformers 4.38+** - NLP模型生态系统
- **JAX/Flax** - 高性能实验性模型
- **ONNX Runtime** - 跨平台模型推理优化

### 本地推理后端（新增）
- **llama.cpp** - 主推理引擎，支持GGUF量化模型
- **vLLM** - 高吞吐量推理，服务器矩阵专用
- **ExLlama** - 极致速度量化推理

### 推理服务引擎
- **NVIDIA Triton** - 生产级模型服务
- **TensorFlow Serving** - TensorFlow模型服务
- **TorchServe** - PyTorch模型服务
- **OpenVINO** - Intel硬件优化推理
- **TensorRT** - NVIDIA GPU推理优化

---

## 🗣️ 语音处理技术栈

### 语音识别 (ASR)
- **OpenAI Whisper** - 多语言语音识别主力
- **Vosk** - 离线语音识别备用
- **NVIDIA NeMo** - 企业级ASR方案
- **WeNet** - 中文优化语音识别
- **SpeechBrain** - 研究级语音工具包

### 语音合成 (TTS)
- **Coqui TTS** - 主要TTS引擎
- **XTTS** - 跨语言语音合成
- **Microsoft Speech API** - 商业TTS备用
- **eSpeak NG** - 轻量级备用方案
- **Festival** - 传统TTS系统

### 语音处理工具
- **Librosa** - 音频分析处理
- **PyAudio** - 音频流处理
- **SoundFile** - 音频文件I/O
- **pydub** - 音频格式转换
- **noisereduce** - 噪声抑制

---

## 👁️ 计算机视觉技术栈

### 人脸与表情识别
- **InsightFace** - 人脸识别主力
- **MediaPipe** - 实时人脸、手势、姿态检测
- **OpenCV** - 计算机视觉基础库
- **Dlib** - 传统人脸检测
- **Face Recognition** - 简化人脸识别

### 图像处理与分析
- **Pillow (PIL)** - 图像处理基础
- **scikit-image** - 图像分析算法
- **OpenCV** - 实时视觉处理
- **Albumentations** - 数据增强

### 目标检测与场景理解
- **YOLOv8/v9** - 实时目标检测
- **DETR** - Transformer目标检测
- **CLIP** - 视觉语言理解
- **Segment Anything** - 图像分割

---

## 📝 自然语言处理技术栈

### 大语言模型（组合模型方案）
| 场景 | 模型 | 用途 |
|------|------|------|
| 日常聊天/情感陪伴 | Llama 3.1 70B / Qwen 3.5 32B | 主力日常模型 |
| 编程/复杂推理 | DeepSeek V3 / Qwen3-Coder-32B | 编程与深度推理 |
| 长上下文 (>128K) | Llama 4 Maverick / Qwen3-Next | 长对话与复杂分析 |
| 多模态（图文/视频） | Llama 4 Scout / Qwen3-Omni | 图像与视频理解 |

### NLP基础工具
- **spaCy** - 工业级NLP处理
- **NLTK** - 传统NLP工具包
- **jieba** - 中文分词
- **sentence-transformers** - 文本嵌入（升级版）
- **Gensim** - 主题建模

### 文本处理
- **transformers** - Transformer模型库
- **accelerate** - 分布式训练
- **bitsandbytes** - 模型量化
- **peft** - 参数高效微调

---

## 🎮 3D渲染与图形技术栈

### 3D引擎
- **Panda3D** - 主要3D渲染引擎
- **Unity** - 备选3D引擎（通过插件集成）
- **OpenGL** - 底层图形API
- **Vulkan** - 高性能图形API

### 3D模型与动画
- **Blender** - 3D模型创建与编辑
- **FBX SDK** - 3D模型格式支持
- **Assimp** - 模型导入库
- **Bullet Physics** - 物理引擎

### 图形处理
- **Pillow** - 2D图像处理
- **Matplotlib** - 数据可视化
- **Plotly** - 交互式可视化
- **VTK** - 科学可视化

---

## 💾 数据库与存储技术栈

### 向量数据库
- **Chroma** - 主要向量数据库
- **FAISS** - 向量相似性搜索
- **Pinecone** - 云向量数据库（可选）
- **Weaviate** - 图向量混合数据库

### 图数据库（新增）
- **Neo4j** - 主要图数据库（知识图谱核心）
- **NetworkX** - 内存图计算
- **Apache Age** - PostgreSQL图扩展

### 时序数据库
- **InfluxDB** - 主要时序数据库
- **TimescaleDB** - PostgreSQL时序扩展
- **Prometheus** - 监控时序数据

### 关系数据库
- **PostgreSQL** - 主要关系数据库
- **SQLite** - 嵌入式数据库
- **MySQL** - 备选关系数据库

### 缓存系统
- **Redis** - 内存数据存储
- **Memcached** - 分布式缓存
- **LMDB** - 轻量级键值存储

---

## 🌐 后端与API技术栈

### Web框架
- **FastAPI** - 主要API框架
- **Flask** - 轻量级Web框架
- **Sanic** - 异步Web框架
- **Django** - 全功能Web框架（管理界面）

### 消息队列与通信
- **Redis Pub/Sub** - 实时消息
- **RabbitMQ** - 企业级消息队列
- **ZeroMQ** - 轻量级消息
- **WebSocket** - 实时双向通信

### API网关与代理
- **Nginx** - Web服务器与反向代理
- **Traefik** - 动态反向代理
- **Kong** - API网关

---

## 📱 前端与客户端技术栈

### 桌面应用
- **Electron** - 跨平台桌面应用
- **Qt** - 原生C++ UI框架
- **Tauri** - 轻量级桌面应用

### 移动应用
- **React Native** - 跨平台移动应用
- **Flutter** - Google跨平台UI工具包
- **Android Native (Kotlin)** - Android原生
- **iOS Native (Swift)** - iOS原生

### Web前端
- **React** - 主要前端框架
- **TypeScript** - 类型安全JavaScript
- **Three.js** - Web 3D渲染
- **WebGL** - 浏览器3D图形

---

## 🔧 开发工具与基础设施

### 编程语言
- **Python 3.9+** - 主要开发语言
- **C++** - 性能关键组件
- **JavaScript/TypeScript** - 前端开发
- **Rust** - 系统级组件（Tauri用）

### 容器化与编排
- **Docker** - 应用容器化
- **Docker Compose** - 开发环境编排
- **Kubernetes** - 生产环境编排
- **Helm** - Kubernetes包管理

### CI/CD与DevOps
- **GitLab CI** - 主要CI/CD平台
- **GitHub Actions** - 备选CI/CD
- **Jenkins** - 企业级CI/CD
- **Argo CD** - GitOps持续部署

### 监控与可观测性
- **Prometheus** - 指标收集
- **Grafana** - 数据可视化
- **ELK Stack** - 日志管理
- **Jaeger** - 分布式追踪
- **Loki** - 日志聚合

---

## 🔐 安全与加密技术栈

### 加密库
- **cryptography** - Python加密库
- **OpenSSL** - 底层加密
- **libsodium** - 现代加密
- **age** - 简单文件加密

### 身份认证
- **OAuth 2.0/OpenID Connect** - 身份协议
- **JWT** - 令牌认证
- **Passport.js** - 身份认证中间件

### 安全工具
- **Bandit** - Python安全扫描
- **Trivy** - 容器漏洞扫描
- **ClamAV** - 恶意软件扫描
- **Fail2ban** - 入侵防护
- **Auditd** - 系统审计日志

---

## 📊 数据处理与机器学习运维

### 数据处理
- **Apache Spark** - 大数据处理
- **Pandas** - 数据分析
- **NumPy** - 数值计算
- **Dask** - 并行计算

### 特征存储
- **Feast** - 特征存储
- **Hopsworks** - 企业级特征平台

### 实验追踪
- **MLflow** - 机器学习生命周期
- **Weights & Biases** - 实验追踪
- **TensorBoard** - TensorFlow可视化

### 机器学习
- **scikit-learn** - 分类器、聚类（情绪识别用）
- **PyTorch Lightning** - 训练简化

---

## 🎯 智能路由机制

Mirexs 2.0 核心创新：**智能模型路由系统**

```python
# infrastructure/model_hub/smart_router.py

根据硬件检测自动选择：
- 低配（RTX 3060以下）：Llama 3.1 8B / Qwen 3.5 8B
- 中配（RTX 3060-4080）：Qwen 3.5 32B
- 高配（RTX 4090+）：Llama 3.1 70B / DeepSeek V3

根据任务类型自动切换：
- 日常聊天：Qwen 3.5 32B（快、自然）
- 编程任务：DeepSeek V3 / Qwen3-Coder-32B
- 长文本分析：Llama 4 Maverick
- 图像理解：Qwen3-Omni
📦 系统依赖与运行时
Python主要依赖包版本要求
text
torch>=2.1.0
transformers>=4.38.0
accelerate>=0.28.0
llama-cpp-python>=0.2.58
sentence-transformers>=2.6.0
neo4j>=5.14.0
scikit-learn>=1.4.0
系统级依赖
CUDA 12.0+ - NVIDIA GPU计算

cuDNN 8.0+ - 深度学习加速

NVIDIA Drivers 545+ - GPU驱动

FFmpeg - 音视频处理

OpenCL - 跨平台GPU计算

Git LFS - 大模型下载

Java 17+ - Neo4j运行环境