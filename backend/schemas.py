from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    is_active: bool = True
    is_superuser: bool = False

    class Config:
        orm_mode = True

class RefreshRequest(BaseModel):
    refresh_token: str

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None

class ProjectCreate(BaseModel):
    name: str

from datetime import datetime

class ProjectOut(BaseModel):
    id: int
    name: str
    created_at: datetime
    class Config:
        orm_mode = True

class TaskCreate(BaseModel):
    project_id: Optional[int]
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None

class TaskOut(BaseModel):
    id: int
    project_id: Optional[int]
    title: str
    description: Optional[str]
    assignee_id: Optional[int]
    status: str
    created_at: datetime
    class Config:
        orm_mode = True

class ActivityOut(BaseModel):
    action: str
    count: int
