# 沉浸式面试前端集成指南

> **版本**: v2.0  
> **更新日期**: 2025-01-18  
> **适用对象**: 前端开发人员

---

## 一、概述

本文档描述沉浸式面试模块的完整业务流程，供前端重构参考。

**核心数据流**:
```
创建会话 → 开始录制 → [循环: 同步发言+心理评分] → 完成会话 → 获取面试报告
```

**三项心理评分**（贯穿整个面试过程）:
| 评分项 | 字段名 | 说明 |
|-------|-------|------|
| 大五人格 | `big_five` | 开放性/尽责性/外向性/宜人性/神经质，各维度 0-1 |
| 欺骗检测 | `deception` | score: 0-1，越高越可能欺骗 |
| 抑郁风险 | `depression` | score: 0-100，level: low/medium/high |

---

## 二、完整面试流程

### 阶段 1: 创建会话

**时机**: 用户进入沉浸式面试页面时

**接口**: `POST /api/v1/immersive`

**请求体**:
```json
{
  "application_id": "应聘申请ID（必填）",
  "local_camera_enabled": true,
  "stream_url": "rtmp://...",
  "config": {}
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": "session_xxx",  // 后续所有接口都需要此 session_id
    "application_id": "...",
    "is_recording": false,
    "is_completed": false,
    ...
  }
}
```

**前端处理**:
1. 保存返回的 `session_id`，后续所有接口都需要
2. 如果该 `application_id` 已存在会话，后端会自动删除旧会话并创建新会话

---

### 阶段 2: 开始录制

**时机**: 用户点击"开始面试"按钮

**接口**: `POST /api/v1/immersive/{session_id}/start`

**响应**:
```json
{
  "success": true,
  "data": {
    "session_id": "session_xxx",
    "status": "recording",
    "start_time": "2025-01-18T10:00:00"
  }
}
```

**前端处理**:
1. 调用成功后，启动本地的语音识别/心理分析模块
2. 开始定时器，准备进行数据同步
3. UI 切换到"面试进行中"状态

---

### 阶段 3: 实时数据同步（核心）

**时机**: 面试进行过程中，每当检测到新的发言时

**接口**: `POST /api/v1/immersive/{session_id}/sync`

**调用频率建议**: 
- **方式 A**: 每检测到一条完整发言就同步（推荐）
- **方式 B**: 批量累积 2-5 秒的发言后同步

#### 请求结构

```json
{
  "utterances": [
    {
      "speaker": "interviewer",
      "text": "请介绍一下你自己",
      "timestamp": 1737187200000,
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
    }
  ]
}
```

#### 字段规范

| 字段 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| `utterances` | array | ✅ | 发言记录数组，至少包含 1 条 |
| `utterances[].speaker` | string | ✅ | 固定值：`"interviewer"` 或 `"candidate"` |
| `utterances[].text` | string | ✅ | 发言内容，不能为空 |
| `utterances[].timestamp` | number | ✅ | **毫秒时间戳**（后端自动转秒存储） |
| `utterances[].candidate_scores` | object | ⚠️ | 候选人心理评分，强烈建议每次都带 |

#### 关键规则

1. **`candidate_scores` 必须每次都带**
   - 不管当前 `speaker` 是 `interviewer` 还是 `candidate`，都要带上候选人的实时心理评分
   - 这是因为心理分析是持续进行的，每个时间点都需要记录

2. **时间戳格式**
   - 发送 **毫秒时间戳**（如 `Date.now()` 返回的值）
   - 后端会自动识别并转换为秒存储

3. **发言顺序**
   - `utterances` 数组中的发言应按时间顺序排列
   - 每条发言的 `timestamp` 应递增

#### 响应

```json
{
  "success": true,
  "data": {
    "session_id": "session_xxx",
    "synced_count": 1,
    "total_utterances": 15
  }
}
```

---

### 阶段 4: 获取问题提示（可选）

**时机**: 面试过程中，面试官需要问题建议时

**接口**: `POST /api/v1/immersive/{session_id}/questions`

**请求体**:
```json
{
  "count": 5,
  "difficulty": "medium",
  "focus_areas": ["技术能力", "团队协作"],
  "use_psychological_context": false,
  "use_conversation_history": true,
  "question_type": "mixed"
}
```

**参数说明**:
| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `count` | int | 5 | 生成问题数量，范围 1-20 |
| `difficulty` | string | "medium" | 难度：easy/medium/hard |
| `focus_areas` | array | null | 关注领域，如 ["技术能力", "沟通能力"] |
| `use_psychological_context` | bool | false | 是否使用心理分析上下文（当前固定为 false） |
| `use_conversation_history` | bool | true | 是否基于对话历史生成问题 |
| `question_type` | string | "mixed" | 问题类型：technical/behavioral/situational/mixed |

**响应示例**:
```json
{
  "success": true,
  "data": {
    "suggestions": [
      {
        "question": "你刚才提到了微服务架构，能具体说说你们是如何处理服务间通信的吗？",
        "type": "technical",
        "priority": 1,
        "reason": "基于对话历史中提到的技术点进行追问",
        "timing_suggestion": "适合在当前话题结束后提问"
      }
    ],
    "total_count": 5,
    "generation_context": {
      "difficulty": "medium",
      "question_type": "mixed",
      "psychological_context_used": false,
      "conversation_history_used": true
    }
  }
}
```

**前端处理**:
1. 将问题建议展示在 UI 上供面试官参考
2. `priority` 越小优先级越高（1 最高）
3. 面试官可以直接使用或修改后使用

---

### 阶段 5: 完成会话

**时机**: 用户点击"结束面试"按钮

**接口**: `POST /api/v1/immersive/{session_id}/complete`

**请求体**: 无

#### 响应结构

```json
{
  "success": true,
  "message": "沉浸式面试会话已完成",
  "data": {
    "session_id": "session_xxx",
    "duration_seconds": 1800,
    "start_time": "2025-01-18T10:00:00",
    "end_time": "2025-01-18T10:30:00",
    
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
        "timestamp": "2025-01-18T10:00:05",
        "candidate_scores": {
          "big_five": {...},
          "deception": {...},
          "depression": {...}
        }
      },
      {
        "speaker": "candidate",
        "text": "我是一名软件工程师...",
        "timestamp": "2025-01-18T10:00:15",
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

#### 响应字段说明

| 字段 | 说明 |
|-----|------|
| `duration_seconds` | 面试总时长（秒） |
| `statistics.total_utterances` | 总发言数 |
| `statistics.interviewer_utterances` | 面试官发言数 |
| `statistics.candidate_utterances` | 候选人发言数 |
| `statistics.interviewer_ratio` | 面试官发言占比（0-1） |
| `statistics.candidate_ratio` | 候选人发言占比（0-1） |
| `statistics.overall_depression` | 总体抑郁水平评估 |
| `conversation_history` | 完整会话历史，每条记录都捆绑三项心理评分 |
| `candidate_info` | 候选人基本信息 |

#### 前端处理

1. 展示面试报告页面
2. 可视化统计数据（如发言比例饼图）
3. 按时间轴展示 `conversation_history`，每条记录显示对应的心理评分
4. 展示总体抑郁水平和趋势

---

## 三、完整流程时序图

```
┌─────────┐                                    ┌─────────┐
│  前端   │                                    │  后端   │
└────┬────┘                                    └────┬────┘
     │                                              │
     │  1. POST /immersive                          │
     │  (创建会话)                                   │
     │─────────────────────────────────────────────>│
     │<─────────────────────────────────────────────│
     │  返回 session_id                             │
     │                                              │
     │  2. POST /immersive/{id}/start               │
     │  (开始录制)                                   │
     │─────────────────────────────────────────────>│
     │<─────────────────────────────────────────────│
     │                                              │
     │  ╔═══════════════════════════════════════╗   │
     │  ║        面试进行中 (循环)               ║   │
     │  ╚═══════════════════════════════════════╝   │
     │                                              │
     │  3. POST /immersive/{id}/sync                │
     │  (同步发言 + 心理评分)                        │
     │─────────────────────────────────────────────>│
     │<─────────────────────────────────────────────│
     │                                              │
     │  4. POST /immersive/{id}/questions (可选)    │
     │  (获取问题提示)                               │
     │─────────────────────────────────────────────>│
     │<─────────────────────────────────────────────│
     │                                              │
     │  ... (重复 3-4)                              │
     │                                              │
     │  ╔═══════════════════════════════════════╗   │
     │  ║        面试结束                        ║   │
     │  ╚═══════════════════════════════════════╝   │
     │                                              │
     │  5. POST /immersive/{id}/complete            │
     │  (完成会话，获取报告)                         │
     │─────────────────────────────────────────────>│
     │<─────────────────────────────────────────────│
     │  返回完整面试报告                             │
     │                                              │
```

---

## 四、错误处理

### 常见错误码

| HTTP 状态码 | 错误类型 | 处理建议 |
|------------|---------|---------|
| 404 | 会话不存在 | 检查 session_id 是否正确，或会话是否已被删除 |
| 400 | 请求参数错误 | 检查请求体格式是否符合规范 |
| 409 | 会话状态冲突 | 如已完成的会话不能再同步数据 |

### 错误响应格式

```json
{
  "success": false,
  "code": 404,
  "message": "沉浸式面试会话不存在: session_xxx",
  "data": null
}
```

### 前端错误处理建议

1. **网络错误**: 实现重试机制，sync 请求失败时本地缓存，稍后重试
2. **会话不存在**: 提示用户重新创建会话
3. **会话已完成**: 禁止继续同步，直接跳转到报告页面

---

## 五、注意事项

### 数据一致性

1. **心理评分连续性**: 确保每次 sync 都带上最新的 `candidate_scores`，即使发言人是面试官
2. **时间戳准确性**: 使用本地时间戳，确保发言顺序正确
3. **发言完整性**: 建议在发言完成（语音识别 final 结果）后再同步

### 性能优化

1. **批量同步**: 可以累积多条发言后一次性同步，减少请求次数
2. **问题缓存**: 问题建议可以本地缓存，避免重复请求
3. **防抖处理**: sync 请求建议做防抖，避免过于频繁

### 会话状态管理

| 状态 | `is_recording` | `is_completed` | 可执行操作 |
|-----|---------------|----------------|-----------|
| 已创建 | false | false | start |
| 录制中 | true | false | sync, questions, stop, complete |
| 已停止 | false | false | start, complete |
| 已完成 | false | true | 只能查看，不能修改 |

---

## 六、接口汇总

| 接口 | 方法 | 说明 |
|-----|------|------|
| `/api/v1/immersive` | POST | 创建会话 |
| `/api/v1/immersive/{id}` | GET | 获取会话详情 |
| `/api/v1/immersive/{id}` | DELETE | 删除会话 |
| `/api/v1/immersive/{id}/start` | POST | 开始录制 |
| `/api/v1/immersive/{id}/stop` | POST | 停止录制 |
| `/api/v1/immersive/{id}/sync` | POST | **同步发言数据（核心）** |
| `/api/v1/immersive/{id}/complete` | POST | **完成会话（核心）** |
| `/api/v1/immersive/{id}/questions` | POST | 获取问题建议 |
| `/api/v1/immersive/{id}/statistics` | GET | 获取实时统计 |
| `/api/v1/immersive/{id}/insights` | GET | 获取实时洞察 |

---

**如有疑问，请联系后端开发人员。**
