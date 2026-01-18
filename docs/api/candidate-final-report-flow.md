# 候选人最终报告生成流程指南

> **版本**: v1.0  
> **更新日期**: 2025-01-18  
> **适用场景**: 前端从候选人信息出发，查找沉浸式面试记录并生成最终分析报告

---

## 一、核心流程概览

```
候选人/申请 ID
      │
      ▼
┌─────────────────────────────────────┐
│ 1. 检查是否存在已完成的沉浸式面试    │
│    GET /api/v1/immersive            │
│    ?application_id=xxx&is_completed │
└─────────────────────────────────────┘
      │
      ├── 不存在 → 提示"请先完成沉浸式面试"
      │
      ▼ 存在
┌─────────────────────────────────────┐
│ 2. 创建/更新综合分析报告             │
│    POST /api/v1/analysis            │
│    {"application_id": "xxx"}        │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│ 3. 展示最终推荐报告                  │
│    - 综合得分与推荐等级              │
│    - 五维度评估                      │
│    - 心理分析                        │
│    - 综合报告                        │
└─────────────────────────────────────┘
```

---

## 二、详细步骤

### 步骤 1: 获取候选人的 application_id

在进入"最终报告"页面前，前端需要持有当前候选人的 `application_id`。

**常见入口**:
- 从候选人列表页点击进入
- 从面试管理页面跳转
- URL 参数传递

```typescript
// 示例：从路由获取
const applicationId = route.params.applicationId;
```

---

### 步骤 2: 检查沉浸式面试状态

调用接口检查该申请是否有已完成的沉浸式面试会话。

**接口**: 
```http
GET /api/v1/immersive?application_id={application_id}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "session_abc123",
        "application_id": "app_xyz",
        "is_completed": true,
        "is_recording": false,
        "duration_seconds": 1800,
        "created_at": "2025-01-18T14:00:00"
      }
    ],
    "total": 1
  }
}
```

**前端处理逻辑**:

```typescript
async function checkImmersiveStatus(applicationId: string) {
  const response = await api.get('/api/v1/immersive', {
    params: { application_id: applicationId }
  });
  
  const sessions = response.data.items || [];
  
  // 查找已完成的会话
  const completedSession = sessions.find(s => s.is_completed === true);
  
  if (!completedSession) {
    // 情况1: 没有沉浸式面试记录
    if (sessions.length === 0) {
      return { 
        status: 'no_session', 
        message: '该候选人尚未进行沉浸式面试，请先创建面试会话' 
      };
    }
    
    // 情况2: 有会话但未完成
    const activeSession = sessions.find(s => !s.is_completed);
    if (activeSession) {
      return { 
        status: 'in_progress', 
        message: '沉浸式面试尚未完成，请先完成面试',
        sessionId: activeSession.id
      };
    }
  }
  
  // 情况3: 有已完成的会话
  return { 
    status: 'completed', 
    sessionId: completedSession.id,
    session: completedSession
  };
}
```

**UI 处理**:

| 状态 | UI 展示 |
|-----|---------|
| `no_session` | 显示空状态，提供"开始沉浸式面试"按钮 |
| `in_progress` | 显示"面试进行中"，提供"继续面试"按钮 |
| `completed` | 显示"生成最终报告"按钮 |

---

### 步骤 3: 生成综合分析报告

当沉浸式面试已完成，调用分析接口生成报告。

**接口**:
```http
POST /api/v1/analysis
Content-Type: application/json

{
  "application_id": "app_xyz"
}
```

**重要说明**:
- 该接口耗时 **10-30 秒**，需要显示加载状态
- 如果已存在分析记录，会更新而非创建新记录
- 后端会自动从 `final_analysis.conversation_history` 获取面试数据

**前端实现**:

```typescript
async function generateFinalReport(applicationId: string) {
  try {
    // 1. 显示加载状态
    setLoading(true);
    setLoadingText('正在执行 AI 综合分析，请稍候...');
    
    // 2. 调用分析接口（设置较长超时）
    const response = await api.post('/api/v1/analysis', 
      { application_id: applicationId },
      { timeout: 60000 }  // 60秒超时
    );
    
    if (response.success) {
      // 3. 保存分析结果
      setAnalysisData(response.data);
      showMessage('综合分析报告生成成功');
      return response.data;
    }
  } catch (error) {
    // 4. 错误处理
    if (error.message?.includes('LLM服务未配置')) {
      showError('AI 服务未配置，请联系管理员');
    } else if (error.code === 'TIMEOUT') {
      showError('分析超时，请重试');
    } else {
      showError(error.message || '生成报告失败');
    }
  } finally {
    setLoading(false);
  }
}
```

**响应数据结构**:

```json
{
  "success": true,
  "data": {
    "id": "analysis_001",
    "application_id": "app_xyz",
    "final_score": 78.5,
    "recommendation_level": "推荐录用",
    "recommendation_reason": "推荐录用",
    "suggested_action": "符合要求，可以录用",
    
    "dimension_scores": {
      "professional_competency": { ... },
      "work_experience": { ... },
      "soft_skills": { ... },
      "cultural_fit": { ... },
      "interview_performance": { ... }
    },
    
    "report": "## 综合分析报告\n...",
    
    "input_snapshot": {
      "position": "高级软件工程师",
      "candidate": "张三",
      "psychological_analysis": {
        "big_five": { ... },
        "credibility": { ... },
        "depression": { ... }
      },
      "immersive_session_id": "session_abc123"
    },
    
    "candidate_name": "张三",
    "position_title": "高级软件工程师"
  }
}
```

---

### 步骤 4: 查询已有分析报告（可选）

如果只需要查看已生成的报告，无需重新生成：

**按 application_id 查询**:
```http
GET /api/v1/analysis?application_id={application_id}
```

**按 analysis_id 查询**:
```http
GET /api/v1/analysis/{analysis_id}
```

```typescript
async function getExistingReport(applicationId: string) {
  const response = await api.get('/api/v1/analysis', {
    params: { application_id: applicationId }
  });
  
  const items = response.data.items || [];
  return items.length > 0 ? items[0] : null;
}
```

---

## 三、完整页面流程示例

```typescript
// 最终报告页面组件
async function FinalReportPage({ applicationId }) {
  const [status, setStatus] = useState('loading');
  const [analysis, setAnalysis] = useState(null);
  const [immersiveSession, setImmersiveSession] = useState(null);
  
  useEffect(() => {
    initPage();
  }, [applicationId]);
  
  async function initPage() {
    // 1. 检查沉浸式面试状态
    const immersiveStatus = await checkImmersiveStatus(applicationId);
    
    if (immersiveStatus.status !== 'completed') {
      setStatus(immersiveStatus.status);
      return;
    }
    
    setImmersiveSession(immersiveStatus.session);
    
    // 2. 检查是否已有分析报告
    const existingReport = await getExistingReport(applicationId);
    
    if (existingReport) {
      setAnalysis(existingReport);
      setStatus('has_report');
    } else {
      setStatus('ready_to_generate');
    }
  }
  
  async function handleGenerateReport() {
    setStatus('generating');
    const result = await generateFinalReport(applicationId);
    if (result) {
      setAnalysis(result);
      setStatus('has_report');
    } else {
      setStatus('ready_to_generate');
    }
  }
  
  // 渲染逻辑
  switch (status) {
    case 'loading':
      return <Loading text="加载中..." />;
      
    case 'no_session':
      return (
        <EmptyState 
          message="该候选人尚未进行沉浸式面试"
          action={<Button onClick={goToCreateSession}>开始沉浸式面试</Button>}
        />
      );
      
    case 'in_progress':
      return (
        <EmptyState 
          message="沉浸式面试尚未完成"
          action={<Button onClick={goToContinueSession}>继续面试</Button>}
        />
      );
      
    case 'ready_to_generate':
      return (
        <div>
          <SessionInfo session={immersiveSession} />
          <Button onClick={handleGenerateReport} type="primary">
            生成最终推荐报告
          </Button>
        </div>
      );
      
    case 'generating':
      return <Loading text="AI 正在分析中，预计需要 10-30 秒..." />;
      
    case 'has_report':
      return (
        <FinalReportView 
          analysis={analysis}
          onRegenerate={handleGenerateReport}
        />
      );
  }
}
```

---

## 四、接口调用时序图

```
┌─────────┐                                         ┌─────────┐
│  前端   │                                         │  后端   │
└────┬────┘                                         └────┬────┘
     │                                                   │
     │  1. 进入最终报告页面                               │
     │                                                   │
     │  GET /api/v1/immersive?application_id=xxx         │
     │──────────────────────────────────────────────────>│
     │<──────────────────────────────────────────────────│
     │  返回沉浸式面试会话列表                            │
     │                                                   │
     │  [检查是否有已完成的会话]                          │
     │                                                   │
     │  ───── 如果没有已完成会话 ─────                    │
     │  显示"请先完成沉浸式面试"                          │
     │                                                   │
     │  ───── 如果有已完成会话 ─────                      │
     │                                                   │
     │  2. (可选) 检查是否已有分析报告                    │
     │  GET /api/v1/analysis?application_id=xxx          │
     │──────────────────────────────────────────────────>│
     │<──────────────────────────────────────────────────│
     │                                                   │
     │  ───── 如果已有报告 ─────                          │
     │  直接展示报告                                      │
     │                                                   │
     │  ───── 如果没有报告 ─────                          │
     │                                                   │
     │  3. 用户点击"生成报告"                             │
     │  POST /api/v1/analysis                            │
     │  {"application_id": "xxx"}                        │
     │──────────────────────────────────────────────────>│
     │                                                   │
     │        [显示加载中... 10-30秒]                     │
     │                                                   │
     │<──────────────────────────────────────────────────│
     │  返回完整分析结果                                  │
     │                                                   │
     │  4. 展示最终推荐报告                              │
     │  - 综合得分与推荐等级                             │
     │  - 五维度雷达图                                   │
     │  - 心理分析卡片                                   │
     │  - Markdown 报告                                  │
     │                                                   │
```

---

## 五、接口汇总

| 步骤 | 接口 | 方法 | 用途 |
|-----|------|------|------|
| 检查沉浸式面试 | `/api/v1/immersive` | GET | 查询是否有已完成的会话 |
| 查询已有报告 | `/api/v1/analysis` | GET | 检查是否已生成过报告 |
| **生成报告** | `/api/v1/analysis` | **POST** | **核心：生成最终推荐报告** |
| 查看报告详情 | `/api/v1/analysis/{id}` | GET | 获取单个报告详情 |

---

## 六、常见问题

### Q1: 为什么需要先检查沉浸式面试状态？

分析报告依赖沉浸式面试的 `conversation_history` 数据。如果没有完成面试，则：
- 心理分析部分（大五人格、可信度、抑郁风险）将为空
- 五维度评估中的"面试表现"维度无数据支撑

### Q2: 重复调用 POST /api/v1/analysis 会发生什么？

会更新已有的分析记录，不会创建新记录。适用于"重新分析"功能。

### Q3: 如何判断报告是否需要更新？

比较 `analysis.updated_at` 与 `immersive_session.updated_at`：
- 如果面试数据更新时间晚于报告，建议重新生成

### Q4: 生成报告超时怎么办？

1. 前端设置 60 秒超时
2. 提示用户"分析超时，请重试"
3. 后端日志检查 LLM 服务状态

---

## 七、数据关联关系

```
Application (应聘申请)
    │
    ├── Resume (简历)
    │
    ├── ImmersiveSession (沉浸式面试)
    │       │
    │       └── final_analysis.conversation_history
    │               │
    │               └── candidate_scores (big_five, deception, depression)
    │
    └── ComprehensiveAnalysis (综合分析)
            │
            ├── dimension_scores (五维度评估)
            │
            └── input_snapshot.psychological_analysis (心理分析)
```

**关键字段**:
- `application_id`: 贯穿所有表的核心关联字段
- `final_analysis`: 沉浸式面试完成时保存的数据快照
- `conversation_history`: 面试对话记录（含心理评分）

---

**文档结束**
