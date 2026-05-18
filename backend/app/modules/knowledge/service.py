from app.modules.knowledge.schemas import SearchResult
from app.modules.risks.service import list_risks
from app.modules.test_items.service import list_test_items
from app.modules.test_packages.service import list_packages


def search_project_knowledge(project_id: str, query: str) -> list[SearchResult]:
    terms = [term.lower() for term in query.split() if term.strip()]
    candidates: list[SearchResult] = []

    for item in list_test_items(project_id):
        if item.status != "published":
            continue
        text = " ".join([item.title, item.objective, item.method, item.evidence])
        candidates.append(SearchResult(source_type="test_item", source_id=item.id, title=item.title, text=text, score=score_text(text, terms)))

    for package in list_packages(project_id):
        if package.status != "published":
            continue
        text = " ".join([package.name, package.change_type, package.applicable_scope, package.evidence])
        candidates.append(SearchResult(source_type="test_package", source_id=package.id, title=package.name, text=text, score=score_text(text, terms)))

    for risk in list_risks(project_id=project_id):
        if risk.status != "published":
            continue
        text = " ".join([risk.title, risk.description, risk.suggested_test])
        candidates.append(SearchResult(source_type="risk", source_id=risk.id, title=risk.title, text=text, score=score_text(text, terms)))

    return sorted([candidate for candidate in candidates if candidate.score > 0], key=lambda result: result.score, reverse=True)


def score_text(text: str, terms: list[str]) -> float:
    lowered = text.lower()
    if not terms:
        return 0
    return sum(1 for term in terms if term in lowered) / len(terms)
