# 沉浸式面试 API 文档

## 概述

沉浸式面试模块提供双摄像头面试、说话人识别、实时状态分析等功能，支持完整的心理分析数据收集和处理。

**基础路径**: `/api/v1/immersive`

**特性**:
- 🎥 双摄像头支持（本地 + 远程推流）
- 🎤 实时语音转录和说话人识别
- 🧠 大五人格分析和抑郁风险评估
- 📊 实时心理状态监控
- 📈 面试完成后即时数据汇总

## 数据模型

### 核心实体

```json
{
  "id": "会话ID",
  "application_id": "应聘申请ID",
  "local_camera_enabled": true,
  "stream_url": "rtmp://example.com/live/stream",
  "is_recording": false,
  "is_completed": false,
  "start_time": "2024-01-01T10:00:00Z",
  "end_time": "2024-01-01T10:30:00Z",
  "duration_seconds": 1800,
  "transcripts": [...],
  "speaker_segments": [...],
  "state_history": [...],
  "statistics": {...},
  "psychological_summary": {...}
}
```

### 心理分析数据

#### 大五人格 (Big Five Personality)
```json
{
  "openness": 0.75,        // 开放性 (0-1)
  "conscientiousness": 0.82, // 尽责性 (0-1)
  "extraversion": 0.68,    // 外向性 (0-1)
  "agreeableness": 0.71,   // 宜人性 (0-1)
  "neuroticism": 0.35      // 神经质 (0-1)
}
```

#### 抑郁风险评估
```json
{
  "score": 15.2,           // 抑郁可能性 (0-100)
  "level": "low",          // 风险等级: low/medium/high
  "confidence": 0.88       // 分析置信度 (0-1)
}
```

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

**重要**: 此接口会返回完整的面试数据汇总，包括：
- 所有转录记录
- 说话人分段（含心理分析）
- 状态历史记录
- 统计数据汇总
- 心理分析汇总

**响应示例**:
```json
{
  "success": true,
  "message": "沉浸式面试会话已完成",
  "data": {
    "session_info": {
      "id": "session_123",
      "duration_seconds": 1800,
      "start_time": "2024-01-01T10:00:00Z",
      "end_time": "2024-01-01T10:30:00Z",
      "is_completed": true
    },
    "statistics": {
      "total_segments": 25,
      "candidate_segments": 15,
      "interviewer_segments": 10,
      "candidate_speak_ratio": 0.6,
      "interviewer_speak_ratio": 0.4,
      "avg_engagement": 0.82,
      "avg_confidence": 0.75,
      "avg_nervousness": 0.25,
      "session_quality_score": 88.5
    },
    "psychological_summary": {
      "final_big_five": {
        "openness": {
          "score": 0.75,
          "percentile": 78,
          "description": "较高的开放性，乐于接受新想法"
        }
      },
      "depression_assessment": {
        "overall_score": 16.8,
        "risk_level": "low",
        "trend_analysis": "stable"
      },
      "psychological_wellness_score": 85.2
    },
    "full_transcripts": [...],
    "full_speaker_segments": [...],
    "full_state_history": [...],
    "candidate_info": {
      "name": "张三",
      "position_title": "高级软件工程师"
    }
  }
}
```

### 3. 实时数据同步

#### 3.1 批量同步数据 ⭐
```http
POST /api/v1/immersive/{session_id}/sync
```

**请求体**:
```json
{
  "transcripts": [
    {
      "speaker": "interviewer",
      "text": "请介绍一下你自己",
      "is_final": true
    }
  ],
  "speaker_segments": [
    {
      "speaker": "candidate",
      "start_time": 10.5,
      "end_time": 25.3,
      "text": "我是一名软件工程师...",
      "confidence": 0.92,
      "big_five_personality": {
        "openness": 0.75,
        "conscientiousness": 0.82,
        "extraversion": 0.68,
        "agreeableness": 0.71,
        "neuroticism": 0.35
      },
      "depression_risk": {
        "score": 15.2,
        "level": "low",
        "confidence": 0.88
      }
    }
  ],
  "state_records": [
    {
      "segment_id": "seg_001",
      "emotion": {
        "emotion": "confident",
        "confidence": 0.85,
        "valence": 0.6,
        "arousal": 0.4
      },
      "engagement": 0.8,
      "nervousness": 0.2,
      "confidence_level": 0.75,
      "eye_contact": 0.9,
      "posture_score": 0.85,
      "speech_clarity": 0.9,
      "speech_pace": "normal"
    }
  ]
}
```

#### 3.2 添加单条转录
```http
POST /api/v1/immersive/{session_id}/transcript
```

**请求体**:
```json
{
  "speaker": "candidate",
  "text": "我认为这个问题很有趣...",
  "is_final": true
}
```

#### 3.3 添加说话人分段
```http
POST /api/v1/immersive/{session_id}/segment
```

**请求体**:
```json
{
  "speaker": "candidate",
  "start_time": 30.0,
  "end_time": 45.5,
  "text": "关于这个技术问题，我的理解是...",
  "confidence": 0.95,
  "big_five_personality": {
    "openness": 0.78,
    "conscientiousness": 0.85,
    "extraversion": 0.70,
    "agreeableness": 0.73,
    "neuroticism": 0.32
  },
  "depression_risk": {
    "score": 14.8,
    "level": "low",
    "confidence": 0.90
  }
}
```

#### 3.4 添加状态记录
```http
POST /api/v1/immersive/{session_id}/state
```

**请求体**:
```json
{
  "segment_id": "seg_002",
  "emotion": {
    "emotion": "focused",
    "confidence": 0.88,
    "valence": 0.5,
    "arousal": 0.6
  },
  "engagement": 0.85,
  "nervousness": 0.15,
  "confidence_level": 0.80,
  "eye_contact": 0.92,
  "posture_score": 0.88,
  "speech_clarity": 0.93,
  "speech_pace": "normal"
}
```

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

#### 转录数据
- 建议每 2-5 秒同步一次转录数据
- 使用 `is_final=false` 表示临时结果，`is_final=true` 表示最终结果

#### 说话人分段
- 当检测到说话人切换时添加分段
- 候选人分段应包含心理分析数据
- 面试官分段可以不包含心理分析

#### 状态记录
- 建议每 10-30 秒记录一次候选人状态
- 关键时刻（如回答重要问题时）可以增加记录频率

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

**版本**: v1.0  
**更新时间**: 2024-01-17  
**维护者**: HRM2 开发团队