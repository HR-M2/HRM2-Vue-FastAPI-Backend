# HRM2-Vue-FastAPI-Backend

企业招聘管理系统（HRM2）的 FastAPI 后端服务。

## 📐 数据模型

```
Position (岗位)
    |
    | 1:N
    v
Application (应聘申请) <-- 核心表
    |
    | N:1
    |
Resume (简历)

Application (应聘申请)
    |
    +-- 1:N --> ScreeningTask (筛选任务)
    |
    +-- 1:N --> VideoAnalysis (视频分析)
    |
    +-- 1:N --> InterviewSession (面试会话)
    |
    +-- 1:N --> ComprehensiveAnalysis (综合分析)
```

## 🛠️ 技术栈

| 层级 | 技术 |
| ---- | ---- |
| 框架 | FastAPI 0.115+ |
| ORM | SQLAlchemy 2.0 (异步) |
| 数据库 | SQLite (开发) / PostgreSQL (生产) |
| 验证 | Pydantic 2.0 |
| 迁移 | Alembic |

## 📁 项目结构

```
HRM2-Vue-FastAPI-Backend/
├── app/
│   ├── api/                 # API 路由
│   │   └── v1/
│   │       ├── positions.py    # 岗位管理
│   │       ├── resumes.py      # 简历管理
│   │       ├── applications.py # 应聘申请
│   │       ├── screening.py    # 简历筛选
│   │       ├── video.py        # 视频分析
│   │       ├── interview.py    # 面试辅助
│   │       └── analysis.py     # 综合分析
│   ├── core/                # 核心配置
│   │   ├── config.py           # 配置管理
│   │   ├── database.py         # 数据库配置
│   │   ├── response.py         # 统一响应
│   │   └── exceptions.py       # 异常处理
│   ├── models/              # 数据库模型
│   ├── schemas/             # Pydantic Schema
│   ├── crud/                # CRUD 操作
│   └── main.py              # 应用入口
├── data/                    # 数据库文件
├── .env.example             # 环境变量模板
├── requirements.txt         # 依赖
├── run.py                   # 启动脚本
└── README.md
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境

```bash
copy .env.example .env
# 编辑 .env 文件，配置数据库和 LLM 等
```

### 3. 启动服务

```bash
# 方式一：使用启动脚本
python run.py

# 方式二：直接使用 uvicorn
uvicorn app.main:app --reload
```

### 4. 访问文档

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## 📡 API 端点

### 岗位管理 `/api/v1/positions`

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| GET | `/` | 岗位列表 |
| POST | `/` | 创建岗位 |
| GET | `/{id}` | 岗位详情 |
| PATCH | `/{id}` | 更新岗位 |
| DELETE | `/{id}` | 删除岗位 |

### 简历管理 `/api/v1/resumes`

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| GET | `/` | 简历列表 |
| POST | `/` | 创建简历 |
| GET | `/check-hash` | 检查文件哈希(去重) |
| GET | `/{id}` | 简历详情 |
| PATCH | `/{id}` | 更新简历 |
| DELETE | `/{id}` | 删除简历 |

### 应聘申请 `/api/v1/applications`

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| GET | `/` | 申请列表 |
| POST | `/` | 创建申请(投递) |
| GET | `/{id}` | 申请详情(含关联数据) |
| PATCH | `/{id}` | 更新状态 |
| DELETE | `/{id}` | 删除申请 |
| GET | `/stats/overview` | 状态统计 |

### 简历筛选 `/api/v1/screening`

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| GET | `/` | 任务列表 |
| POST | `/` | 创建筛选任务 |
| GET | `/{id}` | 任务详情 |
| GET | `/{id}/status` | 任务状态(轮询) |
| PATCH | `/{id}` | 更新结果 |
| DELETE | `/{id}` | 删除任务 |

### 视频分析 `/api/v1/video`

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| GET | `/` | 分析列表 |
| POST | `/` | 创建分析任务 |
| GET | `/{id}` | 分析详情 |
| GET | `/{id}/status` | 分析状态 |
| PATCH | `/{id}` | 更新结果 |
| DELETE | `/{id}` | 删除分析 |

### 面试辅助 `/api/v1/interview`

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| GET | `/` | 会话列表 |
| POST | `/` | 创建会话 |
| GET | `/{id}` | 会话详情 |
| POST | `/{id}/questions` | 生成问题 |
| POST | `/{id}/qa` | 记录问答 |
| POST | `/{id}/complete` | 完成会话 |
| DELETE | `/{id}` | 删除会话 |

### 综合分析 `/api/v1/analysis`

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| GET | `/` | 分析列表 |
| POST | `/` | 创建分析 |
| GET | `/{id}` | 分析详情 |
| DELETE | `/{id}` | 删除分析 |
| GET | `/stats/recommendation` | 推荐统计 |

## 📝 统一响应格式

```json
{
    "success": true,
    "code": 200,
    "message": "操作成功",
    "data": { ... }
}
```

分页响应:

```json
{
    "success": true,
    "code": 200,
    "message": "查询成功",
    "data": {
        "items": [...],
        "total": 100,
        "page": 1,
        "page_size": 20,
        "pages": 5
    }
}
```

## 🔧 环境变量

| 变量 | 说明 | 默认值 |
| ---- | ---- | ---- |
| APP_NAME | 应用名称 | HRM2-API |
| APP_ENV | 环境 | development |
| DEBUG | 调试模式 | true |
| DATABASE_URL | 数据库连接 | sqlite+aiosqlite:///./data/hrm2.db |
| CORS_ORIGINS | CORS 来源 | ["http://localhost:5173"] |
| LLM_MODEL | LLM 模型 | deepseek-chat |
| LLM_API_KEY | LLM API Key | - |
| LLM_BASE_URL | LLM API URL | https://api.deepseek.com |

## 📄 License

MIT License
