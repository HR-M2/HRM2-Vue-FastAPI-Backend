# HRM2 后端开发规范（AI读）

> 精简版规范，供 AI 编程助手快速参考。详细说明见 `后端开发规范（人读）.md`

---

## 技术栈

- FastAPI 0.119+ / SQLModel 0.0.27+ / PyAutoGen 0.10+
- 异步数据库：AsyncSession + aiosqlite

## 分层架构

```
API 层 (app/api/v1/)     → 路由、参数校验、调用 CRUD
CRUD 层 (app/crud/)      → 数据库操作，继承 CRUDBase
Models 层 (app/models/)  → SQLModel 统一定义 Table + Schema
Services 层 (app/services/agents/) → AI Agent 业务逻辑
Core 层 (app/core/)      → 配置、数据库、响应、异常
```

**禁止**：
- API 层写业务逻辑
- CRUD 层之间相互调用
- 直接修改 Core 层基础设施

## 命名规范

| 类型 | 风格 | 示例 |
|------|------|------|
| 变量/函数 | snake_case | `candidate_name`, `get_by_id()` |
| 类 | PascalCase | `PositionCreate`, `CRUDBase` |
| 常量 | UPPER_SNAKE_CASE | `TOTAL_AGENTS` |

## SQLModel 定义模式

每个模块文件结构：`{Module}Base` → `{Module}(table=True)` → `{Module}Create` → `{Module}Update` → `{Module}Response`

```python
class PositionBase(SQLModelBase):        # 基础字段
class Position(PositionBase, TimestampMixin, IDMixin, table=True):  # 表模型
class PositionCreate(PositionBase):      # 创建请求
class PositionUpdate(SQLModelBase):      # 更新请求（字段可选）
class PositionResponse(TimestampResponse):  # 响应
```

## CRUD 规范

- 继承 `CRUDBase[Model]`，只添加业务特定查询
- 创建单例：`position_crud = CRUDPosition(Position)`
- 使用基类方法：`get`, `get_multi`, `count`, `create`, `update`, `delete`

## API 路由规范

- 路由命名：`GET ""` 列表，`POST ""` 创建，`GET "/{id}"` 详情，`PATCH "/{id}"` 更新，`DELETE "/{id}"` 删除
- 响应包装：`success_response()`, `paged_response()`, `error_response()`
- 异常：`NotFoundException(404)`, `BadRequestException(400)`, `ConflictException(409)`

```python
@router.get("", response_model=PagedResponseModel[ItemListResponse])
async def get_items(page: int = Query(1, ge=1), db: AsyncSession = Depends(get_db)):
    items = await item_crud.get_multi(db, skip=(page-1)*page_size, limit=page_size)
    return paged_response([...], total, page, page_size)
```

## Agent 开发规范

- 继承 `BaseAgentManager`
- Prompt 定义为模块常量，使用 `.format()` 填充
- 实现 `setup()` 和 `run_{function}()` 方法

## 类型注解

**必须**：所有函数有完整的入参和返回值类型注解

```python
async def get(self, db: AsyncSession, id: str) -> Optional[Position]:
```

## 新模块开发流程

1. `app/models/{module}.py` - 创建 SQLModel 定义
2. `app/crud/{module}.py` - 创建 CRUD 类和单例
3. `app/api/v1/{modules}.py` - 创建 API 路由
4. 在各 `__init__.py` 中注册导出
