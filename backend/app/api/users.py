from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database import models
from app.schemas.quiz import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserOut)
def create_or_get_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    V1 has no authentication yet, so this simply creates a user record
    (or returns the existing one) that document uploads and quiz attempts
    can be attached to. Real auth (login, tokens) is a V2+ concern.
    """
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        return existing

    user = models.User(email=user_in.email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user