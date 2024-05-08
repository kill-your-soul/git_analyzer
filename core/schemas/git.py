from pydantic import BaseModel


class GitIn(BaseModel):
    url: str
