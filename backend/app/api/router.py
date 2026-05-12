from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.ai.router import router as ai_router
from app.modules.documents.router import router as documents_router
from app.modules.health.router import router as health_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.parsing.router import router as parsing_router
from app.modules.projects.router import router as projects_router
from app.modules.requirements.router import router as requirements_router
from app.modules.risks.router import router as risks_router
from app.modules.test_items.router import router as test_items_router
from app.modules.test_packages.router import router as test_packages_router
from app.modules.validation_plans.router import router as validation_plans_router


api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(documents_router)
api_router.include_router(parsing_router)
api_router.include_router(test_items_router)
api_router.include_router(test_packages_router)
api_router.include_router(risks_router)
api_router.include_router(knowledge_router)
api_router.include_router(ai_router)
api_router.include_router(requirements_router)
api_router.include_router(validation_plans_router)
