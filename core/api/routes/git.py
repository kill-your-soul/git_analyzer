from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from schemas.git import GitIn
from utils.download import download_content

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/")
async def get_dot_git(git_in: GitIn, request: Request) -> None:
    path_to_save = Path(__file__).parent.parent.parent / "gits" / git_in.url.split("://")[1]
    task = download_content.apply_async(args=[git_in.url, str(path_to_save)])
    return {
        "task_id": task.id,
        "url": git_in.url,
        "added_by": request.headers.get("Authorization"),
        "datetime": datetime.now(ZoneInfo("Europe/Moscow")),
    }

@router.get("/status/{task_id}")
async def get_status(task_id: str) -> dict[str, str]:
    task_result = download_content.AsyncResult(task_id)
    if task_result.state == "PENDING":
        return {"status": "pending"}
    elif task_result.state == "SUCCESS":
        return task_result.result
    elif task_result.state == "FAILURE":
        return {"status": "failure", "error": str(task_result.info)}
    else:
        return {"status": "unknown"}


@router.get("/html", response_class=HTMLResponse)
async def html(request: Request):
    return templates.TemplateResponse("git.html", {"request": request})

@router.get("/tasks")
async def tasks(request: Request):
    return
