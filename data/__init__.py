"""
数据持久层 - 管理所有数据存储，包括模型、数据库、用户数据、系统日志等

核心模块:
- models: AI模型存储与管理
- databases: 数据库系统
- user_data: 用户数据管理  
- system: 系统数据管理
"""

__version__ = "1.0.0"
__all__ = ["initialize_data_layer"]

# 数据层初始化
def initialize_data_layer():
    """初始化数据持久层所有组件"""
    # 说明：为避免包导入时的副作用（重模型加载/可选依赖缺失），
    # 数据层不在 __init__ 阶段自动导入所有子模块。
    from .databases.vector_db import VectorDatabase  # 轻量导入

    # 重模型/可选依赖在需要时再初始化（保持可运行性与可扩展性）
    vector_db = VectorDatabase()

    print("✅ 数据持久层初始化完成")

    return {
        "vector_db": vector_db,
    }
