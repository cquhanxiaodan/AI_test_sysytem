from app.modules.auth.seed_data import PROJECTS, SeedProject, SeedUser
from app.modules.projects.schemas import ProjectDocumentRuleRead, ProjectRead


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


def to_project_read(project: SeedProject, role: str) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        code=project.code,
        name=project.name,
        description=project.description,
        role=role,
        document_rules=[ProjectDocumentRuleRead(**rule) for rule in project.document_rules],
    )
