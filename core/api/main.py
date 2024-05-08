from fastapi import APIRouter

from api.routes import git

api_router = APIRouter()
api_router.include_router(git.router, prefix="/git", tags=["git"])
