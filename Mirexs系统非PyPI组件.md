## 🖥️ 系统级依赖与非PyPI技术组件（完整更新版）

### ========== 推理服务引擎（支持多模型路由） ==========

- **NVIDIA Triton** - 从NVIDIA官网下载服务器镜像或使用Docker容器
  - 用途：生产级模型服务，支持多模型并发
  - 安装方式：`docker pull nvcr.io/nvidia/tritonserver:24.02-py3`
- **TensorFlow Serving** - 通过Docker镜像(tensorflow/serving)安装
  - 用途：TensorFlow模型服务
- **TorchServe** - 通过PyTorch官方Docker镜像安装
  - 用途：PyTorch模型服务
- **vLLM** - 通过pip安装（已在Python依赖中），建议编译安装获得最佳性能
  - 编译依赖：`sudo apt-get install build-essential cmake`
- **llama.cpp** - 通过pip安装，或从源码编译
  - 编译优化：`CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python`

### ========== 语音处理技术栈 ==========

- **Microsoft Speech API** - 集成在Windows系统中
- **eSpeak NG** - `sudo apt-get install espeak-ng`
- **Festival** - `sudo apt-get install festival`
- **WeNet** - 从GitHub源码编译安装

### ========== 计算机视觉技术栈（新增情绪识别支持） ==========

- **Dlib** - `sudo apt-get install cmake build-essential`
- **Face Recognition** - 依赖dlib
- **OpenCV** - `sudo apt-get install libopencv-dev`
- **CUDA视觉库** - `sudo apt-get install libnvcuvid1 libnvidia-encode1`

### ========== 3D渲染与图形技术栈（新增自定义形象支持） ==========

- **Unity** - 从Unity官网下载Unity Hub
- **Vulkan** - 从Vulkan官网下载SDK
- **FBX SDK** - 从Autodesk开发者官网下载
- **Bullet Physics** - `sudo apt-get install libbullet-dev`
- **Three.js** - `npm install three`
- **Assimp** - `sudo apt-get install libassimp-dev`（3D模型导入）
- **OpenGL** - `sudo apt-get install libgl1-mesa-dev libglu1-mesa-dev`

### ========== 数据库与存储技术栈（新增知识图谱） ==========

- **Neo4j**（核心新增）
  - 从Neo4j官网下载桌面版或服务器版：https://neo4j.com/download/
  - 或使用Docker：`docker run -p 7687:7687 -p 7474:7474 neo4j:5-enterprise`
  - 系统依赖：`sudo apt-get install openjdk-17-jdk`
- **Apache Age** - 从GitHub源码编译（PostgreSQL图扩展）
- **TimescaleDB** - 通过Docker安装：`docker pull timescale/timescaledb:latest-pg15`
- **Prometheus** - 下载预编译二进制文件
- **Memcached** - `sudo apt-get install memcached`
- **MySQL/PostgreSQL** - `sudo apt-get install mysql-server postgresql`

### ========== 后端与API技术栈 ==========

- **Nginx** - `sudo apt-get install nginx`
- **Traefik** - 通过Docker镜像
- **Kong** - 通过Docker镜像
- **RabbitMQ** - `sudo apt-get install rabbitmq-server`
- **ZeroMQ** - `sudo apt-get install libzmq3-dev`
- **Redis** - `sudo apt-get install redis-server`

### ========== 前端与客户端技术栈（新增捏人系统支持） ==========

- **Electron** - `npm install -g electron`
- **Qt** - 从Qt官网下载安装器
- **Tauri** - 需要Rust工具链：`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- **React Native** - `npm install -g react-native-cli`
- **Flutter** - 从Flutter官网下载SDK
- **Android SDK** - 安装Android Studio
- **Xcode** - 从Mac App Store安装（仅macOS）
- **Three.js** - `npm install three`（Web 3D渲染）

### ========== 开发工具与基础设施（新增模型训练环境） ==========

- **CUDA 12.0+** - 从NVIDIA官网下载
- **cuDNN 8.0+** - 从NVIDIA开发者网站下载
- **NVIDIA Drivers** - `sudo apt-get install nvidia-driver-545`
- **FFmpeg** - `sudo apt-get install ffmpeg`
- **OpenCL** - `sudo apt-get install ocl-icd-opencl-dev`
- **Git LFS** - `sudo apt-get install git-lfs`（用于下载大模型）
- **Docker** - `sudo apt-get install docker.io`
- **Kubernetes** - `sudo snap install kubectl --classic`
- **Grafana** - 通过Docker或`sudo apt-get install grafana`
- **ELK Stack** - 通过Docker或手动安装
- **Jaeger** - 通过Docker：`docker run -d --name jaeger -p 16686:16686 jaegertracing/all-in-one:1.45`

### ========== 安全与加密技术栈（新增事件响应） ==========

- **OpenSSL** - `sudo apt-get install openssl libssl-dev`
- **libsodium** - `sudo apt-get install libsodium-dev`
- **age** - 从GitHub下载预编译二进制
- **Trivy** - `sudo apt-get install trivy` 或从GitHub下载
- **ClamAV** - `sudo apt-get install clamav clamav-daemon`
- **Fail2ban** - `sudo apt-get install fail2ban`（入侵防护）
- **Auditd** - `sudo apt-get install auditd`（系统审计日志）

### ========== 特殊AI模型清单（完整组合模型方案） ==========

以下模型需要从Hugging Face Hub、ModelScope、官方仓库下载模型权重文件（GGUF 量化版优先）
这些模型通过 infrastructure/model_hub/model_manager.py 智能路由动态加载
**不需要全部打包进安装包**，初始包只含 8B/32B 轻量模型，其他按需下载

#### 🗣️ 日常聊天/情感陪伴（默认主力）
- **Llama 3.1 70B Q4_K_M** - Meta官方 / Hugging Face
- **Qwen 3.5 32B Q5_K_M** - 阿里通义千问 / ModelScope

#### 💻 编程/复杂推理（高配切换）
- **DeepSeek V3 Q4_K_M** - DeepSeek官方 / Hugging Face
- **Qwen3-Coder-32B Q5** - 阿里通义千问 / ModelScope

#### 📚 长上下文（>128K）（复杂分析时切换）
- **Llama 4 Maverick 128K** - Meta官方 / Hugging Face
- **Qwen3-Next** - 阿里通义千问 / ModelScope

#### 🖼️ 多模态（图文/视频理解）（图像/视频任务切换）
- **Llama 4 Scout** - Meta官方 / Hugging Face
- **Qwen3-Omni** - 阿里通义千问 / ModelScope

#### 🧠 情绪识别神经网络（本地训练/微调）
- **自定义LSTM模型** - 用用户数据训练，位置：`models/emotion/`
- **Sentence-BERT** - 用于文本嵌入（已在Python依赖中）

#### 🔍 实时知识更新（RAG + 工具链）
- **搜索引擎API**（可选）：Google Custom Search、Bing Search API
- **RSS订阅源**：根据用户兴趣配置

#### 🗺️ 知识图谱
- **Neo4j数据库**：存储实体关系
- **网络爬虫**：用于主动知识摄取

#### 🔐 安全模型
- **敏感词分类器**：本地训练的小型BERT模型
- **异常行为检测模型**：Isolation Forest / One-Class SVM

#### 📦 原有模型（保持兼容）
- **GPT-4/Claude 3** - 通过API调用（可选云端增强）
- **LLaMA 3 70B** - Meta官方
- **Qwen 72B** - 阿里通义千问
- **Mixtral 8x7B** - Mistral AI
- **Code Llama** - Meta官方
- **Stable Diffusion** - Stability AI
- **MusicGen** - Meta官方
- **Whisper Large** - OpenAI
- **DistilBERT** - Hugging Face
- **MobileNet** - TensorFlow Hub
- **DeepSpeech** - Mozilla

---

## 📦 安装说明（完整版）

### Python依赖安装
```bash
pip install -r requirements.txt --upgrade
系统级依赖安装 (Ubuntu/Debian)
bash
# 基础开发工具
sudo apt-get update
sudo apt-get install -y build-essential cmake git-lfs

# 语音处理
sudo apt-get install -y espeak-ng festival ffmpeg

# 计算机视觉
sudo apt-get install -y libopencv-dev libdlib-dev libavcodec-dev

# 3D图形
sudo apt-get install -y libgl1-mesa-dev libglu1-mesa-dev libassimp-dev libbullet-dev

# 数据库
sudo apt-get install -y neo4j redis-server memcached postgresql mysql-server

# 消息队列
sudo apt-get install -y rabbitmq-server libzmq3-dev

# 安全
sudo apt-get install -y clamav clamav-daemon fail2ban auditd libsodium-dev

# 监控
sudo apt-get install -y prometheus grafana
Docker组件安装
bash
# Neo4j（知识图谱）
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/mirexs neo4j:5-enterprise

# Jaeger（链路追踪）
docker run -d --name jaeger -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:1.45

# Prometheus + Grafana（监控）
docker run -d --name prometheus -p 9090:9090 prom/prometheus
docker run -d --name grafana -p 3000:3000 grafana/grafana
AI模型下载
bash
# 安装 Hugging Face CLI
pip install huggingface-hub

# 下载默认模型（8B/32B）
huggingface-cli download TheBloke/Llama-3.1-8B-GGUF llama-3.1-8b-q4_k_m.gguf --local-dir models/gguf/
huggingface-cli download Qwen/Qwen3.5-32B-GGUF qwen3.5-32b-q5_k_m.gguf --local-dir models/gguf/

# 情绪识别模型（需训练）
# 位置：models/emotion/emotion_model.pth