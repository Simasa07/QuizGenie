from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database import models
from app.core.security import decode_access_token

# HTTPBearer rather than OAuth2PasswordBearer: our login endpoint takes a
# JSON body (email/password), not OAuth2's form-encoded username/password,
# so a plain "paste your Bearer token" scheme matches our actual login flow
# and still shows the padlock/Authorize button correctly in /docs.
bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Every protected endpoint depends on this instead of trusting a raw
    user_id passed in by the client. The identity comes only from a valid,
    signed token - nobody can claim to be a different user just by
    changing a request parameter.
    """
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again.",
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again.",
        )

    return user
