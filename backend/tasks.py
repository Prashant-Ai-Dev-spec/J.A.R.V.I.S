from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .schemas import TaskCreate, TaskOut, ProjectCreate, ProjectOut
from .database import get_db
from .crud import create_task, list_tasks, create_project, list_projects, get_user_by_username
from .auth import get_current_user

router = APIRouter()

@router.post('/projects', response_model=ProjectOut)
def create_project_endpoint(p: ProjectCreate, db: Session = Depends(get_db), user = Depends(get_current_user)):
    pr = create_project(db, p, user)
    return pr

@router.get('/projects', response_model=List[ProjectOut])
def list_projects_endpoint(db: Session = Depends(get_db), user = Depends(get_current_user)):
    return list_projects(db, user)

@router.post('/tasks', response_model=TaskOut)
def create_task_endpoint(t: TaskCreate, db: Session = Depends(get_db), user = Depends(get_current_user)):
    return create_task(db, t, user)

@router.get('/tasks', response_model=List[TaskOut])
def list_tasks_endpoint(db: Session = Depends(get_db), user = Depends(get_current_user)):
    return list_tasks(db, user)
