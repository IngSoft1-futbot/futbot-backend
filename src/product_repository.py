import secrets

from sqlalchemy import select

from schemas import Player, Player_out, PACSS_attributes

# importar acá tus modelos SQLAlchemy
# from models import Users, Players

# importar/crear acá tu session
# from database import session


def auth_login(email: str, password: str) -> str | None:

    stmt = select(Users).where(Users.email == email)
    user = session.scalar(stmt)

    if user is None:
        return None

    if user.password != password:
        return None

    return secrets.token_urlsafe(32)


def create_player(user_id: int, player: Player) -> Player_out:

    u = session.get(Users, user_id)

    if u is None:
        return None

    u.numb_players += 1

    p = Players(
        name=player.name,
        user_id=user_id,
        shirt_numb=player.shirt_numb,
        power=player.pacss_attributes.power,
        agility=player.pacss_attributes.agility,
        control=player.pacss_attributes.control,
        speed=player.pacss_attributes.speed,
        strength=player.pacss_attributes.strength
    )

    session.add(p)
    session.commit()
    session.refresh(p)

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