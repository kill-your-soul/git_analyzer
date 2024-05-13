from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from core.config import settings


class TokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Извлечение токена из заголовков
        token = request.headers.get("Authorization")
        if token is None or token not in settings.TOKENS:
            # Если токен не предоставлен или недействителен, возвращаем ошибку
            # raise HTTPException(status_code=403, detail="Access Denied")
            return JSONResponse(content={"reason": "Access Denied"}, status_code=403)
        response = await call_next(request)
        return response

