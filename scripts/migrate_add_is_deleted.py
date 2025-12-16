"""
数据库迁移脚本：为 applications 表添加 is_deleted 字段

用法：
    python scripts/migrate_add_is_deleted.py
"""
import sqlite3
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "hrm2.db"


def check_column_exists(cursor, table: str, column: str) -> bool:
    """检查列是否已存在"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migrate():
    """执行迁移"""
    if not DB_PATH.exists():
        print(f"错误：数据库文件不存在: {DB_PATH}")
        return False
    
    print(f"数据库路径: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查 applications 表是否存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='applications'"
        )
        if not cursor.fetchone():
            print("错误：applications 表不存在")
            return False
        
        # 检查 is_deleted 列是否已存在
        if check_column_exists(cursor, "applications", "is_deleted"):
            print("is_deleted 列已存在，无需迁移")
            return True
        
        # 添加 is_deleted 列
        print("正在添加 is_deleted 列...")
        cursor.execute(
            "ALTER TABLE applications ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0"
        )
        
        # 创建索引
        print("正在创建索引...")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_applications_is_deleted ON applications(is_deleted)"
        )
        
        conn.commit()
        print("迁移成功完成！")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}")
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
