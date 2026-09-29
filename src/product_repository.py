from typing import Any
import secrets
from .schemas import PlayerIn, Player, Player_out, PACSS_attributes
from typing import Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Users
from .utils import hash_password

def get_user_by_email(db: Session, *, email: str) -> Optional[Users]:
    return (
        db.query(Users)
        .filter(Users.email == email)
        .first()
    )

def get_user_by_club(
    db: Session, *, club: str
) -> Optional[Users]:
    return (
        db.query(Users)
        .filter(Users.club == club)
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
) -> Users:
    user = Users(
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



def auth_login(db : Session, email: str, password: str) -> Optional[str]:

    stmt = select(Users).where(Users.email == email)
    

    user = db.scalar(stmt)

    if user is None:
        return None

    if user.password_hash != hash_password(password): #Frontend deberia enviar la contraseña hasheada
        return None

    return secrets.token_urlsafe(32)


def create_player(db:Session ,user_id: int, player: PlayerIn) -> Player_out:

    user: Any | None = db.get(Users, user_id)

    if user is None:
        return None

    user.numb_players += 1

    p = Player(
        name=player.name,
        user_id=user_id,
        shirt_numb=player.shirt_numb,
        power=player.pacss_attributes.power,
        agility=player.pacss_attributes.agility,
        control=player.pacss_attributes.control,
        speed=player.pacss_attributes.speed,
        strength=player.pacss_attributes.strength
    )

    db.add(p)
    db.commit()
    db.refresh(p)

    return Player_out(
        player_id=p.player_id,
        name=p.name,
        shirt_numb=p.shirt_numb,
        pacss_attributes=PACSS_attributes(
            power=p.power,
            agility=p.agility,
            control=p.control,
            speed=p.speed,
            strength=p.strength
        )
    )
