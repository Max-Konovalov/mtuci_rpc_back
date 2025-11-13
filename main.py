from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database import SessionLocal, engine, Base
import models
from schemas import TaskCreate, TaskUpdate, Task as TaskSchema

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000", "http://localhost:5173"],
#     allow_methods=["*"],
#     allow_headers=["*"],
#     allow_credentials=True  
# )
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://aeza-3xui.ru"],  # ← Замени на реальный домен фронта
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/tasks/", response_model=TaskSchema)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    db_task = models.Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@app.get("/tasks/", response_model=List[TaskSchema], tags=["Tasks"])
def read_tasks(
    status: Optional[str] = Query(None, regex="^(todo|in_progress|done)$"),
    priority: Optional[str] = Query(None, regex="^(low|medium|high)$"),
    q: Optional[str] = Query(None, description="Поиск по title/description"),
    sort: Optional[str] = Query("created_at", regex="^(id|title|status|priority|due_date|created_at|updated_at)$"),
    order: Optional[str] = Query("asc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(models.Task)

    if status:
        query = query.filter(models.Task.status == status)
    if priority:
        query = query.filter(models.Task.priority == priority)
    if q:
        q = q.strip().lower()
        query = query.filter(
            (models.Task.title.ilike(f"%{q}%")) |
            (models.Task.description.ilike(f"%{q}%"))
        )

    sort_col = getattr(models.Task, sort)
    if order == "desc":
        sort_col = sort_col.desc()
    query = query.order_by(sort_col)

    offset = (page - 1) * size
    tasks = query.offset(offset).limit(size).all()
    return tasks


@app.get("/tasks/count", response_model=dict, tags=["Stats"])
def get_task_stats(db: Session = Depends(get_db)):
    total = db.query(models.Task).count()
    by_status = {
        "todo": db.query(models.Task).filter(models.Task.status == "todo").count(),
        "in_progress": db.query(models.Task).filter(models.Task.status == "in_progress").count(),
        "done": db.query(models.Task).filter(models.Task.status == "done").count(),
    }
    by_priority = {
        "low": db.query(models.Task).filter(models.Task.priority == "low").count(),
        "medium": db.query(models.Task).filter(models.Task.priority == "medium").count(),
        "high": db.query(models.Task).filter(models.Task.priority == "high").count(),
    }
    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
    }


@app.get("/tasks/{task_id}", response_model=TaskSchema, tags=["Tasks"])
def read_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/tasks/{task_id}", response_model=TaskSchema, tags=["Tasks"])
def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    for key, value in task_update.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(db_task, key, value)
    
    db.commit()
    db.refresh(db_task)
    return db_task


@app.patch("/tasks/{task_id}/status", response_model=TaskSchema, tags=["Tasks"])
def update_task_status(
    task_id: int,
    status: str = Query(..., regex="^(todo|in_progress|done)$"),
    db: Session = Depends(get_db)
):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db_task.status = status
    db.commit()
    db.refresh(db_task)
    return db_task


@app.delete("/tasks/{task_id}", response_model=dict, tags=["Tasks"])
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()
    return {"message": "Task deleted successfully"}