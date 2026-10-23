from collections.abc import Generator

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy import select

from sqlalchemy.exc import IntegrityError

from sqlalchemy.orm import Session

from app.database import get_db

from app.models import User

from app.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse

from app.utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
    )




router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
    )

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    )
def register_user(payload: UserRegister, db: DbSession) -> User:
    """Create an account with a securely hashed password."""
    username = payload.username.lower()

    existing_user = db.scalar(
        select(User).where(User.username == username)
        )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered.",
            )
    user = User(
        username=username,
        hashed_password=hash_password(payload.password),
        )
    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered.",
            ) from None

    return user


@router.post("/token", response_model=TokenResponse)

def login_user(
    payload: UserLogin, 
    db: DbSession
    ) -> TokenResponse:
    """Verify credentials and issue an access token."""
    
    username = payload.username.strip().lower()
    
    user = db.scalar(
        select(User).where(User.username == username)
        )

    if (
        user is None
        or not verify_password(payload.password, user.hashed_password)
        or not user.is_active
        ):
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
            )
    token = create_access_token(user_id=user.id)
    return TokenResponse(access_token=token)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
        ],
    db: DbSession,
    ) -> User:
    """Resolve the active user from a verified bearer token."""
    
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
            )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (ValueError, KeyError, TypeError):
            
            raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
            ) from None

    user = db.get(User, user_id)
    
    if user is None or not user.is_active:
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive user.",
            headers={"WWW-Authenticate": "Bearer"},
            )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get(
        "/me", 
        response_model=UserResponse
        )
def read_current_user(
    current_user: CurrentUser
    ) -> User:
    """Return the authenticated user's public profile."""
    
    return current_user

    







