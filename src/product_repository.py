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

def get_user_by_club(
    db: Session, *, club: str
) -> Optional[models.User]:
    return (
        db.query(models.User)
        .filter(models.User.club == club)
        .first()
    )

def create_user(
    db: Session,
    *,
    club: str,
    name: str,
    email: str,
    password_hash: str,
    avatar: Optional[str],
) -> models.User:
    user = models.User(
        club=club,
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