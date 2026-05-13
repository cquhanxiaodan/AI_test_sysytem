from pydantic import BaseModel


class ProjectDocumentRuleRead(BaseModel):
    label_key: str
    label_value: str


class ProjectRead(BaseModel):
    id: str
    code: str
    name: str
    description: str | None
    role: str
    document_rules: list[ProjectDocumentRuleRead]


class ProjectCreateRequest(BaseModel):
    code: str
    name: str
    description: str | None = None


class ProjectDeleteRequest(BaseModel):
    password: str


class ProjectWorkspaceStats(BaseModel):
    project_id: str
    published_documents: int
    test_items: int
    risk_items: int
    validation_plans: int
    test_packages: int
    ai_configured: bool
    next_steps: list[str]
