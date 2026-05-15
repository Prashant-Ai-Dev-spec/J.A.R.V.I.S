from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas
from passlib.context import CryptContext
from typing import List, Optional
from .integrations import token_storage

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed = pwd_context.hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# Chat message persistence
def save_message(db: Session, user, content: str):
    msg = models.Message(user_id=user.id, username=user.username, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

def get_messages(db: Session, limit: int = 100, q: Optional[str] = None) -> List[models.Message]:
    query = db.query(models.Message)
    if q:
        query = query.filter(models.Message.content.ilike(f"%{q}%"))
    return query.order_by(models.Message.created_at.desc()).limit(limit).all()

# File metadata persistence
def save_file_metadata(db: Session, user, filename: str, path: str, content_type: str = None, size: int = None):
    fm = models.FileMeta(user_id=user.id, filename=filename, path=path, content_type=content_type, size=size)
    db.add(fm)
    db.commit()
    db.refresh(fm)
    return fm

def get_user_files(db: Session, user_id: int):
    return db.query(models.FileMeta).filter(models.FileMeta.user_id == user_id).order_by(models.FileMeta.created_at.desc()).all()

def get_file_by_id(db: Session, file_id: int):
    return db.query(models.FileMeta).filter(models.FileMeta.id == file_id).first()

# Project / Task CRUD
def create_project(db: Session, p, user):
    pr = models.Project(name=p.name, owner_id=user.id)
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr

def list_projects(db: Session, user):
    return db.query(models.Project).filter(models.Project.owner_id == user.id).all()

def create_task(db: Session, t, user):
    task = models.Task(project_id=t.project_id, title=t.title, description=t.description, assignee_id=t.assignee_id, status='open')
    db.add(task)
    db.commit()
    db.refresh(task)
    # Log activity
    log_activity(db, user, 'create_task', f'Task {task.id} created')
    return task

def list_tasks(db: Session, user, limit: int = 100):
    return db.query(models.Task).limit(limit).all()

# Activity logging
def log_activity(db: Session, user, action: str, details: str = None):
    uid = getattr(user, 'id', None)
    al = models.ActivityLog(user_id=uid, action=action, details=details)
    db.add(al)
    db.commit()
    db.refresh(al)
    return al

def get_activity_summary(db: Session):
    # simple summary: counts per action
    rows = db.query(models.ActivityLog.action, func.count(models.ActivityLog.id)).group_by(models.ActivityLog.action).all()
    return {r[0]: r[1] for r in rows}

# Integration token helpers
def save_integration_token(db: Session, user_id: Optional[int], provider: str, token_info: dict):
    """Upsert an encrypted token for a user and provider. user_id may be None for global tokens."""
    enc_access = None
    enc_refresh = None
    if token_info.get('access_token'):
        enc_access = token_storage.encrypt_token(token_info.get('access_token'))
    if token_info.get('refresh_token'):
        enc_refresh = token_storage.encrypt_token(token_info.get('refresh_token'))
    expires_at = token_info.get('expires_at')
    existing = db.query(models.IntegrationToken).filter(models.IntegrationToken.user_id == user_id, models.IntegrationToken.provider == provider).first()
    if existing:
        existing.access_token = enc_access
        existing.refresh_token = enc_refresh
        existing.expires_at = expires_at
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    it = models.IntegrationToken(user_id=user_id, provider=provider, access_token=enc_access, refresh_token=enc_refresh, expires_at=expires_at)
    db.add(it)
    db.commit()
    db.refresh(it)
    return it

def get_integration_token(db: Session, user_id: Optional[int], provider: str) -> Optional[dict]:
    """Retrieve and decrypt a token for a user and provider."""
    it = db.query(models.IntegrationToken).filter(models.IntegrationToken.user_id == user_id, models.IntegrationToken.provider == provider).first()
    if not it:
        return None
    result = {'provider': provider}
    if it.access_token:
        try:
            result['access_token'] = token_storage.decrypt_token(it.access_token)
        except Exception:
            result['access_token'] = it.access_token  # fallback: plain text
    if it.refresh_token:
        try:
            result['refresh_token'] = token_storage.decrypt_token(it.refresh_token)
        except Exception:
            result['refresh_token'] = it.refresh_token
    if it.expires_at:
        result['expires_at'] = it.expires_at
    return result

def get_integration_token(db: Session, user_id: Optional[int], provider: str):
    row = None
    if user_id is not None:
        row = db.query(models.IntegrationToken).filter(models.IntegrationToken.user_id == user_id, models.IntegrationToken.provider == provider).first()
    if not row:
        row = db.query(models.IntegrationToken).filter(models.IntegrationToken.user_id.is_(None), models.IntegrationToken.provider == provider).first()
    if not row:
        return None
    return {
        'access_token': token_storage.decrypt_token(row.access_token) if row.access_token else None,
        'refresh_token': token_storage.decrypt_token(row.refresh_token) if row.refresh_token else None,
        'expires_at': row.expires_at
    }

def list_integration_tokens(db: Session, user_id: Optional[int]):
    rows = db.query(models.IntegrationToken).filter(models.IntegrationToken.user_id == user_id).all()
    out = []
    for r in rows:
        out.append({'provider': r.provider, 'access_token': token_storage.decrypt_token(r.access_token) if r.access_token else None, 'expires_at': r.expires_at})
    return out
