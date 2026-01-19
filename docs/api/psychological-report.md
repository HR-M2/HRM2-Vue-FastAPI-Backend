# 心理分析报告模块 API 文档

> **版本**: v1.0  
> **更新日期**: 2026-01-19  
> **模块说明**: 基于沉浸式面试数据生成心理分析报告

---

## 一、模块概述

### 1.1 功能说明

心理分析报告模块用于对沉浸式面试会话的心理数据进行深度分析，生成结构化的心理评估报告。

**核心特点**：
- 每个面试会话（ImmersiveSession）绑定一份心理报告（1:1 关系）
- 报告**不会自动生成**，需用户在"最终推荐"界面主动点击生成
- 支持**重新生成**（覆盖旧报告）
- 基于 AI Agent 进行深度分析

### 1.2 数据来源

| 数据类型 | 来源 | 说明 |
|---------|------|------|
| 大五人格 | `conversation_history[].candidate_scores.big_five` | 各维度 0-1 |
| 欺骗检测 | `conversation_history[].candidate_scores.deception` | score 0-1 |
| 抑郁风险 | `conversation_history[].candidate_scores.depression` | score 0-100 |
| 发言模式 | `statistics.speaking_ratio`, `statistics.char_count` | 统计数据 |

### 1.3 数据关系

```
Application (应聘申请)
    │
    ├── ImmersiveSession (沉浸式面试会话)
    │       │
    │       └── PsychologicalReport (心理分析报告) [1:1]
    │
    └── ComprehensiveAnalysis (综合分析)
```

---

## 二、API 接口列表

| 接口 | 方法 | 说明 |
|-----|------|------|
| `/api/v1/psychological/{session_id}/generate` | POST | 生成心理分析报告 |
| `/api/v1/psychological/{session_id}` | GET | 获取心理分析报告 |
| `/api/v1/psychological/by-application/{application_id}` | GET | 按申请ID获取报告 |
| `/api/v1/psychological/{session_id}/exists` | GET | 检查报告是否存在 |
| `/api/v1/psychological/{session_id}` | DELETE | 删除心理分析报告 |

---

## 三、接口详细说明

### 3.1 生成心理分析报告

生成或更新面试会话的心理分析报告。

#### 请求

```
POST /api/v1/psychological/{session_id}/generate
```

#### 路径参数

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| session_id | string | 是 | 沉浸式面试会话ID |

#### 前置条件

- 面试会话必须**已完成**（`is_completed = true`）
- 面试会话必须有**对话记录**（`conversation_history` 非空）

#### 响应

```json
{
  "code": 200,
  "message": "心理分析报告生成成功",
  "data": {
    "id": "report-uuid",
    "session_id": "session-uuid",
    "application_id": "app-uuid",
    
    "big_five_scores": {
      "openness": 0.62,
      "conscientiousness": 0.71,
      "extraversion": 0.55,
      "agreeableness": 0.68,
      "neuroticism": 0.32
    },
    "big_five_analysis": {
      "scores": {
        "openness": 0.62,
        "conscientiousness": 0.71,
        "extraversion": 0.55,
        "agreeableness": 0.68,
        "neuroticism": 0.32
      },
      "personality_type": "外向开放型",
      "strengths": ["创新思维", "团队协作能力强", "沟通表达流畅"],
      "potential_concerns": ["可能过于乐观估计项目难度", "需关注细节把控"],
      "work_style": "适合创意型、协作型工作环境",
      "team_fit": "适合跨部门协作，能有效调动团队氛围"
    },
    
    "deception_score": 0.15,
    "deception_analysis": {
      "overall_score": 0.15,
      "credibility_level": "high",
      "suspicious_responses": [],
      "analysis_summary": "候选人回答真实可信，表达自然，无明显欺骗迹象"
    },
    
    "depression_score": 12.5,
    "depression_level": "low",
    "depression_analysis": {
      "average_score": 12.5,
      "risk_level": "low",
      "trend": "stable",
      "high_risk_moments": [],
      "interpretation": "情绪状态稳定，心理健康状况良好，无需特别关注"
    },
    
    "speech_pattern_analysis": {
      "speaking_ratio": 0.64,
      "total_chars": 3200,
      "avg_response_length": 114.3,
      "response_count": 28,
      "communication_style": "表达流畅，逻辑清晰，善于举例说明",
      "fluency_assessment": "语言组织能力强，回答有条理",
      "confidence_level": "high"
    },
    
    "overall_score": 85.0,
    "risk_level": "low",
    "overall_summary": "候选人心理状态良好，人格特质与岗位要求匹配度高。具备较强的开放性和外向性，善于沟通协作。可信度高，抑郁风险低，情绪稳定。建议进入下一轮评估。",
    "recommendations": [
      "可安排团队协作类面试进一步考察",
      "关注候选人在高压场景下的表现",
      "建议与直属团队进行文化契合度沟通"
    ],
    
    "report_markdown": "# 心理分析报告\n\n## 一、候选人概述\n...",
    
    "created_at": "2026-01-19T14:00:00",
    "updated_at": "2026-01-19T14:00:00"
  }
}
```

#### 错误码

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 404 | 未找到已完成的面试会话 | session_id 无效或会话未完成 |
| 400 | 面试会话无对话记录 | conversation_history 为空 |
| 400 | 心理分析生成失败 | AI 分析异常 |

#### 耗时说明

- 预计耗时：**10-30 秒**
- 建议前端设置 **60 秒超时**
- 显示 Loading 状态提示用户等待

---

### 3.2 获取心理分析报告

获取已生成的心理分析报告。

#### 请求

```
GET /api/v1/psychological/{session_id}
```

#### 路径参数

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| session_id | string | 是 | 沉浸式面试会话ID |

#### 响应

与 3.1 相同。

#### 错误码

| HTTP状态码 | 错误信息 | 说明 |
|-----------|---------|------|
| 404 | 未找到该面试会话的心理分析报告 | 报告不存在，需先生成 |

---

### 3.3 按申请ID获取报告

根据应聘申请ID获取最新的心理分析报告。

#### 请求

```
GET /api/v1/psychological/by-application/{application_id}
```

#### 路径参数

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| application_id | string | 是 | 应聘申请ID |

#### 响应

与 3.1 相同。

---

### 3.4 检查报告是否存在

检查心理分析报告是否已生成，用于前端判断是否显示"生成报告"或"查看报告"按钮。

#### 请求

```
GET /api/v1/psychological/{session_id}/exists
```

#### 响应

```json
{
  "code": 200,
  "data": {
    "exists": true,
    "report_id": "report-uuid",
    "created_at": "2026-01-19T14:00:00"
  }
}
```

| 字段 | 类型 | 说明 |
|-----|------|------|
| exists | boolean | 报告是否存在 |
| report_id | string/null | 报告ID（存在时返回） |
| created_at | datetime/null | 创建时间（存在时返回） |

---

### 3.5 删除心理分析报告

删除心理分析报告。

#### 请求

```
DELETE /api/v1/psychological/{session_id}
```

#### 响应

```json
{
  "code": 200,
  "message": "心理分析报告已删除"
}
```

---

## 四、数据结构详解

### 4.1 大五人格 (Big Five)

| 维度 | 英文 | 数值范围 | 高分特征 | 低分特征 |
|-----|------|---------|---------|---------|
| 开放性 | openness | 0-1 | 创意、好奇、想象力丰富 | 务实、传统、专注 |
| 尽责性 | conscientiousness | 0-1 | 有组织、可靠、勤奋 | 灵活、随性、即兴 |
| 外向性 | extraversion | 0-1 | 健谈、活力充沛、自信 | 内敛、独立、深思 |
| 宜人性 | agreeableness | 0-1 | 友善、信任他人、乐于助人 | 客观、直接、竞争 |
| 神经质 | neuroticism | 0-1 | 敏感、情绪波动、焦虑 | 稳定、冷静、抗压 |

### 4.2 欺骗检测 (Deception)

| 字段 | 类型 | 说明 |
|-----|------|------|
| overall_score | float | 整体欺骗分数 (0-1)，**越低越可信** |
| credibility_level | string | 可信度等级：`high`/`medium`/`low` |
| suspicious_responses | array | 可疑回答列表（如有） |
| analysis_summary | string | 分析总结 |

**可信度等级判定**：

| 等级 | 分数范围 | 说明 |
|-----|---------|------|
| high | 0 - 0.3 | 高可信度 |
| medium | 0.3 - 0.6 | 中等可信度，建议关注 |
| low | 0.6 - 1.0 | 低可信度，需重点核实 |

### 4.3 抑郁风险 (Depression)

| 字段 | 类型 | 说明 |
|-----|------|------|
| average_score | float | 平均抑郁分数 (0-100) |
| risk_level | string | 风险等级：`low`/`medium`/`high` |
| trend | string | 趋势：`stable`/`increasing`/`decreasing` |
| high_risk_moments | array | 高风险时刻列表（如有） |
| interpretation | string | 解读说明 |

**风险等级判定**：

| 等级 | 分数范围 | 说明 |
|-----|---------|------|
| low | 0 - 30 | 低风险，情绪稳定 |
| medium | 30 - 60 | 中等风险，需关注 |
| high | 60 - 100 | 高风险，建议专业评估 |

### 4.4 发言模式 (Speech Pattern)

| 字段 | 类型 | 说明 |
|-----|------|------|
| speaking_ratio | float | 候选人发言占比 (0-1) |
| total_chars | int | 候选人总字数 |
| avg_response_length | float | 平均回答长度（字） |
| response_count | int | 回答次数 |
| communication_style | string | 沟通风格描述 |
| fluency_assessment | string | 流畅度评估 |
| confidence_level | string | 自信程度：`high`/`medium`/`low` |

### 4.5 综合评估

| 字段 | 类型 | 说明 |
|-----|------|------|
| overall_score | float | 心理健康综合评分 (0-100) |
| risk_level | string | 综合风险等级：`low`/`medium`/`high` |
| overall_summary | string | 综合评估摘要 (100-200字) |
| recommendations | array | 建议列表 |
| report_markdown | string | Markdown 格式完整报告 |

---

## 五、前端对接指南

### 5.1 页面流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        最终推荐页面                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  1. 页面加载时                                             │ │
│  │     ↓                                                      │ │
│  │     检查报告是否存在                                        │ │
│  │     GET /api/v1/psychological/{session_id}/exists          │ │
│  │     ↓                                                      │ │
│  │     ├── exists=true: 显示"查看心理报告"按钮                │ │
│  │     └── exists=false: 显示"生成心理报告"按钮               │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  2. 用户点击"生成心理报告"                                 │ │
│  │     ↓                                                      │ │
│  │     显示 Loading（提示：正在分析心理数据，预计需要10-30秒） │ │
│  │     ↓                                                      │ │
│  │     POST /api/v1/psychological/{session_id}/generate       │ │
│  │     ↓                                                      │ │
│  │     显示心理分析报告                                        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  3. 报告展示                                               │ │
│  │     - 综合评分 + 风险等级（卡片）                          │ │
│  │     - 大五人格雷达图                                       │ │
│  │     - 可信度评估                                           │ │
│  │     - 抑郁风险指示器                                       │ │
│  │     - 发言模式统计                                         │ │
│  │     - 完整报告（Markdown 渲染）                            │ │
│  │     - [重新生成] 按钮                                      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 代码示例

#### 检查报告是否存在

```javascript
async function checkReportExists(sessionId) {
  const response = await axios.get(
    `/api/v1/psychological/${sessionId}/exists`
  );
  return response.data.data;
}

// 使用示例
const { exists, report_id, created_at } = await checkReportExists(sessionId);
if (exists) {
  showViewReportButton();
} else {
  showGenerateReportButton();
}
```

#### 生成心理分析报告

```javascript
async function generatePsychologicalReport(sessionId) {
  // 显示加载状态
  showLoading('正在分析心理数据，预计需要 10-30 秒...');
  
  try {
    const response = await axios.post(
      `/api/v1/psychological/${sessionId}/generate`,
      {},
      { timeout: 60000 }  // 60秒超时
    );
    
    const report = response.data.data;
    displayReport(report);
    
  } catch (error) {
    if (error.response?.status === 404) {
      showError('面试会话不存在或未完成');
    } else if (error.response?.status === 400) {
      showError(error.response.data.message);
    } else {
      showError('生成失败，请重试');
    }
  } finally {
    hideLoading();
  }
}
```

#### 获取心理分析报告

```javascript
async function getPsychologicalReport(sessionId) {
  try {
    const response = await axios.get(
      `/api/v1/psychological/${sessionId}`
    );
    return response.data.data;
  } catch (error) {
    if (error.response?.status === 404) {
      return null;  // 报告不存在
    }
    throw error;
  }
}
```

#### 展示报告

```javascript
function displayReport(report) {
  // 1. 综合评分卡片
  console.log('综合评分:', report.overall_score);
  console.log('风险等级:', report.risk_level);
  
  // 2. 大五人格雷达图数据
  const bigFiveData = report.big_five_scores;
  // { openness: 0.62, conscientiousness: 0.71, ... }
  
  // 3. 可信度
  console.log('可信度:', report.deception_analysis.credibility_level);
  
  // 4. 抑郁风险
  console.log('抑郁分数:', report.depression_score);
  console.log('风险等级:', report.depression_level);
  
  // 5. 发言模式
  console.log('发言占比:', report.speech_pattern_analysis.speaking_ratio);
  
  // 6. 建议列表
  report.recommendations.forEach(rec => console.log('- ', rec));
  
  // 7. 完整报告 (Markdown)
  const reportHtml = marked(report.report_markdown);
  document.getElementById('report-content').innerHTML = reportHtml;
}
```

### 5.3 UI 组件建议

#### 综合评分卡片

```
┌─────────────────────────────────────┐
│  心理健康评分                        │
│                                     │
│         ╭───────────╮               │
│         │    85     │               │
│         │   /100    │               │
│         ╰───────────╯               │
│                                     │
│     风险等级: 🟢 低风险              │
│                                     │
└─────────────────────────────────────┘
```

#### 大五人格雷达图

```
            开放性 0.62
               ▲
              /│\
             / │ \
    神经质  /  │  \  尽责性
     0.32 ◄───┼───► 0.71
             \ │ /
              \│/
               ▼
           外向性 0.55
           
        宜人性 0.68
```

#### 可信度指示器

```
┌─────────────────────────────────────┐
│  可信度评估                          │
│                                     │
│  ████████████░░░░░░░░ 85%           │
│                                     │
│  等级: 🟢 高可信度                   │
│  分析: 候选人回答真实可信            │
└─────────────────────────────────────┘
```

#### 抑郁风险指示器

```
┌─────────────────────────────────────┐
│  抑郁风险评估                        │
│                                     │
│  低风险 ●────────○─────────○ 高风险  │
│         ▲                           │
│      12.5分                         │
│                                     │
│  趋势: 稳定                          │
│  解读: 情绪状态稳定，心理健康良好     │
└─────────────────────────────────────┘
```

---

## 六、注意事项

### 6.1 隐私与伦理

- 心理分析结果**仅供参考**，不构成临床诊断
- 请勿将分析结果作为唯一的录用依据
- 注意保护候选人隐私，避免敏感数据泄露
- 高风险结果应由专业人员进一步评估

### 6.2 数据依赖

- 报告质量依赖于面试过程中采集的心理数据
- 如果面试时未采集心理评分，报告内容可能不完整
- 建议面试时长至少 **15 分钟**以获取足够数据

### 6.3 重新生成

- 支持重新生成，新报告会**覆盖**旧报告
- 重新生成会使用最新的面试数据
- 建议在面试数据更新后重新生成

---

## 七、常见问题

### Q1: 报告生成失败怎么办？

检查以下条件：
1. 面试会话是否已完成（调用过 `/complete` 接口）
2. 面试会话是否有对话记录
3. LLM 服务是否正常

### Q2: 报告内容不准确怎么办？

1. 检查面试时采集的心理评分是否准确
2. 尝试重新生成报告
3. 心理分析仅供参考，建议结合其他评估维度

### Q3: 如何获取 session_id？

1. 从面试记录查询接口获取：`GET /api/v1/immersive/by-application/{application_id}/record`
2. 返回数据中的 `id` 字段即为 `session_id`

### Q4: 与综合分析（ComprehensiveAnalysis）的区别？

| 模块 | 心理分析报告 | 综合分析 |
|-----|------------|---------|
| 关注点 | 心理特征评估 | 全面的录用建议 |
| 数据来源 | 心理评分数据 | 简历 + 面试 + 心理 |
| 输出 | 心理画像 + 风险评估 | 推荐等级 + 综合报告 |
| 生成时机 | 最终推荐-点击生成 | 最终推荐-点击生成 |
