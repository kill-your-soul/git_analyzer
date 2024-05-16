from uuid import uuid4

from sqlmodel import Field, SQLModel


class BaseModel(SQLModel):
    id: str = Field(primary_key=True, default_factory=lambda: str(uuid4()), nullable=False)
