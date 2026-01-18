# 沉浸式面试 API 文档

## 概述

沉浸式面试模块提供双摄像头面试、说话人识别、实时心理分析等功能。

**基础路径**: `/api/v1/immersive`

**核心特性**:
- 🎥 双摄像头支持（本地 + 远程推流）
- 🎤 实时语音转录和说话人识别
- 🧠 三项心理评分：大五人格、欺骗检测、抑郁风险
- 📊 面试完成后返回完整会话历史和统计数据

## 数据模型

### 候选人心理评分 (CandidateScores)

每次 sync 都会携带候选人的三项心理评分（不管当前发言人是谁）：

```json
{
  "big_five": {
    "openness": 0.75,
    "conscientiousness": 0.82,
    "extraversion": 0.68,
    "agreeableness": 0.71,
    "neuroticism": 0.35
  },
  "deception": {
    "score": 0.15,
    "confidence": 0.85
  },
  "depression": {
    "score": 22.1,
    "level": "low",
    "confidence": 0.88
  }
}
```

| 字段 | 说明 |
|-----|------|
| `big_five` | 大五人格分析（各维度 0-1） |
| `deception` | 欺骗检测（score: 0-1，越高越可能欺骗） |
| `depression` | 抑郁风险（score: 0-100，level: low/medium/high）|

## API 接口

### 1. 核心 CRUD 操作

#### 1.1 获取会话列表
```http
GET /api/v1/immersive
```

**查询参数**:
- `page` (int): 页码，默认 1
- `page_size` (int): 每页数量，默认 20，最大 100
- `application_id` (string, 可选): 应聘申请ID筛选
- `is_recording` (boolean, 可选): 录制状态筛选
- `is_completed` (boolean, 可选): 完成状态筛选

**响应示例**:
```json
{
  "success": true,
  "code": 200,
  "message": "查询成功",
  "data": {
    "items": [...],
    "total": 10,
    "page": 1,
    "page_size": 20,
    "pages": 1
  }
}
```

#### 1.2 创建会话
```http
POST /api/v1/immersive
```

**请求体**:
```json
{
  "application_id": "app_123",
  "local_camera_enabled": true,
  "stream_url": "rtmp://example.com/live/stream1",
  "config": {
    "video_quality": "HD",
    "audio_sample_rate": 44100
  }
}
```

**响应**: 返回创建的会话信息

#### 1.3 获取会话详情
```http
GET /api/v1/immersive/{session_id}
```

**特殊行为**:
- 如果会话未完成：返回基础信息和实时数据
- 如果会话已完成：返回完整数据汇总（包含统计分析和心理评估）

#### 1.4 删除会话
```http
DELETE /api/v1/immersive/{session_id}
```

### 2. 会话控制

#### 2.1 开始录制
```http
POST /api/v1/immersive/{session_id}/start
```

**响应示例**:
```json
{
  "success": true,
  "message": "面试录制已开始",
  "data": {
    "session_id": "session_123",
    "status": "recording",
    "start_time": "2024-01-01T10:00:00Z"
  }
}
```

#### 2.2 停止录制
```http
POST /api/v1/immersive/{session_id}/stop
```

**响应示例**:
```json
{
  "success": true,
  "message": "面试录制已停止",
  "data": {
    "session_id": "session_123",
    "status": "stopped",
    "duration_seconds": 1800,
    "end_time": "2024-01-01T10:30:00Z"
  }
}
```

#### 2.3 完成会话 ⭐
```http
POST /api/v1/immersive/{session_id}/complete
```

**重要**: 此接口会返回简化的面试数据汇总，包括：
- **统计数据**：发言数、发言占比、总体抑郁水平
- **会话历史**：每条记录捆绑三项心理评分（大五人格、欺骗检测、抑郁值）
- **候选人信息**

数据会自动保存到 `final_analysis` 字段供后续推荐使用。

**响应示例**:
```json
{
  "success": true,
  "message": "沉浸式面试会话已完成",
  "data": {
    "session_id": "session_123",
    "duration_seconds": 1800,
    "start_time": "2024-01-01T10:00:00",
    "end_time": "2024-01-01T10:30:00",
    
    "statistics": {
      "total_utterances": 50,
      "interviewer_utterances": 20,
      "candidate_utterances": 30,
      "interviewer_ratio": 0.4,
      "candidate_ratio": 0.6,
      "overall_depression": {
        "avg_score": 18.5,
        "final_level": "low"
      }
    },
    
    "conversation_history": [
      {
        "speaker": "interviewer",
        "text": "请介绍一下你自己",
        "timestamp": "2024-01-01T10:00:05",
        "candidate_scores": {
          "big_five": {
            "openness": 0.75,
            "conscientiousness": 0.82,
            "extraversion": 0.68,
            "agreeableness": 0.71,
            "neuroticism": 0.35
          },
          "deception": {
            "score": 0.12,
            "confidence": 0.88
          },
          "depression": {
            "score": 18.5,
            "level": "low",
            "confidence": 0.85
          }
        }
      },
      {
        "speaker": "candidate",
        "text": "我是一名软件工程师，有5年经验...",
        "timestamp": "2024-01-01T10:00:15",
        "candidate_scores": {...}
      }
    ],
    
    "candidate_info": {
      "name": "张三",
      "position_title": "高级软件工程师"
    }
  }
}
```

### 3. 实时数据同步

#### 3.1 同步发言数据 ⭐
```http
POST /api/v1/immersive/{session_id}/sync
```

**简化的请求结构**：每次同步发送一个或多个发言记录，每条记录都带上候选人的三项心理评分。

**请求体**:
```json
{
  "utterances": [
    {
      "speaker": "interviewer",
      "text": "请介绍一下你自己",
      "timestamp": 1768720937024,
      "candidate_scores": {
        "big_five": {
          "openness": 0.75,
          "conscientiousness": 0.82,
          "extraversion": 0.68,
          "agreeableness": 0.71,
          "neuroticism": 0.35
        },
        "deception": {
          "score": 0.15,
          "confidence": 0.85
        },
        "depression": {
          "score": 22.1,
          "level": "low",
          "confidence": 0.88
        }
      }
    },
    {
      "speaker": "candidate",
      "text": "我是一名软件工程师，有5年经验...",
      "timestamp": 1768720950123,
      "candidate_scores": {
        "big_five": {...},
        "deception": {...},
        "depression": {...}
      }
    }
  ]
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|-----|------|------|
| `speaker` | string | 发言人：`interviewer` 或 `candidate` |
| `text` | string | 发言内容 |
| `timestamp` | number | 毫秒时间戳（后端自动转秒存储） |
| `candidate_scores` | object | 候选人三项心理评分（不管 speaker 是谁都要带） |

**响应示例**:
```json
{
  "success": true,
  "message": "实时数据同步成功",
  "data": {
    "session_id": "session_123",
    "synced_count": 2,
    "total_utterances": 15
  }
}
```

#### 3.2 旧版同步接口（兼容）
```http
POST /api/v1/immersive/{session_id}/sync-legacy
```

保留旧版接口以兼容现有前端，支持 `transcripts`、`speaker_segments`、`state_records` 分开传输。

### 4. 智能问题建议 ⭐

#### 4.1 生成问题建议
```http
POST /api/v1/immersive/{session_id}/questions
```

**特色功能**: 基于心理状态和对话历史的智能问题建议（已集成真实AI服务）

**AI集成状态**: ✅ 已完成
- 使用项目统一的LLM客户端
- 支持AI服务失败时的备用方案
- 基于心理状态和对话历史的智能分析

**请求体**:
```json
{
  "count": 5,
  "difficulty": "medium",
  "focus_areas": ["技术能力", "团队协作"],
  "use_psychological_context": true,
  "use_conversation_history": true,
  "question_type": "mixed"
}
```

**参数说明**:
- `count`: 生成问题数量 (1-20)
- `difficulty`: 问题难度 (easy/medium/hard)
- `focus_areas`: 关注领域 (可选)
- `use_psychological_context`: 是否使用心理分析上下文
- `use_conversation_history`: 是否使用对话历史
- `question_type`: 问题类型 (technical/behavioral/situational/mixed)

**响应示例**:
```json
{
  "success": true,
  "message": "问题建议生成成功",
  "data": {
    "suggestions": [
      {
        "question": "我注意到你现在看起来很自信，能详细说说你刚才提到的技术实现吗？",
        "type": "technical",
        "priority": 5,
        "reason": "基于候选人当前自信状态，适合深入技术问题",
        "psychological_context": "当前情绪: confident, 参与度: 0.85, 紧张程度: 0.20, 自信程度: 0.80",
        "timing_suggestion": "适合在当前话题结束后提问",
        "expected_response_indicators": [
          "技术深度",
          "表达清晰度",
          "情绪稳定性",
          "自信程度"
        ]
      }
    ],
    "total_count": 5,
    "generation_context": {
      "difficulty": "medium",
      "question_type": "mixed",
      "psychological_context_used": true,
      "conversation_history_used": true
    }
  }
}
```

#### 4.2 获取实时洞察
```http
GET /api/v1/immersive/{session_id}/insights
```

**功能**: 基于心理状态的实时面试洞察和建议

**响应示例**:
```json
{
  "success": true,
  "message": "面试洞察获取成功",
  "data": {
    "insights": [
      {
        "category": "参与度",
        "content": "候选人参与度很高，表现出强烈的兴趣",
        "severity": "info",
        "timestamp": "2024-01-01T10:15:00Z"
      }
    ],
    "alerts": [
      {
        "category": "情绪状态",
        "content": "候选人紧张程度较高，建议营造轻松氛围",
        "severity": "warning",
        "timestamp": "2024-01-01T10:15:00Z"
      }
    ],
    "suggestions": [
      "可以先聊一些轻松的话题，让候选人放松",
      "尝试询问候选人感兴趣的技术领域"
    ],
    "session_quality_score": 88.5,
    "psychological_wellness_score": 85.2
  }
}
```

### 5. 统计查询

#### 4.1 获取会话统计
```http
GET /api/v1/immersive/{session_id}/statistics
```

**响应示例**:
```json
{
  "success": true,
  "message": "统计数据获取成功",
  "data": {
    "total_segments": 25,
    "candidate_segments": 15,
    "interviewer_segments": 10,
    "candidate_speak_ratio": 0.6,
    "interviewer_speak_ratio": 0.4,
    "avg_engagement": 0.82,
    "avg_confidence": 0.75,
    "avg_nervousness": 0.25,
    "session_quality_score": 88.5
  }
}
```

## 使用流程

### 典型的面试流程

1. **创建会话**
   ```http
   POST /api/v1/immersive
   ```

2. **开始录制**
   ```http
   POST /api/v1/immersive/{session_id}/start
   ```

3. **实时数据同步** (循环进行)
   ```http
   POST /api/v1/immersive/{session_id}/sync
   ```

4. **完成会话并获取汇总**
   ```http
   POST /api/v1/immersive/{session_id}/complete
   ```

### 数据收集建议

#### Sync 请求
- 建议每 2-5 秒同步一次发言数据
- 每次 sync 都带上当前候选人的三项心理评分（不管发言人是谁）
- 时间戳使用毫秒格式，后端会自动转换为秒存储

#### 心理评分更新
- 大五人格：基于候选人回答内容的实时分析
- 欺骗检测：基于语音/表情的实时检测
- 抑郁风险：基于整体表现的持续评估

## 错误处理

### 常见错误码

- `404`: 会话不存在
- `400`: 请求参数错误
- `409`: 会话状态冲突（如已完成的会话不能再录制）

### 错误响应格式
```json
{
  "success": false,
  "code": 404,
  "message": "沉浸式面试会话不存在: session_123",
  "data": null
}
```

## 数据安全和隐私

### 敏感数据处理
- 心理分析数据被标记为敏感信息
- 支持数据匿名化和访问控制
- 遵循数据保护法规要求

### 数据保留策略
- 会话数据默认保留 365 天
- 可配置自动归档和删除策略
- 支持手动数据导出

## 与其他模块的集成

### Analysis 模块
沉浸式面试的数据会被 Analysis 模块用于生成综合分析报告：

```http
POST /api/v1/analysis
{
  "application_id": "app_123"
}
```

Analysis 模块会自动收集：
- 简历筛选结果
- 视频分析结果
- 传统面试记录
- **沉浸式面试数据** ← 新增
- 生成最终的录用建议

## 开发和测试

### 本地开发
```bash
# 启动服务
python run.py --reload

# 访问 API 文档
http://127.0.0.1:8000/docs
```

### API 测试
推荐使用 Swagger UI 进行交互式测试：
- 访问 `http://127.0.0.1:8000/docs`
- 找到 "沉浸式面试" 标签
- 直接在浏览器中测试所有接口

---

**版本**: v2.0 (重构版)  
**更新时间**: 2025-01-18  
**维护者**: HRM2 开发团队

### 变更记录

**v2.0 (2025-01-18)**
- 简化 `/sync` 接口：使用 `utterances` 结构替代分散的 `transcripts`/`speaker_segments`/`state_records`
- 简化 `/complete` 返回：统一返回 `statistics` + `conversation_history` 结构
- 新增三项心理评分捆绑：`big_five` + `deception` + `depression`
- 完成数据自动保存到 `final_analysis` 供后续推荐使用
- 废弃 `state_records`，保留旧版接口 `/sync-legacy` 兼容