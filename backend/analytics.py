from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .database import get_db
from .crud import get_activity_summary
from .auth import require_superuser

router = APIRouter()

@router.get('/analytics/activity')
def activity_summary(db: Session = Depends(get_db), admin = Depends(require_superuser)):
    return get_activity_summary(db)
