from datetime import datetime

from sqlmodel import Field, MetaData

from models.base import BaseModel


class Task(BaseModel, table=True):
    metadata = MetaData()
    __tablename__ = "tasks"

    task_id: str = Field(unique=True, index=True)
    path: str
    status: str = Field(index=True)
    result: str = Field(index=True)
    user: str = Field(index=True)
    url: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)
