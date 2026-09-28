from typing import Optional

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models


def get_user_by_email_or_username(
    db: Session, *, email: str, username: str
) -> Optional[models.User]:
    return (
        db.query(models.User)
        .filter(or_(models.User.email == email, models.User.username == username))
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