from uuid import uuid4

from app.modules.ai.service import get_ai_config
from app.modules.auth.seed_data import PROJECTS, SeedProject, SeedUser
from app.modules.documents.repository import list_documents
from app.modules.projects.schemas import ProjectCreateRequest, ProjectDocumentRuleRead, ProjectRead, ProjectWorkspaceStats
from app.modules.risks.service import list_risks
from app.modules.test_items.service import list_test_items
from app.modules.test_packages.service import list_packages
from app.modules.validation_plans.service import list_plans


def list_projects_for_user(user: SeedUser) -> list[ProjectRead]:
    projects = []
    for project in PROJECTS.values():
        role = project.members.get(user.id)
        if role is None and "admin" not in user.roles:
            continue
        projects.append(to_project_read(project, role or "admin"))
    return projects


def get_project_for_user(project_id: str, user: SeedUser) -> ProjectRead | None:
    project = PROJECTS.get(project_id)
    if project is None:
        return None
    role = project.members.get(user.id)
    if role is None and "admin" not in user.roles:
        return None
    return to_project_read(project, role or "admin")


def create_project_for_user(payload: ProjectCreateRequest, user: SeedUser) -> ProjectRead:
    project_id = f"project-{uuid4()}"
    project = SeedProject(
        id=project_id,
        code=payload.code.strip(),
        name=payload.name.strip(),
        description=(payload.description or "").strip(),
        members={user.id: "owner"},
        document_rules=(),
    )
    PROJECTS[project_id] = project
    return to_project_read(project, "owner")


def delete_project_for_user(project_id: str, user: SeedUser, password: str) -> bool | None:
    project = PROJECTS.get(project_id)
    if project is None:
        return None
    if "admin" not in user.roles:
        return False
    if user.password != password:
        return False
    PROJECTS.pop(project_id)
    return True


def get_project_workspace_stats(project_id: str, user: SeedUser) -> ProjectWorkspaceStats | None:
    project = get_project_for_user(project_id, user)
    if project is None:
        return None
    documents = list_documents(project_id)
    published_documents = len([document for document in documents if document.status == "published"])
    test_items = len(list_test_items(project_id))
    risk_items = len(list_risks(project_id=project_id))
    validation_plans = len(list_plans(project_id))
    test_packages = len(list_packages(project_id))
    ai_configured = get_ai_config().configured
    return ProjectWorkspaceStats(
        project_id=project_id,
        published_documents=published_documents,
        test_items=test_items,
        risk_items=risk_items,
        validation_plans=validation_plans,
        test_packages=test_packages,
        ai_configured=ai_configured,
        next_steps=build_next_steps(published_documents, test_items, risk_items, validation_plans, test_packages, ai_configured),
    )


def build_next_steps(
    published_documents: int,
    test_items: int,
    risk_items: int,
    validation_plans: int,
    test_packages: int,
    ai_configured: bool,
) -> list[str]:
    steps: list[str] = []
    if published_documents == 0:
        steps.append("上传并发布验证方案、测试规范、Jira 导出或 DFMEA，建立项目资料基础。")
    if test_items == 0:
        steps.append("发布测试方案类资料后自动拆分测试条目，或在测试资产维护工具中补拆。")
    if test_packages == 0:
        steps.append("生成测试归口包，把测试条目归并为需求分析可复用的推荐集合。")
    if risk_items == 0:
        steps.append("上传 Jira 导出或 DFMEA，沉淀历史问题和失效模式风险。")
    if not ai_configured:
        steps.append("进入系统设置配置 AI 模型，提升标签识别、拆分、解析和方案检查质量。")
    if test_items > 0 and (risk_items > 0 or test_packages > 0):
        steps.append("进入需求分析，输入新需求或变更描述，生成测试推荐。")
    if validation_plans > 0:
        steps.append("进入验证方案页面执行完整性检查并导出 Word 草稿。")
    return steps[:5]


def to_project_read(project: SeedProject, role: str) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        code=project.code,
        name=project.name,
        description=project.description,
        role=role,
        document_rules=[ProjectDocumentRuleRead(**rule) for rule in project.document_rules],
    )
