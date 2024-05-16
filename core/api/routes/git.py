from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select

from api.deps import SessionDep
from models.task import Task
from schemas.git import GitIn
from utils.celery_worker import celery_app
from utils.download import download_content

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/")
async def get_dot_git(session: SessionDep, git_in: GitIn, request: Request) -> None:
    path_to_save = Path(__file__).parent.parent.parent / "gits" / git_in.url.split("://")[1]
    task = download_content.apply_async(args=[git_in.url, str(path_to_save)])

    new_task = Task(
        task_id=task.id,
        status="PENDING",
        result=str(path_to_save),
        user=request.headers.get("Authorization"),
        url=git_in.url,
        path="",
    )
    session.add(new_task)
    await session.commit()
    await session.refresh(new_task)
    return new_task


# @router.get("/status/{task_id}")
# async def get_status(task_id: str) -> dict[str, str]:
#     task_result = download_content.AsyncResult(task_id)
#     if task_result.state == "PENDING":
#         return {"status": "pending"}
#     elif task_result.state == "SUCCESS":
#         return task_result.result
#     elif task_result.state == "FAILURE":
#         return {"status": "failure", "error": str(task_result.info)}
#     else:
#         return {"status": "unknown"}


@router.get("/status/{task_id}")
async def get_status(session: SessionDep, task_id: str):
    task_result = AsyncResult(task_id, backend=celery_app.backend, app=celery_app)
    statement = select(Task).where(Task.task_id == task_id)
    result = await session.execute(statement)
    task_in_db: Task | None = result.scalar_one_or_none()
    if not task_in_db:
        raise HTTPException(status_code=404, detail="Task not found")
    # task = Task.model_validate()
    task_in_db.status = task_result.state
    task_in_db.result = task_result.result["status"] if task_result.ready() else ""
    if task_result.info and task_result.info["status"] == "success":
        task_in_db.path = task_result.info["path"]
    # print(task_result.result)
    # print(task_result.info)
    # print(task_result.state)
    session.add(task_in_db)
    await session.commit()
    await session.refresh(task_in_db)
    return task_in_db


@router.get("/html", response_class=HTMLResponse)
async def html(request: Request):
    return templates.TemplateResponse("git.html", {"request": request})


@router.get("/tasks")
async def tasks(session: SessionDep, request: Request):
    statement = select(Task)
    result = await session.execute(statement)
    tasks = result.scalars().all()
    # return tasks
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks})
