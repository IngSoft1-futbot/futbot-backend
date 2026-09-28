from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
from . import models, schemas
from .utils import hash_password


def get_user_by_email_or_username(db: Session, email: str, username: str) -> Optional[models.User]:
    return (
        db.query(models.User)
        .filter(or_(models.User.email == email, models.User.username == username))
        .first()
    )


def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    user = models.User(
        username=user_in.username,
        name=user_in.name,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        avatar=user_in.avatar,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user