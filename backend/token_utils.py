from datetime import datetime, timedelta
import secrets
from typing import Optional
from sqlalchemy.orm import Session
from . import models


def create_refresh_token(db: Session, user_id: int, expires_days: int = 7) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=expires_days)
    rt = models.RefreshToken(token=token, user_id=user_id, expires_at=expires_at)
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return token


def get_refresh_token(db: Session, token: str) -> Optional[models.RefreshToken]:
    return db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()


def revoke_refresh_token(db: Session, token: str):
    rt = get_refresh_token(db, token)
    if rt:
        db.delete(rt)
        db.commit()


def revoke_user_refresh_tokens(db: Session, user_id: int):
    db.query(models.RefreshToken).filter(models.RefreshToken.user_id == user_id).delete()
    db.commit()


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def cleanup_expired(db: Session):
    db.query(models.RefreshToken).filter(models.RefreshToken.expires_at < datetime.utcnow()).delete()
    db.commit()
