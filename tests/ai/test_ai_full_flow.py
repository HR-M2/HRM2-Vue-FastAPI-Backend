"""
AI服务完整流程单元测试

测试整个招聘AI流程：
1. 岗位AI要求生成 (PositionService)
2. 简历筛选 (ScreeningAgentManager) 
3. 面试问答 (InterviewService)
4. 综合分析 (AnalysisService)

注意：这些测试会调用真实的LLM服务，运行时间较长
"""
import asyncio
import logging
import pytest
from typing import Dict, Any, List

from app.agents.position import PositionService, get_position_service
from app.agents.screening import ScreeningAgentManager
from app.agents.interview import InterviewService
from app.agents.analysis import AnalysisService
from app.agents.llm_client import get_llm_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 测试数据 ====================

SAMPLE_JOB_DESCRIPTION = """
招聘高级Python后端工程师

岗位职责：
1. 负责公司核心业务系统的后端开发和架构设计
2. 使用Python/FastAPI开发高性能Web服务
3. 负责数据库设计和性能优化
4. 参与代码审查和技术方案评审
5. 指导初级工程师的技术成长

任职要求：
1. 计算机相关专业本科及以上学历
2. 5年以上Python开发经验
3. 熟练掌握FastAPI、Django等Web框架
4. 精通MySQL、Redis、MongoDB等数据库
5. 有微服务架构设计和实施经验
6. 具备良好的沟通能力和团队协作精神
"""

SAMPLE_RESUME_CONTENT = """
姓名：张三
联系电话：13800138000
邮箱：zhangsan@example.com

教育背景：
- 2015-2019 北京大学 计算机科学与技术 本科

工作经历：

1. 2021.06 - 至今 | ABC科技有限公司 | 高级后端工程师
   - 主导公司电商平台后端架构重构，从单体应用迁移至微服务架构
   - 使用Python/FastAPI开发核心订单系统，日处理订单量100万+
   - 设计并实现分布式缓存方案，将接口响应时间从500ms降低到50ms
   - 负责MySQL数据库性能优化，查询效率提升80%
   - 带领5人团队完成多个重要项目交付

2. 2019.07 - 2021.05 | XYZ互联网公司 | Python开发工程师
   - 参与公司内部管理系统开发，使用Django框架
   - 负责API接口开发和单元测试编写
   - 参与数据库表结构设计和SQL优化

技能特长：
- 编程语言：Python（精通）、Go（熟悉）、JavaScript（了解）
- Web框架：FastAPI（精通）、Django（熟练）、Flask（熟练）
- 数据库：MySQL（精通）、Redis（精通）、MongoDB（熟悉）
- 中间件：RabbitMQ、Kafka、Elasticsearch
- 容器化：Docker、Kubernetes
- 其他：Git、Linux、CI/CD

项目经验：

1. 电商订单系统重构（2022.01 - 2022.12）
   - 项目背景：原有单体架构无法支撑业务增长
   - 技术方案：采用微服务架构，FastAPI + MySQL + Redis + RabbitMQ
   - 主要贡献：负责架构设计和核心模块开发
   - 项目成果：系统吞吐量提升10倍，可用性达到99.99%

2. 实时数据分析平台（2021.01 - 2021.06）
   - 项目背景：为运营提供实时业务数据分析能力
   - 技术方案：Kafka + Flink + ClickHouse + Grafana
   - 主要贡献：负责数据采集和实时计算模块开发
   - 项目成果：实现秒级数据更新，支撑日均10亿条数据处理

自我评价：
具有扎实的编程基础和丰富的项目经验，对技术有热情，持续学习新技术。
具备良好的沟通能力和团队协作意识，能够承担压力并按时交付高质量代码。
"""


# ==================== Fixtures ====================

@pytest.fixture(scope="module")
def event_loop():
    """创建事件循环（模块级共享）"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def llm_client():
    """获取LLM客户端"""
    client = get_llm_client()
    if not client.is_configured():
        pytest.skip("LLM服务未配置，跳过AI测试")
    return client


@pytest.fixture(scope="module")
def position_service():
    """获取岗位AI服务"""
    return get_position_service()


@pytest.fixture(scope="module")
def job_config() -> Dict[str, Any]:
    """标准岗位配置"""
    return {
        "title": "高级Python后端工程师",
        "description": SAMPLE_JOB_DESCRIPTION,
        "requirements": {
            "required_skills": ["Python", "FastAPI", "MySQL", "Redis"],
            "optional_skills": ["Docker", "Kubernetes", "微服务"],
            "min_experience": 5,
            "education": ["本科", "硕士"],
        },
        "salary_range": [25000, 40000],
    }


@pytest.fixture(scope="module")
def interview_service(job_config: Dict[str, Any]):
    """获取面试服务"""
    return InterviewService(job_config=job_config)


@pytest.fixture(scope="module")
def analysis_service(job_config: Dict[str, Any]):
    """获取综合分析服务"""
    return AnalysisService(job_config=job_config)


# ==================== 测试类 ====================

class TestAIFullFlow:
    """AI服务完整流程测试"""

    # 存储中间结果供后续测试使用
    generated_position: Dict[str, Any] = {}
    screening_result: Dict[str, Any] = {}
    interview_questions: List[Dict[str, Any]] = []
    interview_messages: List[Dict[str, Any]] = []
    interview_report: Dict[str, Any] = {}
    comprehensive_result: Dict[str, Any] = {}

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_01_position_ai_generate(self, position_service: PositionService, llm_client):
        """测试1：AI生成岗位要求"""
        logger.info("=" * 60)
        logger.info("测试1：AI生成岗位要求")
        logger.info("=" * 60)

        result = await position_service.generate_position_requirements(
            description=SAMPLE_JOB_DESCRIPTION
        )

        # 验证必要字段
        assert "position" in result, "生成结果缺少 position 字段"
        assert "required_skills" in result, "生成结果缺少 required_skills 字段"
        assert isinstance(result["required_skills"], list), "required_skills 应为列表"
        assert len(result["required_skills"]) > 0, "required_skills 不应为空"

        # 验证其他字段
        assert "optional_skills" in result, "生成结果缺少 optional_skills 字段"
        assert "min_experience" in result, "生成结果缺少 min_experience 字段"
        assert "education" in result, "生成结果缺少 education 字段"
        assert "salary_range" in result, "生成结果缺少 salary_range 字段"

        # 存储结果
        TestAIFullFlow.generated_position = result

        logger.info("生成的岗位要求：")
        logger.info(f"  - 岗位名称: {result.get('position')}")
        logger.info(f"  - 必备技能: {result.get('required_skills')}")
        logger.info(f"  - 可选技能: {result.get('optional_skills')}")
        logger.info(f"  - 最低经验: {result.get('min_experience')}年")
        logger.info(f"  - 学历要求: {result.get('education')}")
        logger.info(f"  - 薪资范围: {result.get('salary_range')}")
        logger.info("✓ 岗位AI要求生成测试通过")

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    async def test_02_screening_agents(self, llm_client):
        """测试2：简历筛选多代理流程"""
        logger.info("=" * 60)
        logger.info("测试2：简历筛选多代理流程")
        logger.info("=" * 60)

        # 使用生成的岗位要求或默认配置
        criteria = TestAIFullFlow.generated_position if TestAIFullFlow.generated_position else {
            "position": "高级Python后端工程师",
            "required_skills": ["Python", "FastAPI", "MySQL"],
            "optional_skills": ["Docker", "Kubernetes"],
            "min_experience": 5,
            "education": ["本科", "硕士"],
            "salary_range": [25000, 40000],
            "project_requirements": {
                "min_projects": 2,
                "team_lead_experience": True,
            }
        }

        # 确保有必要字段
        if "project_requirements" not in criteria:
            criteria["project_requirements"] = {
                "min_projects": 2,
                "team_lead_experience": True,
            }

        manager = ScreeningAgentManager(criteria=criteria)
        manager.setup()

        # 运行筛选流程
        messages = manager.run_screening(
            candidate_name="张三",
            resume_text=SAMPLE_RESUME_CONTENT
        )

        # 验证结果
        assert messages is not None, "筛选结果不应为空"
        assert len(messages) > 0, "筛选对话记录不应为空"

        # 存储结果
        TestAIFullFlow.screening_result = {
            "messages": messages,
            "speakers": manager.speakers,
        }

        logger.info(f"筛选流程完成，共 {len(messages)} 轮对话")
        logger.info(f"发言顺序: {manager.speakers}")

        # 输出关键信息
        for msg in messages:
            name = msg.get("name", "Unknown")
            content = msg.get("content", "")[:200]
            logger.info(f"  [{name}]: {content}...")

        logger.info("✓ 简历筛选测试通过")

    @pytest.mark.asyncio
    @pytest.mark.timeout(180)
    async def test_03_interview_generate_questions(self, interview_service: InterviewService, llm_client):
        """测试3：面试问题生成"""
        logger.info("=" * 60)
        logger.info("测试3：面试问题生成")
        logger.info("=" * 60)

        # 基于简历生成问题
        result = await interview_service.generate_initial_questions(
            resume_content=SAMPLE_RESUME_CONTENT,
            count=3,
            interest_point_count=2
        )

        # 验证结果
        assert "questions" in result, "结果缺少 questions 字段"
        assert "interest_points" in result, "结果缺少 interest_points 字段"

        questions = result["questions"]
        interest_points = result["interest_points"]

        assert len(questions) > 0, "生成的问题不应为空"

        # 存储问题
        TestAIFullFlow.interview_questions = questions

        logger.info(f"生成 {len(questions)} 个面试问题：")
        for i, q in enumerate(questions, 1):
            logger.info(f"  问题{i}: {q.get('question', '')[:100]}...")
            logger.info(f"    - 类别: {q.get('category')}")
            logger.info(f"    - 难度: {q.get('difficulty')}")
            logger.info(f"    - 考察技能: {q.get('expected_skills')}")

        logger.info(f"\n识别到 {len(interest_points)} 个兴趣点：")
        for i, p in enumerate(interest_points, 1):
            logger.info(f"  兴趣点{i}: {p.get('content', '')[:80]}...")

        logger.info("✓ 面试问题生成测试通过")

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    async def test_04_interview_simulate_and_evaluate(self, interview_service: InterviewService, llm_client, job_config: Dict[str, Any]):
        """测试4：模拟面试问答并评估"""
        logger.info("=" * 60)
        logger.info("测试4：模拟面试问答并评估")
        logger.info("=" * 60)

        questions = TestAIFullFlow.interview_questions
        if not questions:
            # 如果没有问题，生成一个默认问题
            questions = [{"question": "请介绍一下您在微服务架构方面的经验？", "difficulty": 6, "expected_skills": ["微服务", "架构设计"]}]

        messages: List[Dict[str, Any]] = []
        seq = 0

        # 模拟2轮问答
        for q in questions[:2]:
            question = q.get("question", "")
            difficulty = q.get("difficulty", 6)
            expected_skills = q.get("expected_skills", [])

            logger.info(f"\n--- 第{seq // 2 + 1}轮问答 ---")
            logger.info(f"面试官: {question}")

            # 记录问题
            seq += 1
            messages.append({
                "role": "interviewer",
                "content": question,
                "seq": seq
            })

            # 模拟候选人回答
            answer = await interview_service.simulate_candidate_answer(
                question=question,
                resume_content=SAMPLE_RESUME_CONTENT,
                position_title=job_config["title"],
                position_description=job_config["description"],
                candidate_name="张三",
                candidate_type="ideal",
                conversation_history=""
            )

            logger.info(f"候选人: {answer[:200]}...")

            # 记录回答
            seq += 1
            messages.append({
                "role": "candidate",
                "content": answer,
                "seq": seq
            })

        # 存储消息
        TestAIFullFlow.interview_messages = messages
        logger.info("✓ 模拟面试问答测试通过")

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_05_interview_final_report(self, interview_service: InterviewService, llm_client):
        """测试5：生成面试最终报告"""
        logger.info("=" * 60)
        logger.info("测试5：生成面试最终报告")
        logger.info("=" * 60)

        messages = TestAIFullFlow.interview_messages
        if not messages:
            pytest.skip("没有面试消息记录，跳过报告生成测试")

        report = await interview_service.generate_final_report(
            candidate_name="张三",
            messages=messages,
            hr_notes="候选人背景优秀，值得关注"
        )

        # 验证报告结构
        assert "overall_assessment" in report, "报告缺少 overall_assessment"
        overall = report["overall_assessment"]
        assert "recommendation_score" in overall, "缺少推荐分数"
        assert "recommendation" in overall, "缺少推荐建议"
        assert "summary" in overall, "缺少总结"

        # 存储报告
        TestAIFullFlow.interview_report = report

        logger.info("面试报告：")
        logger.info(f"  - 推荐分数: {overall.get('recommendation_score')}")
        logger.info(f"  - 推荐建议: {overall.get('recommendation')}")
        logger.info(f"  - 总结: {overall.get('summary')}")
        logger.info(f"  - 亮点: {report.get('highlights', [])}")
        logger.info(f"  - 风险点: {report.get('red_flags', [])}")
        logger.info(f"  - 过度自信检测: {report.get('overconfidence_detected')}")
        logger.info("✓ 面试报告生成测试通过")

    @pytest.mark.asyncio
    @pytest.mark.timeout(300)
    async def test_06_comprehensive_analysis(self, analysis_service: AnalysisService, llm_client):
        """测试6：综合分析评估"""
        logger.info("=" * 60)
        logger.info("测试6：综合分析评估")
        logger.info("=" * 60)

        # 准备筛选报告
        screening_report = {
            "comprehensive_score": 85,
            "screening_summary": "候选人具备丰富的Python开发经验，技术栈匹配度高"
        }

        # 使用之前的面试记录和报告
        interview_records = TestAIFullFlow.interview_messages or []
        interview_report = TestAIFullFlow.interview_report or {
            "overall_assessment": {
                "recommendation_score": 80,
                "recommendation": "推荐",
                "summary": "候选人表现良好"
            },
            "highlights": ["技术扎实", "沟通流畅"],
            "red_flags": []
        }

        # 进度回调
        progress_log = []
        def progress_callback(step: str, percent: int):
            progress_log.append((step, percent))
            logger.info(f"  进度: {step} - {percent}%")

        # 执行综合分析
        result = await analysis_service.analyze(
            candidate_name="张三",
            resume_content=SAMPLE_RESUME_CONTENT,
            screening_report=screening_report,
            interview_records=interview_records,
            interview_report=interview_report,
            video_analysis=None,
            progress_callback=progress_callback
        )

        # 验证结果结构
        assert "candidate_name" in result, "结果缺少 candidate_name"
        assert "final_score" in result, "结果缺少 final_score"
        assert "recommendation" in result, "结果缺少 recommendation"
        assert "dimension_scores" in result, "结果缺少 dimension_scores"
        assert "comprehensive_report" in result, "结果缺少 comprehensive_report"

        # 存储结果
        TestAIFullFlow.comprehensive_result = result

        logger.info("\n综合分析结果：")
        logger.info(f"  - 候选人: {result['candidate_name']}")
        logger.info(f"  - 最终得分: {result['final_score']}")
        logger.info(f"  - 推荐等级: {result['recommendation'].get('label')}")
        logger.info(f"  - 建议行动: {result['recommendation'].get('action')}")

        logger.info("\n各维度评分：")
        for dim_key, dim_data in result.get("dimension_scores", {}).items():
            logger.info(f"  - {dim_data.get('dimension_name', dim_key)}: {dim_data.get('dimension_score')}分")
            logger.info(f"    优势: {dim_data.get('strengths', [])}")
            logger.info(f"    不足: {dim_data.get('weaknesses', [])}")

        logger.info(f"\n综合报告：")
        logger.info(result.get("comprehensive_report", "")[:500])

        logger.info("✓ 综合分析评估测试通过")

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_07_llm_client_status(self, llm_client):
        """测试7：验证LLM客户端状态"""
        logger.info("=" * 60)
        logger.info("测试7：LLM客户端状态检查")
        logger.info("=" * 60)

        status = llm_client.get_status()

        assert status is not None, "状态不应为空"
        assert "model" in status, "状态缺少 model"
        assert "api_key_configured" in status, "状态缺少 api_key_configured"

        logger.info("LLM客户端状态：")
        logger.info(f"  - 模型: {status.get('model')}")
        logger.info(f"  - Base URL: {status.get('base_url')}")
        logger.info(f"  - API Key已配置: {status.get('api_key_configured')}")
        logger.info(f"  - 温度: {status.get('temperature')}")
        logger.info(f"  - 超时: {status.get('timeout')}s")
        logger.info(f"  - 最大并发: {status.get('max_concurrency')}")
        logger.info(f"  - 速率限制: {status.get('rate_limit')}/min")

        logger.info("✓ LLM客户端状态检查通过")


class TestPositionAIService:
    """岗位AI服务独立测试"""

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_generate_with_documents(self, position_service: PositionService, llm_client):
        """测试：带参考文档的岗位生成"""
        logger.info("=" * 60)
        logger.info("测试：带参考文档的岗位生成")
        logger.info("=" * 60)

        documents = [
            {
                "name": "公司技术栈说明.txt",
                "content": "公司主要使用Python/FastAPI作为后端技术栈，数据库使用MySQL和Redis，部署在Kubernetes集群上。"
            }
        ]

        result = await position_service.generate_position_requirements(
            description="招聘一名后端开发工程师",
            documents=documents
        )

        assert "position" in result
        assert "required_skills" in result

        logger.info(f"生成的岗位: {result.get('position')}")
        logger.info(f"必备技能: {result.get('required_skills')}")
        logger.info("✓ 带文档的岗位生成测试通过")


class TestInterviewService:
    """面试服务独立测试"""

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_skill_based_questions(self, interview_service: InterviewService, llm_client):
        """测试：基于技能生成问题"""
        logger.info("=" * 60)
        logger.info("测试：基于技能生成问题")
        logger.info("=" * 60)

        questions = await interview_service.generate_skill_based_questions(
            category="系统设计",
            candidate_level="senior",
            count=2
        )

        assert len(questions) > 0, "应生成至少1个问题"

        for i, q in enumerate(questions, 1):
            logger.info(f"问题{i}: {q.get('question', '')[:100]}...")
            logger.info(f"  难度: {q.get('difficulty')}")

        logger.info("✓ 基于技能的问题生成测试通过")

class TestCandidateTypes:
    """不同候选人类型的模拟测试"""

    @pytest.mark.asyncio
    @pytest.mark.timeout(180)
    async def test_different_candidate_types(self, interview_service: InterviewService, llm_client, job_config: Dict[str, Any]):
        """测试：不同类型候选人的回答模拟"""
        logger.info("=" * 60)
        logger.info("测试：不同类型候选人的回答模拟")
        logger.info("=" * 60)

        question = "请描述一个您主导的技术难点攻克案例？"
        candidate_types = ["ideal", "junior", "nervous", "overconfident"]

        for ctype in candidate_types:
            logger.info(f"\n--- 候选人类型: {ctype} ---")

            answer = await interview_service.simulate_candidate_answer(
                question=question,
                resume_content=SAMPLE_RESUME_CONTENT,
                position_title=job_config["title"],
                position_description=job_config["description"],
                candidate_name="测试候选人",
                candidate_type=ctype,
                conversation_history=""
            )

            logger.info(f"回答: {answer[:200]}...")

        logger.info("✓ 不同候选人类型模拟测试通过")


# ==================== 运行配置 ====================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "-x",  # 遇到第一个失败就停止
    ])
