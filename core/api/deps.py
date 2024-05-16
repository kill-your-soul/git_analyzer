from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from core.db import engine

async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None, None]:
    async with async_session_maker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db)]
