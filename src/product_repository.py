from typing import Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, schemas


def get_user_by_email(db: Session, *, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_club(db: Session, *, club: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.club == club).first()


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


# -----------------TEAMS-----------------------
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.get(models.User, user_id)


def get_players_by_ids(db: Session, *, ids: list[int]) -> list[models.Player]:
    return (
        db.query(models.Player)
        .filter(models.Player.player_id.in_(ids))
        .order_by(models.Player.player_id)
        .with_for_update()
        .all()
    )


def get_behaviors_by_ids(db: Session, *, ids: list[int]) -> list[models.Behavior]:
    return db.query(models.Behavior).filter(models.Behavior.id_behavior.in_(ids)).all()


def get_team_by_owner_and_name(
    db: Session, *, owner_id: int, name: str
) -> Optional[models.Team]:
    return (
        db.query(models.Team)
        .filter(models.Team.owner_id == owner_id, models.Team.name == name)
        .first()
    )


def add_team(
    db: Session,
    *,
    owner_id: int,
    name: str,
    starters: list[tuple[int, int]],
    substitutes: list[tuple[int, int]],
) -> models.Team:
    assignments = [(pid, bid, True) for pid, bid in starters] + [
        (pid, bid, False) for pid, bid in substitutes
    ]

    try:
        team = models.Team(owner_id=owner_id, name=name)
        db.add(team)
        db.flush()  # asigna team.team_id sin confirmar

        for player_id, behavior_id, is_starter in assignments:
            player = db.get(models.Player, player_id)
            player.team_id = team.team_id
            player.behavior_id = behavior_id
            player.is_starter = is_starter
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(team)
    return team


def create_player(db: Session, user_id: int, player: schemas.PlayerIn) -> models.Player:

    pacss = player.pacss_attributes
    p = models.Player(
        name=player.name,
        owner_id=user_id,
        shirt_number=player.shirt_number,
        power=pacss.power,
        agility=pacss.agility,
        control=pacss.control,
        speed=pacss.speed,
        strength=pacss.strength,
    )

    db.add(p)
    db.commit()
    db.refresh(p)

    return p

def get_players(db: Session, user_id: int) -> list[models.Player]:
    return (
            db.query(models.Player)
            .filter(models.Player.owner_id == user_id)
            .all()
        )

#-----------------FRIENDLY MATCHES-----------------------
def create_match(
    db: Session,
    *,
    is_friendly: bool,
    status: str,
    home_team_id: int,
    away_team_id: Optional[int],
    match_duration: int,
    is_private: bool,
    password: Optional[str],
    current_period: int,
    league_id: Optional[int],     
    scheduled_at: Optional[int],  
) -> models.Match:
    match = models.Match(
        is_friendly=is_friendly,
        status=status,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        match_duration=match_duration,
        is_private=is_private,
        password=password,
        current_period=current_period,
        league_id=league_id,
        scheduled_at=scheduled_at,
    )
    db.add(match)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(match)
    return match