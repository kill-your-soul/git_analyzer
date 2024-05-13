from fastapi import FastAPI

from api.main import api_router
from core.config import settings
from middlewares.tokens import TokenAuthMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.include_router(api_router)
app.add_middleware(TokenAuthMiddleware)
print(settings.TOKENS)
