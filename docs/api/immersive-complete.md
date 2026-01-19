# 沉浸式面试完成接口 API 文档

> **版本**: v2.0  
> **更新日期**: 2026-01-19  
> **变更说明**: 新增大五人格平均值、字数统计、多维度发言占比

---

## 接口概述

完成沉浸式面试会话，计算统计数据并保存到数据库。

| 项目 | 说明 |
|-----|------|
| **URL** | `POST /api/v1/immersive/{session_id}/complete` |
| **认证** | 需要登录 |
| **耗时** | < 1s |

---

## 请求参数

### 路径参数

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| session_id | string | 是 | 沉浸式面试会话ID |

### 请求体

无

---

## 响应结构

```json
{
  "code": 200,
  "message": "沉浸式面试会话已完成",
  "data": {
    "session_id": "abc123",
    "duration_seconds": 1800,
    "start_time": "2026-01-19T10:00:00",
    "end_time": "2026-01-19T10:30:00",
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
        "text": "您好，我叫张三，毕业于...",
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
    ],
    "candidate_info": {
      "name": "张三",
      "position_title": "产品经理"
    }
  }
}
```

---

## 字段说明

### statistics 统计数据

| 字段 | 类型 | 说明 |
|-----|------|------|
| `utterance_count.total` | int | 总发言次数 |
| `utterance_count.interviewer` | int | 面试官发言次数 |
| `utterance_count.candidate` | int | 候选人发言次数 |
| `char_count.total` | int | 总字数 |
| `char_count.interviewer` | int | 面试官总字数 |
| `char_count.candidate` | int | 候选人总字数 |
| `speaking_ratio.by_count` | object | 按次数计算的发言占比 |
| `speaking_ratio.by_chars` | object | 按字数计算的发言占比 |
| `big_five_average` | object | 大五人格平均值（0-1） |
| `depression_average.score` | float | 抑郁指数平均值（0-100） |
| `depression_average.level` | string | 抑郁等级：`low`/`medium`/`high` |

### big_five_average 大五人格

| 维度 | 英文 | 说明 | 高分特征 |
|-----|------|------|---------|
| 开放性 | openness | 对新事物的接受程度 | 创意、好奇、想象力丰富 |
| 尽责性 | conscientiousness | 自律和目标导向 | 有组织、可靠、勤奋 |
| 外向性 | extraversion | 社交活跃程度 | 健谈、活力充沛、自信 |
| 宜人性 | agreeableness | 合作与同理心 | 友善、信任他人、乐于助人 |
| 神经质 | neuroticism | 情绪稳定性（反向） | 焦虑、情绪波动、敏感 |

### depression_average.level 抑郁等级判定

| 等级 | 分数范围 | 说明 |
|-----|---------|------|
| low | 0-30 | 低风险，情绪稳定 |
| medium | 30-60 | 中等风险，需关注 |
| high | 60+ | 高风险，建议专业评估 |

### conversation_history 会话记录

| 字段 | 类型 | 说明 |
|-----|------|------|
| `speaker` | string | 说话人：`interviewer` 或 `candidate` |
| `text` | string | 发言内容 |
| `timestamp` | string | ISO格式时间戳 |
| `candidate_scores` | object/null | 心理评分（仅候选人发言有值） |

---

## 数据存储

调用此接口后，完整的返回数据会自动保存到数据库的 `final_analysis` 字段，供后续"最终推荐"模块使用。

```
ImmersiveSession.final_analysis = {
  "session_id": "...",
  "statistics": {...},
  "conversation_history": [...],
  ...
}
```

---

## 错误码

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 404 | 会话不存在 | session_id 无效 |
| 400 | 完成会话失败 | 会话状态异常 |

---

## 调用示例

### cURL

```bash
curl -X POST "http://localhost:8000/api/v1/immersive/abc123/complete" \
  -H "Authorization: Bearer <token>"
```

### JavaScript (Axios)

```javascript
const response = await axios.post(
  `/api/v1/immersive/${sessionId}/complete`
);

const { statistics, conversation_history } = response.data.data;

// 使用统计数据
console.log('大五人格平均值:', statistics.big_five_average);
console.log('抑郁水平:', statistics.depression_average);
console.log('发言占比(按字数):', statistics.speaking_ratio.by_chars);
```

---

## 前端展示建议

### 1. 统计卡片

```
┌─────────────────────────────────────────────────────┐
│  面试时长: 30分钟    总发言: 50次    总字数: 5000字   │
├─────────────────────────────────────────────────────┤
│  发言占比（按次数）          发言占比（按字数）        │
│  ████████░░ 候选人 56%      ██████████░ 候选人 64%   │
│  ██████░░░░ 面试官 44%      ██████░░░░░ 面试官 36%   │
└─────────────────────────────────────────────────────┘
```

### 2. 大五人格雷达图

```
         开放性 0.62
            ▲
           /|\
          / | \
  神经质 /  |  \ 尽责性
   0.32 ◄──┼──► 0.71
          \ | /
           \|/
            ▼
        外向性 0.55
```

### 3. 抑郁风险指示器

```
低风险 ●───────────○─────────────○ 高风险
       ▲
    12.5分
```
