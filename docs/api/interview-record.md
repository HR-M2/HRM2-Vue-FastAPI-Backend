# 面试记录查询接口 API 文档（精简版）

> **版本**: v1.0  
> **更新日期**: 2026-01-19  
> **适用场景**: 最终推荐模块查询面试记录

---

## 接口概述

提供精简版面试记录查询，仅返回最终推荐所需的核心数据。

| 接口 | 方法 | 说明 |
|-----|------|------|
| `/api/v1/immersive/{session_id}/record` | GET | 按会话ID查询 |
| `/api/v1/immersive/by-application/{application_id}/record` | GET | 按申请ID查询（推荐） |

---

## 接口1: 按会话ID查询

### 请求

```
GET /api/v1/immersive/{session_id}/record
```

### 路径参数

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| session_id | string | 是 | 沉浸式面试会话ID |

---

## 接口2: 按申请ID查询（推荐）

### 请求

```
GET /api/v1/immersive/by-application/{application_id}/record
```

### 路径参数

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| application_id | string | 是 | 应聘申请ID |

**优点**：自动获取该申请最新的已完成面试记录，无需前端维护 session_id

---

## 响应结构

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "session-uuid",
    "application_id": "app-uuid",
    "candidate_name": "张三",
    "position_title": "产品经理",
    "created_at": "2026-01-19T09:00:00",
    "start_time": "2026-01-19T10:00:00",
    "end_time": "2026-01-19T10:30:00",
    "duration_seconds": 1800,
    "is_completed": true,
    
    "statistics": {
      "utterance_count": {
        "total": 50,
        "interviewer": 22,
        "candidate": 28
      },
      "char_count": {
        "total": 5000,
        "interviewer": 1800,
        "candidate": 3200
      },
      "speaking_ratio": {
        "by_count": {
          "interviewer": 0.44,
          "candidate": 0.56
        },
        "by_chars": {
          "interviewer": 0.36,
          "candidate": 0.64
        }
      },
      "big_five_average": {
        "openness": 0.62,
        "conscientiousness": 0.71,
        "extraversion": 0.55,
        "agreeableness": 0.68,
        "neuroticism": 0.32
      },
      "depression_average": {
        "score": 12.5,
        "level": "low"
      }
    },
    
    "conversation_history": [
      {
        "speaker": "interviewer",
        "text": "请简单介绍一下自己",
        "timestamp": "2026-01-19T10:01:00",
        "candidate_scores": null
      },
      {
        "speaker": "candidate",
        "text": "您好，我叫张三，毕业于清华大学计算机系...",
        "timestamp": "2026-01-19T10:01:30",
        "candidate_scores": {
          "big_five": {
            "openness": 0.65,
            "conscientiousness": 0.72,
            "extraversion": 0.58,
            "agreeableness": 0.70,
            "neuroticism": 0.28
          },
          "deception": {
            "score": 0.15,
            "confidence": 0.85
          },
          "depression": {
            "score": 10.5,
            "level": "low",
            "confidence": 0.88
          }
        }
      }
    ]
  }
}
```

---

## 字段说明

### 基本信息

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | string | 面试会话ID |
| application_id | string | 关联的应聘申请ID |
| candidate_name | string | 候选人姓名 |
| position_title | string | 应聘岗位 |
| created_at | datetime | 会话创建时间 |
| start_time | datetime | 面试开始时间 |
| end_time | datetime | 面试结束时间 |
| duration_seconds | float | 面试时长（秒） |
| is_completed | boolean | 是否已完成 |

### statistics 统计数据

| 字段 | 类型 | 说明 |
|-----|------|------|
| utterance_count | object | 发言次数统计 |
| char_count | object | 字数统计 |
| speaking_ratio | object | 发言占比（按次数/按字数） |
| big_five_average | object | 大五人格平均值 |
| depression_average | object | 抑郁指数平均值 |

### conversation_history 会话记录

| 字段 | 类型 | 说明 |
|-----|------|------|
| speaker | string | `interviewer` 或 `candidate` |
| text | string | 发言内容 |
| timestamp | string | ISO格式时间戳 |
| candidate_scores | object/null | 心理评分（仅候选人有） |

### candidate_scores 心理评分

| 字段 | 说明 | 数值范围 |
|-----|------|---------|
| big_five | 大五人格 | 各维度 0-1 |
| deception | 欺骗检测 | score 0-1，越高越可疑 |
| depression | 抑郁风险 | score 0-100，level: low/medium/high |

---

## 与旧接口对比

| 字段 | 旧接口 | 新接口（精简版） |
|-----|--------|-----------------|
| id | ✅ | ✅ |
| application_id | ✅ | ✅ |
| candidate_name | ✅ | ✅ |
| position_title | ✅ | ✅ |
| created_at | ✅ | ✅ |
| start_time | ✅ | ✅ |
| end_time | ✅ | ✅ |
| duration_seconds | ✅ | ✅ |
| is_completed | ✅ | ✅ |
| statistics | ❌ | ✅ **新增** |
| conversation_history | ❌ | ✅ **新增** |
| local_camera_enabled | ✅ | ❌ 移除 |
| stream_url | ✅ | ❌ 移除 |
| config | ✅ | ❌ 移除 |
| transcripts | ✅ | ❌ 移除 |
| speaker_segments | ✅ | ❌ 移除 |
| state_history | ✅ | ❌ 移除 |
| final_analysis | ✅ | ❌ 移除（数据已展开） |

---

## 错误码

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 404 | 沉浸式面试会话不存在 | session_id 无效 |
| 404 | 未找到该申请的已完成面试记录 | application_id 无效或无已完成记录 |
| 400 | 面试会话尚未完成，无法获取记录 | 会话未完成 |

---

## 调用示例

### 最终推荐模块（推荐用法）

```javascript
// 使用 application_id 查询
async function getInterviewRecord(applicationId) {
  const response = await axios.get(
    `/api/v1/immersive/by-application/${applicationId}/record`
  );
  return response.data.data;
}

// 使用示例
const record = await getInterviewRecord('app-uuid');

// 获取统计数据
const { statistics, conversation_history } = record;
console.log('大五人格平均值:', statistics.big_five_average);
console.log('抑郁水平:', statistics.depression_average);
console.log('发言占比:', statistics.speaking_ratio);

// 遍历会话记录
conversation_history.forEach(item => {
  console.log(`${item.speaker}: ${item.text}`);
  if (item.candidate_scores) {
    console.log('  欺骗分数:', item.candidate_scores.deception.score);
  }
});
```

---

## 数据来源

此接口返回的数据来自 `final_analysis` 字段，该字段在调用 `POST /api/v1/immersive/{session_id}/complete` 时自动计算并存储。

```
面试完成 (complete) → 计算统计数据 → 存储到 final_analysis → 查询时直接返回
```

**优点**：
- 查询时无需重复计算，响应更快
- 数据一致性：统计数据与面试完成时刻一致
- 精简响应：只返回最终推荐所需字段
