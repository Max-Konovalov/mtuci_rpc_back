# main.py
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

# ✅ Абсолютные импорты — без точек
from database import SessionLocal, engine, Base
from models import Task
from schemas import TaskCreate, TaskUpdate, Task

# Создание таблиц (выполняется один раз при импорте main.py)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Task Tracker API",
    description="REST API для управления задачами",
    version="1.0.0",
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- CRUD ---

@app.post("/tasks/", response_model=Task, tags=["Tasks"])
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    db_task = Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.get("/tasks/", response_model=List[Task], tags=["Tasks"])
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
    query = db.query(Task)

    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    if q:
        q = q.strip().lower()
        query = query.filter(
            (Task.title.ilike(f"%{q}%")) |
            (Task.description.ilike(f"%{q}%"))
        )

    sort_col = getattr(Task, sort)
    if order == "desc":
        sort_col = sort_col.desc()
    query = query.order_by(sort_col)

    offset = (page - 1) * size
    tasks = query.offset(offset).limit(size).all()
    return tasks

@app.get("/tasks/count", response_model=dict, tags=["Stats"])
def get_task_stats(db: Session = Depends(get_db)):
    total = db.query(Task).count()
    by_status = {
        "todo": db.query(Task).filter(Task.status == "todo").count(),
        "in_progress": db.query(Task).filter(Task.status == "in_progress").count(),
        "done": db.query(Task).filter(Task.status == "done").count(),
    }
    by_priority = {
        "low": db.query(Task).filter(Task.priority == "low").count(),
        "medium": db.query(Task).filter(Task.priority == "medium").count(),
        "high": db.query(Task).filter(Task.priority == "high").count(),
    }
    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
    }

@app.get("/tasks/{task_id}", response_model=Task, tags=["Tasks"])
def read_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.put("/tasks/{task_id}", response_model=Task, tags=["Tasks"])
def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    for key, value in task_update.model_dump(exclude_unset=True).items():
        setattr(db_task, key, value)
    
    db.commit()
    db.refresh(db_task)
    return db_task

@app.patch("/tasks/{task_id}/status", response_model=Task, tags=["Tasks"])
def update_task_status(
    task_id: int,
    status: str = Query(..., regex="^(todo|in_progress|done)$"),
    db: Session = Depends(get_db)
):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db_task.status = status
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/tasks/{task_id}", response_model=dict, tags=["Tasks"])
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()
    return {"message": "Task deleted successfully"}