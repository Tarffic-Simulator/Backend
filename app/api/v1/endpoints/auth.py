from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.core.log_config import get_logger
from app.models.user import User
from app.schemas import UserCreate, Token

router = APIRouter()
logger = get_logger(__name__)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        logger.warning("Register attempt for existing username: %s", payload.username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario ya registrado")

    new_user = User(username=payload.username, hashed_password=get_password_hash(payload.password))
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception:
        logger.exception("DB error while creating user: %s", payload.username)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear usuario")

    logger.info("User registered: %s (id=%s)", new_user.username, new_user.id)
    return {"message": "Usuario creado exitosamente", "id": new_user.id}


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("Failed login attempt for username: %s", form_data.username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuario o contrase\u00f1a incorrectos")

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    logger.info("User logged in: %s", user.username)
    return {"access_token": access_token, "token_type": "bearer"}