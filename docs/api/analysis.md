# 综合分析 API 文档

> **版本**: v2.0 (重构版)  
> **更新日期**: 2025-01-18  
> **数据来源**: 沉浸式面试会话数据

---

## 一、概述

综合分析模块整合简历筛选、沉浸式面试数据，基于 Rubric 量表进行多维度评估，生成最终录用建议报告。

### 数据流

```
简历内容 ──────────────────────────────┐
                                       │
简历初筛报告 ─────────────────────────→│
                                       ├──→ AI 综合分析 ──→ 最终推荐报告
沉浸式面试会话 ──→ conversation_history │
       │                               │
       └─→ 心理评分（大五/欺骗/抑郁）────┘
```

### 评估维度

| 维度 | 名称 | 权重 | 子维度 |
|-----|------|------|--------|
| `professional_competency` | 专业能力 | 30% | 核心技能、专业知识、问题解决、学习潜力 |
| `work_experience` | 工作经验 | 25% | 经验相关性、项目复杂度、成果量化、职责承担 |
| `soft_skills` | 软技能 | 20% | 沟通表达、团队协作、压力应对、主动责任 |
| `cultural_fit` | 文化匹配 | 15% | 价值观、工作态度、发展意愿、稳定性 |
| `interview_performance` | 面试表现 | 10% | 回答逻辑、思维深度、应变能力、自我认知 |

### 推荐等级

| 等级 | 中文标签 | 最低分 | 建议行动 |
|-----|---------|-------|---------|
| `strong_recommend` | 强烈推荐 | ≥85 | 优先录用，尽快安排后续流程 |
| `recommend` | 推荐录用 | ≥70 | 符合要求，可以录用 |
| `cautious` | 谨慎考虑 | ≥55 | 存在风险，建议进一步评估 |
| `not_recommend` | 不推荐 | <55 | 不建议录用 |

---

## 二、API 接口

### 2.1 创建综合分析 ⭐

```http
POST /api/v1/analysis
```

**功能**: 为指定应聘申请创建综合分析，执行 AI 多维度评估，生成最终录用建议。

**前置条件**:
- 应聘申请必须存在
- 沉浸式面试会话必须已完成（`is_completed=true`）
- LLM 服务必须已配置

**请求体**:
```json
{
  "application_id": "app_123"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "综合分析创建成功",
  "data": {
    "id": "analysis_456",
    "application_id": "app_123",
    "final_score": 78.5,
    "recommendation_level": "推荐录用",
    "recommendation_reason": "推荐录用",
    "suggested_action": "符合要求，可以录用",
    
    "dimension_scores": {
      "professional_competency": {
        "dimension_score": 4,
        "dimension_name": "专业能力",
        "weight": 0.3,
        "sub_scores": {
          "核心技能掌握程度": 4,
          "专业知识深度": 4,
          "问题解决能力": 3,
          "学习成长潜力": 4
        },
        "strengths": ["技术栈匹配度高", "有大型项目经验"],
        "weaknesses": ["算法能力有待提升"],
        "analysis": "候选人具备扎实的技术基础..."
      },
      "work_experience": {...},
      "soft_skills": {...},
      "cultural_fit": {...},
      "interview_performance": {...}
    },
    
    "report": "## 张三 综合分析报告\n\n**综合评价**：...",
    
    "input_snapshot": {
      "position": "高级软件工程师",
      "candidate": "张三",
      "psychological_analysis": {
        "big_five": {
          "scores": {
            "openness": 0.75,
            "conscientiousness": 0.82,
            "extraversion": 0.68,
            "agreeableness": 0.71,
            "neuroticism": 0.35
          },
          "personality_summary": "开放务实、责任心强、善于合作",
          "strengths": ["做事认真负责", "乐于接受新事物"],
          "potential_concerns": ["可能在高压环境下情绪波动"],
          "work_style": "注重计划和条理，善于独立完成任务",
          "team_fit": "适合需要协作但也有独立空间的团队",
          "detailed_analysis": "候选人展现出较高的开放性和尽责性..."
        },
        "credibility": {
          "overall_score": 0.85,
          "level": "高可信度",
          "low_credibility_responses": [],
          "high_credibility_responses": [
            {
              "text": "我在上一家公司负责了核心模块的重构...",
              "deception_score": 0.08,
              "confidence": 0.92
            }
          ],
          "analysis": "面试整体可信度为 85.0%，属于高可信度。未发现明显的不可信回答，候选人陈述整体可信。"
        },
        "depression": {
          "overall_score": 18.5,
          "level": "low",
          "level_label": "低风险",
          "level_distribution": {"low": 45, "medium": 5, "high": 0},
          "interpretation": "候选人在面试过程中整体心理状态良好，未发现明显的抑郁倾向。"
        }
      },
      "immersive_session_id": "session_789"
    },
    
    "candidate_name": "张三",
    "position_title": "高级软件工程师",
    "created_at": "2025-01-18T17:30:00",
    "updated_at": "2025-01-18T17:30:00"
  }
}
```

### 2.2 获取综合分析详情

```http
GET /api/v1/analysis/{analysis_id}
```

**响应**: 同上

### 2.3 获取综合分析列表

```http
GET /api/v1/analysis
```

**查询参数**:
| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页数量，最大100 |
| `application_id` | string | - | 按应聘申请ID筛选 |
| `recommendation_level` | string | - | 按推荐等级筛选 |

### 2.4 删除综合分析

```http
DELETE /api/v1/analysis/{analysis_id}
```

---

## 三、数据模型

### 3.1 维度评分结构 (DimensionScoreItem)

```json
{
  "dimension_score": 4,
  "dimension_name": "专业能力",
  "weight": 0.3,
  "sub_scores": {
    "核心技能掌握程度": 4,
    "专业知识深度": 4,
    "问题解决能力": 3,
    "学习成长潜力": 4
  },
  "strengths": ["优势1", "优势2"],
  "weaknesses": ["不足1"],
  "analysis": "详细分析说明"
}
```

### 3.2 心理分析结构 (PsychologicalAnalysis)

#### 大五人格分析 (BigFiveAnalysis)

```json
{
  "scores": {
    "openness": 0.75,
    "conscientiousness": 0.82,
    "extraversion": 0.68,
    "agreeableness": 0.71,
    "neuroticism": 0.35
  },
  "personality_summary": "一句话性格概括",
  "strengths": ["性格优势1", "性格优势2"],
  "potential_concerns": ["潜在关注点1"],
  "work_style": "工作风格描述",
  "team_fit": "团队协作倾向",
  "detailed_analysis": "详细分析（100-200字）"
}
```

**大五人格维度说明**:
| 维度 | 英文 | 说明 | 分数解读 |
|-----|------|------|---------|
| 开放性 | openness | 对新经验的接受程度 | 高=创新，低=务实 |
| 尽责性 | conscientiousness | 责任心和自律程度 | 高=可靠，低=灵活 |
| 外向性 | extraversion | 社交活跃程度 | 高=外向，低=内敛 |
| 宜人性 | agreeableness | 合作性和同理心 | 高=随和，低=独立 |
| 神经质 | neuroticism | 情绪稳定性（反向） | 高=敏感，低=稳定 |

#### 可信度分析 (CredibilityAnalysis)

```json
{
  "overall_score": 0.85,
  "level": "高可信度",
  "low_credibility_responses": [
    {
      "text": "低可信度回答内容...",
      "deception_score": 0.72,
      "confidence": 0.88
    }
  ],
  "high_credibility_responses": [
    {
      "text": "高可信度回答内容...",
      "deception_score": 0.08,
      "confidence": 0.92
    }
  ],
  "analysis": "面试整体可信度为 85.0%，属于高可信度。"
}
```

**可信度等级**:
| overall_score | level | 说明 |
|---------------|-------|------|
| ≥0.8 | 高可信度 | 回答真实可信 |
| 0.6-0.8 | 中等可信度 | 部分回答需核实 |
| <0.6 | 低可信度 | 存在较多不实陈述 |

#### 抑郁风险分析 (DepressionAnalysis)

```json
{
  "overall_score": 18.5,
  "level": "low",
  "level_label": "低风险",
  "level_distribution": {
    "low": 45,
    "medium": 5,
    "high": 0
  },
  "interpretation": "候选人在面试过程中整体心理状态良好，未发现明显的抑郁倾向。"
}
```

**抑郁风险等级**:
| level | level_label | 说明 |
|-------|-------------|------|
| low | 低风险 | 心理状态良好 |
| medium | 中等风险 | 存在一定压力或情绪波动 |
| high | 高风险 | 表现出明显的负面情绪 |

---

## 四、错误处理

### 常见错误

| HTTP 状态码 | 错误信息 | 处理建议 |
|------------|---------|---------|
| 400 | LLM服务未配置 | 检查后端 LLM API Key 配置 |
| 404 | 应聘申请不存在 | 检查 application_id 是否正确 |
| 404 | 综合分析不存在 | 检查 analysis_id 是否正确 |

### 错误响应格式

```json
{
  "success": false,
  "code": 400,
  "message": "LLM服务未配置，请检查API Key",
  "data": null
}
```

---

## 五、注意事项

### 数据依赖

1. **沉浸式面试会话必须已完成**
   - `is_completed=true`
   - `final_analysis` 字段必须包含 `conversation_history`

2. **如果没有沉浸式面试数据**
   - 分析仍会执行，但心理分析部分将为空
   - 五维度评估基于简历和初筛报告进行

### 重新分析

- 对同一个 `application_id` 重复调用 `POST /api/v1/analysis` 会更新已有分析记录
- 不会创建重复的分析记录

### 性能考虑

- 综合分析涉及多次 AI 调用，耗时约 10-30 秒
- 建议前端显示加载状态

---

**版本**: v2.0 (重构版)  
**更新时间**: 2025-01-18  
**维护者**: HRM2 开发团队
