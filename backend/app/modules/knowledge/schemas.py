from pydantic import BaseModel


class SearchRequest(BaseModel):
    project_id: str
    query: str


class SearchResult(BaseModel):
    source_type: str
    source_id: str
    title: str
    text: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
