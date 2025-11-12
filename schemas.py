from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class TaskBase(BaseModel):
    title: str = Field(..., max_length=100, min_length=3)
    description: Optional[str] = None
    status: str = Field(default="todo", pattern="^(todo|in_progress|done)$")
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    due_date: Optional[datetime] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(TaskBase):
    pass

class Task(TaskBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True