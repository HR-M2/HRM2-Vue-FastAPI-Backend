# SQLModel 迁移指南

## 概述

本次重构将项目从传统的 SQLAlchemy + Pydantic 分离架构迁移到 SQLModel 统一架构。

## 迁移状态

✅ **迁移已完成** (2026-01-03)

## 文件结构对比

### 迁移前
```
app/
├── models/          # SQLAlchemy ORM 模型
├── schemas/         # Pydantic Schema
├── crud/            # CRUD 操作（含大量薄包装）
└── core/database.py
```

### 迁移后
```
app/
├── models/              # SQLModel 统一模型（Model + Schema）
├── crud/                # 精简的 CRUD（只保留业务查询）
├── models_backup/       # 旧版 SQLAlchemy 模型（备份）
├── schemas_backup/      # 旧版 Pydantic Schema（备份）
├── crud_backup/         # 旧版 CRUD（备份）
└── core/
    ├── database.py          # SQLModel 数据库配置
    └── database_backup.py   # 旧版数据库配置（备份）
```

## 代码量对比

| 实体 | 迁移前（行数） | 迁移后（行数） | 减少 |
|------|---------------|---------------|------|
| Position | ~180 (model+schema+crud) | ~100 | 44% |
| Resume | ~170 | ~95 | 44% |
| Application | ~200 | ~130 | 35% |
| 总计 | ~1000+ | ~600 | ~40% |

## 主要变化

### 1. 模型定义
- Model 和 Schema 合并为单个 SQLModel 类
- 使用 `table=True` 区分表模型和纯 Schema
- 外键使用 `sa_column` 定义以支持 `ondelete`

### 2. CRUD 操作
- 移除薄包装方法，直接使用基类方法
- `selectinload` 使用类属性而非字符串

### 3. 导入路径
```python
# 迁移前
from app.models.position import Position
from app.schemas.position import PositionCreate, PositionResponse
from app.crud import position_crud

# 迁移后
from app.models import Position, PositionCreate, PositionResponse
from app.crud import position_crud
```

## 回滚方案

如果需要回滚：
1. 将 `*_backup` 目录重命名回原名
2. 删除当前的 `models/`, `crud/`, `core/database.py`
3. 将 `database_backup.py` 重命名为 `database.py`

## 清理备份

确认迁移成功后，可以删除备份目录：
```bash
rm -rf app/models_backup app/schemas_backup app/crud_backup
rm app/core/database_backup.py
```

## 注意事项

### JSON 字段
SQLModel 需要显式指定 `sa_column=Column(JSON)`：
```python
required_skills: List[str] = Field(
    default_factory=list,
    sa_column=Column(JSON),
    description="必备技能"
)
```

### 外键定义
使用 `sa_column` 定义外键以支持 `ondelete`：
```python
position_id: str = Field(
    sa_column=Column(String, ForeignKey("positions.id", ondelete="CASCADE"), index=True, nullable=False),
    description="岗位ID"
)
```

### Relationship
SQLModel 的 Relationship 配置：
```python
applications: List["Application"] = Relationship(
    back_populates="position",
    sa_relationship_kwargs={"lazy": "selectin"}
)
```

### selectinload
使用类属性而非字符串：
```python
# 正确
selectinload(self.model.application).selectinload(Application.position)

# 错误
selectinload(self.model.application).selectinload("position")
```
