from pydantic import BaseModel


class FreeChatRequest(BaseModel):
    project_id: str
    question: str
    use_project_knowledge: bool = True
    use_external_model: bool = True


class FreeChatSource(BaseModel):
    source_type: str
    source_id: str
    title: str
    text: str
    score: float


class FreeChatResponse(BaseModel):
    answer: str
    used_model: bool
    sources: list[FreeChatSource]
