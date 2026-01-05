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
    v
Resume (简历)

Application (应聘申请)
    |
    +-- 1:1 --> ScreeningTask (筛选任务)
    |
    +-- 1:1 --> VideoAnalysis (视频分析)
    |
    +-- 1:1 --> InterviewSession (面试会话)
    |
    +-- 1:1 --> ComprehensiveAnalysis (综合分析)
```

## 🛠️ 技术栈

| 层级 | 技术 |
| ---- | ---- |
| 框架 | FastAPI 0.119+ |
| ORM + Schema | SQLModel 0.0.27+（统一 SQLAlchemy 2.0 异步 + Pydantic） |
| 数据库 | SQLite (开发) / PostgreSQL (生产) |
| AI 服务 | PyAutoGen 0.10+ / OpenAI SDK 2.5+ |

## 📁 项目结构

```
HRM2-Vue-FastAPI-Backend/
├── app/
│   ├── api/v1/              # API 路由
│   │   ├── positions.py        # 岗位管理
│   │   ├── resumes.py          # 简历管理
│   │   ├── applications.py     # 应聘申请
│   │   ├── screening.py        # 简历筛选
│   │   ├── video.py            # 视频分析
│   │   ├── interview.py        # 面试辅助
│   │   ├── analysis.py         # 综合分析
│   │   └── ai_services.py      # AI 服务接口
│   ├── agents/              # AI Agent 服务
│   │   ├── prompts/            # Prompt 配置 (YAML)
│   │   │   ├── screening.yaml     # 筛选流程 prompts
│   │   │   ├── interview.yaml     # 面试流程 prompts
│   │   │   ├── analysis.yaml      # 分析流程 prompts
│   │   │   └── ...
│   │   ├── base.py             # Agent 基类
│   │   ├── llm_client.py       # LLM 客户端
│   │   ├── screening.py        # 简历筛选 Agent
│   │   ├── interview.py        # 面试辅助 Agent
│   │   ├── analysis.py         # 综合分析 Agent
│   │   ├── position.py         # 岗位分析 Agent
│   │   └── dev_tools.py        # 开发工具服务
│   ├── core/                # 核心模块
│   │   ├── config.py           # 配置管理
│   │   ├── database.py         # 数据库配置
│   │   ├── response.py         # 统一响应
│   │   ├── exceptions.py       # 异常处理
│   │   └── progress_cache.py   # 任务进度缓存
│   ├── models/              # SQLModel 模型（Table + Schema 统一）
│   ├── crud/                # CRUD 操作
│   └── main.py              # 应用入口
├── Docs/                    # 开发文档
├── data/                    # SQLite 数据库文件
├── tests/                   # 测试用例
├── .env.example             # 环境变量模板
├── requirements.txt         # Python 依赖
└── run.py                   # 启动脚本
```

> 💡 **注意**: 本项目使用 **SQLModel** 统一了 ORM Model 和 Pydantic Schema，不再有独立的 `schemas/` 目录。详见 [后端开发规范](./Docs/后端开发规范.md)。

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
# 编辑 .env 文件，配置 LLM API Key 等
```

### 3. 启动服务

```bash
# 方式一：使用启动脚本
python run.py

# 方式二：直接使用 uvicorn
uvicorn app.main:app --reload
```

服务默认运行在 `http://127.0.0.1:8000`

## 📡 API 文档

启动服务后，访问交互式 API 文档查看所有端点详情：

| 文档类型 | 地址 | 说明 |
| -------- | ---- | ---- |
| **Swagger UI** | http://127.0.0.1:8000/docs | 交互式文档，可直接测试 API |
| **ReDoc** | http://127.0.0.1:8000/redoc | 美观的只读文档 |
| **OpenAPI JSON** | http://127.0.0.1:8000/openapi.json | OpenAPI 3.0 规范 |

> 💡 **提示**: Swagger UI 支持在线调试，可直接在浏览器中测试所有 API 端点。

### API 模块概览

| 模块 | 路径前缀 | 功能 |
| ---- | -------- | ---- |
| 岗位管理 | `/api/v1/positions` | 招聘岗位的增删改查 |
| 简历管理 | `/api/v1/resumes` | 候选人简历管理 |
| 应聘申请 | `/api/v1/applications` | 简历投递与状态流转 |
| 简历筛选 | `/api/v1/screening` | AI 简历智能筛选 |
| 视频分析 | `/api/v1/video` | 视频面试分析 |
| 面试辅助 | `/api/v1/interview` | AI 面试问题生成与记录 |
| 综合分析 | `/api/v1/analysis` | 候选人综合评估 |
| AI 服务 | `/api/v1/ai` | AI 能力调用接口 |

## 🔧 环境变量

参考 `.env.example` 文件：

```bash
# 应用配置
APP_NAME=HRM2-API
APP_ENV=development
DEBUG=true

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./data/hrm2.db

# CORS
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]

# LLM 配置 (必填)
LLM_MODEL=deepseek-ai/DeepSeek-V3
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_TEMPERATURE=0.7
LLM_TIMEOUT=120
LLM_MAX_CONCURRENCY=2
LLM_RATE_LIMIT=60

# Embedding 配置 (可选)
EMBEDDING_MODEL=
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=
```

## 📝 统一响应格式

所有 API 响应均遵循统一格式：

```json
{
    "success": true,
    "code": 200,
    "message": "操作成功",
    "data": { ... }
}
```

## 📚 开发文档

- [后端开发规范](./Docs/后端开发规范.md) - 代码风格、架构规范、SQLModel 使用指南

## 📄 License

MIT License
