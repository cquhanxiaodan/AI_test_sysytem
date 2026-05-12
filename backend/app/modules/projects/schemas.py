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
