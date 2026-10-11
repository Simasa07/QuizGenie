from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database import models
from app.schemas.quiz import UserRegister, UserLogin, UserOut, AuthResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/signup", response_model=AuthResponse)
def register_user(user_in: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Account with this email already exists. Please log in.",
        )

    user = models.User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),  # bcrypt hash, never plaintext
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, id=user.id, username=user.username, email=user.email)


@router.post("/login", response_model=AuthResponse)
def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()

    # Same error, same status code, whether the email doesn't exist or the
    # password is wrong. Giving a different message for each ("Account not
    # found" vs "Incorrect password") lets an attacker enumerate which
    # emails are registered just by trying logins - this closes that gap.
    if not user or not user.hashed_password or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, id=user.id, username=user.username, email=user.email)


@router.get("/me", response_model=UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    """Lets the app confirm who it's logged in as, using only the token."""
    return current_user
