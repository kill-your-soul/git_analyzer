from celery.result import AsyncResult
from fastapi import HTTPException
from sqlmodel import select

from api.deps import SessionDep
from models.task import Task
from utils.celery_worker import celery_app


async def update_task_status(session: SessionDep, task_id: str):
    task_result = AsyncResult(task_id, backend=celery_app.backend, app=celery_app)
    statement = select(Task).where(Task.task_id == task_id)
    result = await session.execute(statement)
    task_in_db: Task | None = result.scalar_one_or_none()
    if not task_in_db:
        raise HTTPException(status_code=404, detail="Task not found")

    task_in_db.status = task_result.state
    print(task_result.traceback)
    print(task_result.info)
    
    if task_result.info and task_result.info["status"] == "success":
        task_in_db.path = task_result.info["path"]
        task_in_db.leaks = task_result.info["leaks"]
    if task_result.info and task_result.info["status"].lower() == "error":
        task_in_db.status = "ERROR"
        task_in_db.result = task_result.info["path"]
    session.add(task_in_db)
    await session.commit()
    await session.refresh(task_in_db)
    return task_in_db


async def update_all_tasks_status(session: SessionDep, tasks: list[Task]) -> None:
    for task in tasks:
        await update_task_status(session, task.task_id)
