from pathlib import Path

from fastapi import APIRouter

from schemas.git import GitIn
from utils.download import download_content

router = APIRouter()


@router.post("/")
async def get_dot_git(git_in: GitIn) -> None:
    path_to_save = Path(__file__).parent.parent.parent / "gits"
    download_content(git_in.url, path_to_save / git_in.url.split("://")[1])
