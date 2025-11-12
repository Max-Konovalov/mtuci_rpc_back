from sqlalchemy import Column, Integer, String, Text, DateTime, func
from database import Base  # ← НЕ from .database

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="todo")
    priority = Column(String(10), default="medium")
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())