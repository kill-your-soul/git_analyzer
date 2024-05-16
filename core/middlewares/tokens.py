from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings


class TokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        # Извлечение токена из заголовков
        token = request.headers.get("Authorization")
        if token is None or token not in settings.TOKENS:
            # Если токен не предоставлен или недействителен, возвращаем ошибку
            return JSONResponse(content={"reason": "Access Denied"}, status_code=403)
        response: Response = await call_next(request)
        return response

