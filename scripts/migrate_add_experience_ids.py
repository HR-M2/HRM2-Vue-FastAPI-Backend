# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加 applied_experience_ids 字段

为 screening_tasks 和 interview_sessions 表添加 applied_experience_ids 字段，
用于记录 RAG 经验引用。

使用方法：
    python scripts/migrate_add_experience_ids.py
"""
import sqlite3
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def migrate():
    """执行迁移"""
    # 数据库路径
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "hrm2.db"
    )
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        print("如果是首次运行，启动应用后会自动创建表结构，无需迁移。")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查并添加 screening_tasks.applied_experience_ids
        cursor.execute("PRAGMA table_info(screening_tasks)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "applied_experience_ids" not in columns:
            print("为 screening_tasks 表添加 applied_experience_ids 字段...")
            cursor.execute(
                "ALTER TABLE screening_tasks ADD COLUMN applied_experience_ids TEXT"
            )
            print("✓ screening_tasks.applied_experience_ids 添加成功")
        else:
            print("✓ screening_tasks.applied_experience_ids 已存在，跳过")
        
        # 检查并添加 interview_sessions.applied_experience_ids
        cursor.execute("PRAGMA table_info(interview_sessions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "applied_experience_ids" not in columns:
            print("为 interview_sessions 表添加 applied_experience_ids 字段...")
            cursor.execute(
                "ALTER TABLE interview_sessions ADD COLUMN applied_experience_ids TEXT"
            )
            print("✓ interview_sessions.applied_experience_ids 添加成功")
        else:
            print("✓ interview_sessions.applied_experience_ids 已存在，跳过")
        
        conn.commit()
        print("\n迁移完成！")
        
    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
