from typing import Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models


def get_user_by_email(
    db: Session, *, email: str
) -> Optional[models.User]:
    return (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

def get_user_by_username(
    db: Session, *, username: str
) -> Optional[models.User]:
    return (
        db.query(models.User)
        .filter(models.User.username == username)
        .first()
    )

def create_user(
    db: Session,
    *,
    username: str,
    name: str,
    email: str,
    password_hash: str,
    avatar: Optional[str],
) -> models.User:
    user = models.User(
        username=username,
        name=name,
        email=email,
        password_hash=password_hash,
        avatar=avatar,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(user)
    return user