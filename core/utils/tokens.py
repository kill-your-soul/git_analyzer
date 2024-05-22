from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from core.config import settings


def token_required(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request: Request = kwargs.get("request")
        if request is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request object is required")

        token: str = request.headers.get("Authorization", "")
        print(token)
        if token not in settings.TOKENS:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied")
        return await func(*args, **kwargs)
    return wrapper
