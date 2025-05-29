"""
测试脚本，用于验证应用和GridFS配置正常工作
"""

import os
import sys
from flask import Flask
from pathlib import Path

# 添加项目目录到Python路径
project_dir = Path(__file__).resolve().parent
sys.path.append(str(project_dir))

# 导入应用
from app import app
from utils.db import init_mongodb_connection, get_db
from utils.gridfs_utils import init_gridfs_storage, fs

def test_app():
    """测试应用和GridFS配置"""
    print("测试应用启动...")
    
    with app.app_context():
        # 测试MongoDB连接
        print("初始化MongoDB连接...")
        db_init_success = init_mongodb_connection()
        print(f"MongoDB连接状态: {'已连接' if get_db() is not None else '未连接'}")
        
        # 测试GridFS初始化
        print("初始化GridFS存储...")
        gridfs_init_success = init_gridfs_storage()
        print(f"GridFS初始化状态: {'成功' if gridfs_init_success else '失败'}")
        print(f"GridFS对象状态: {'可用' if fs is not None else '不可用'}")
        
    print("测试完成!")

if __name__ == "__main__":
    test_app()
