from unittest.mock import patch
import pytest
from sqlalchemy import create_engine, event 
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src import models, schemas, product_repository as repo

@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def make_user(db, club="juan", email="juan@gmail.com"):
    return repo.create_user(
        db, club=club, name="Juan",
        email=email, password_hash="hash", avatar=None,
    )


def test_create_user_lo_guarda(db):
    make_user(db)
    assert db.query(models.User).count() == 1


def test_get_user_by_email(db):
    make_user(db)
    assert repo.get_user_by_email(db, email="juan@gmail.com").club == "juan"
    assert repo.get_user_by_email(db, email="nadie@gmail.com") is None


def test_get_user_by_club(db):
    make_user(db)
    assert repo.get_user_by_club(db, club="juan").email == "juan@gmail.com"
    assert repo.get_user_by_club(db, club="nadie") is None


def test_create_user_duplicado_lanza_integrity_error(db):
    make_user(db)
    with pytest.raises(IntegrityError):
        make_user(db, club="otro", email="juan@gmail.com")   # mismo email


# --------------   TESTS DE LOGIN   --------------

def test_get_user_by_email_retorna_password_hash_para_login(db):
    # 1. Creamos un usuario de prueba
    repo.create_user(
        db, club="login_user", name="Login Test",
        email="login@gmail.com", password_hash="password123", avatar=None,
    )
    
    # 2. Buscamos el usuario por email como hace el login
    user = repo.get_user_by_email(db, email="login@gmail.com")
    
    # 3. Verificamos que traiga el usuario y su password para validar
    assert user is not None
    assert user.email == "login@gmail.com"
    assert user.password_hash == "password123"


# --------------   TESTS DE CREAR EQUIPO   --------------
 
def make_behavior(db, bid=0, creator_id=None, is_default=True):
    behavior = models.Behavior(
        id_behavior=bid, creator_id=creator_id, name=f"B{bid}",
        python_code="# code", is_default=is_default,
    )
    db.add(behavior)
    db.commit()
    return behavior
 
 
def make_player(db, owner_id, pid):
    player = models.Player(
        player_id=pid, owner_id=owner_id, shirt_number=pid, name=f"Jugador {pid}",
        power=1, agility=1, control=1, speed=1, strength=1,
    )
    db.add(player)
    db.commit()
    return player
 
 
@pytest.fixture
def usuario_con_jugadores(db):
    user = make_user(db)
    make_behavior(db, 0)
    make_behavior(db, 5, creator_id=user.id, is_default=False)
    for pid in range(7, 13):
        make_player(db, user.id, pid)
    return user
 
 
# ---------- get_user ----------
 
def test_get_user_existente(db):
    user = make_user(db)
 
    assert repo.get_user(db, user.id).email == "juan@gmail.com"
 
 
def test_get_user_inexistente(db):
    assert repo.get_user(db, 999) is None
 
 
# ---------- get_players_by_ids ----------
 
def test_get_players_by_ids_devuelve_solo_los_pedidos(db, usuario_con_jugadores):
    players = repo.get_players_by_ids(db, ids=[7, 9])
 
    assert sorted(p.player_id for p in players) == [7, 9]
 
 
def test_get_players_by_ids_ignora_los_inexistentes(db, usuario_con_jugadores):
    players = repo.get_players_by_ids(db, ids=[7, 999])
 
    assert [p.player_id for p in players] == [7]
 
 
# ---------- get_behaviors_by_ids ----------
 
def test_get_behaviors_by_ids_devuelve_solo_los_pedidos(db, usuario_con_jugadores):
    make_behavior(db, 6, creator_id=usuario_con_jugadores.id, is_default=False)
 
    behaviors = repo.get_behaviors_by_ids(db, ids=[0, 5])
 
    assert sorted(b.id_behavior for b in behaviors) == [0, 5]
 
 
def test_get_behaviors_by_ids_ignora_los_inexistentes(db, usuario_con_jugadores):
    behaviors = repo.get_behaviors_by_ids(db, ids=[0, 999])
 
    assert [b.id_behavior for b in behaviors] == [0]
 
 
# ---------- get_team_by_owner_and_name ----------
 
def test_get_team_by_owner_and_name_existente(db):
    user = make_user(db)
    team = repo.add_team(db, owner_id=user.id, name="Mi Equipo", starters=[], substitutes=[])
 
    found = repo.get_team_by_owner_and_name(db, owner_id=user.id, name="Mi Equipo")
 
    assert found.team_id == team.team_id
 
 
def test_get_team_by_owner_and_name_de_otro_usuario(db):
    user = make_user(db)
    otro = make_user(db, club="pedro", email="pedro@gmail.com")
    repo.add_team(db, owner_id=user.id, name="Mi Equipo", starters=[], substitutes=[])
 
    assert repo.get_team_by_owner_and_name(db, owner_id=otro.id, name="Mi Equipo") is None
 
 
def test_get_team_by_owner_and_name_otro_nombre(db):
    user = make_user(db)
    repo.add_team(db, owner_id=user.id, name="Mi Equipo", starters=[], substitutes=[])
 
    assert repo.get_team_by_owner_and_name(db, owner_id=user.id, name="Otro") is None
 
 
def test_get_team_by_owner_and_name_distingue_mayusculas(db):
    # La busqueda es por nombre exacto: "Mi Equipo" y "mi equipo" son distintos
    user = make_user(db)
    repo.add_team(db, owner_id=user.id, name="Mi Equipo", starters=[], substitutes=[])
 
    assert repo.get_team_by_owner_and_name(db, owner_id=user.id, name="mi equipo") is None
 
 
# ---------- add_team ----------
 
def test_add_team_crea_el_equipo(db, usuario_con_jugadores):
    team = repo.add_team(
        db, owner_id=usuario_con_jugadores.id, name="Mi Equipo",
        starters=[(7, 0), (8, 0), (9, 0)],
        substitutes=[(10, 0), (11, 0), (12, 0)],
    )
 
    assert team.team_id is not None
    assert team.name == "Mi Equipo"
    assert team.owner_id == usuario_con_jugadores.id
    assert db.query(models.Team).count() == 1
 
 
def test_add_team_asigna_el_equipo_a_los_jugadores(db, usuario_con_jugadores):
    team = repo.add_team(
        db, owner_id=usuario_con_jugadores.id, name="Mi Equipo",
        starters=[(7, 0), (8, 0), (9, 0)],
        substitutes=[(10, 0), (11, 0), (12, 0)],
    )
 
    assert all(p.team_id == team.team_id for p in db.query(models.Player).all())
    assert len(team.players) == 6
 
 
def test_add_team_marca_titulares_y_suplentes(db, usuario_con_jugadores):
    repo.add_team(
        db, owner_id=usuario_con_jugadores.id, name="Mi Equipo",
        starters=[(7, 0), (8, 0), (9, 0)],
        substitutes=[(10, 0), (11, 0), (12, 0)],
    )
 
    por_id = {p.player_id: p for p in db.query(models.Player).all()}
    assert [por_id[i].is_starter for i in (7, 8, 9)] == [True, True, True]
    assert [por_id[i].is_starter for i in (10, 11, 12)] == [False, False, False]
 
 
def test_add_team_asigna_el_behavior_de_cada_jugador(db, usuario_con_jugadores):
    repo.add_team(
        db, owner_id=usuario_con_jugadores.id, name="Mi Equipo",
        starters=[(7, 5), (8, 0), (9, 0)],
        substitutes=[(10, 0), (11, 0), (12, 5)],
    )
 
    por_id = {p.player_id: p for p in db.query(models.Player).all()}
    assert por_id[7].behavior_id == 5
    assert por_id[8].behavior_id == 0
    assert por_id[12].behavior_id == 5
 
 
def test_add_team_no_toca_a_los_otros_jugadores(db, usuario_con_jugadores):
    make_player(db, usuario_con_jugadores.id, 99)   # no esta en el equipo
 
    repo.add_team(
        db, owner_id=usuario_con_jugadores.id, name="Mi Equipo",
        starters=[(7, 0), (8, 0), (9, 0)],
        substitutes=[(10, 0), (11, 0), (12, 0)],
    )
 
    ajeno = db.get(models.Player, 99)
    assert ajeno.team_id is None
    assert not ajeno.is_starter
 
 
def test_add_team_jugador_inexistente_hace_rollback(db, usuario_con_jugadores):
    with pytest.raises(Exception):
        repo.add_team(
            db, owner_id=usuario_con_jugadores.id, name="Mi Equipo",
            starters=[(7, 0), (8, 0), (999, 0)],   # el 999 no existe
            substitutes=[],
        )
 
    assert db.query(models.Team).count() == 0          # el equipo no quedo
    assert db.get(models.Player, 7).team_id is None    # ni los jugadores ya asignados
 
 
def test_add_team_nombre_duplicado_para_el_mismo_usuario(db, usuario_con_jugadores):
    user = usuario_con_jugadores
    repo.add_team(db, owner_id=user.id, name="Mi Equipo", starters=[], substitutes=[])
 
    with pytest.raises(IntegrityError):
        repo.add_team(db, owner_id=user.id, name="Mi Equipo", starters=[], substitutes=[])
 
    assert db.query(models.Team).count() == 1   # y la sesion sigue usable (hubo rollback)
 
 
def test_add_team_mismo_nombre_para_usuarios_distintos(db, usuario_con_jugadores):
    otro = make_user(db, club="pedro", email="pedro@gmail.com")
    repo.add_team(db, owner_id=usuario_con_jugadores.id, name="Mi Equipo", starters=[], substitutes=[])
 
    repo.add_team(db, owner_id=otro.id, name="Mi Equipo", starters=[], substitutes=[])
 
    assert db.query(models.Team).count() == 2

@pytest.fixture
def db():
    """BD en memoria para tests de repository."""
    engine = create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_get_players_devuelve_jugadores_del_usuario(db):
    # Crear dos usuarios
    user1 = models.User(
        club="club1", name="User1", email="user1@test.com", password_hash="hash"
    )
    user2 = models.User(
        club="club2", name="User2", email="user2@test.com", password_hash="hash"
    )
    db.add_all([user1, user2])
    db.commit()

    # Crear jugadores para user1 y user2
    p1 = models.Player(
        name="Jugador 1", owner_id=user1.id, shirt_number=10,
        power=60, agility=60, control=60, speed=60, strength=60,
    )
    p2 = models.Player(
        name="Jugador 2", owner_id=user1.id, shirt_number=11,
        power=60, agility=60, control=60, speed=60, strength=60,
    )
    p3 = models.Player(
        name="Jugador 3", owner_id=user2.id, shirt_number=12,
        power=60, agility=60, control=60, speed=60, strength=60,
    )
    db.add_all([p1, p2, p3])
    db.commit()

    # get_players debe devolver solo los de user1
    result = repo.get_players(db, user1.id)

    assert len(result) == 2
    assert all(p.owner_id == user1.id for p in result)
    assert {p.name for p in result} == {"Jugador 1", "Jugador 2"}


def test_get_players_usuario_sin_jugadores(db):
    user = models.User(
        club="vacio", name="User", email="empty@test.com", password_hash="hash"
    )
    db.add(user)
    db.commit()

    result = repo.get_players(db, user.id)

    assert result == []


def test_get_players_usuario_inexistente(db):
    result = repo.get_players(db, 999)

    assert result == []
    
    
def make_user(db, club="juan", email="juan@gmail.com"):
    """Crea un usuario de prueba."""
    user = models.User(
        club=club, 
        name="Juan",
        email=email, 
        password_hash="hash", 
        avatar=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
 
# ============================== create_player

def make_player_in(name="Lionel Messi", shirt_number=10, **pacss):
    attrs = dict(power=60, agility=60, control=60, speed=60, strength=60) | pacss
    return schemas.PlayerIn(
        name=name,
        shirt_number=shirt_number,
        pacss_attributes=schemas.PacssAttributes(**attrs),
    )

def test_create_player_ok(db):
    user = make_user(db)

    p = repo.create_player(
        db, user.id,
        make_player_in(power=90, agility=50, control=50, speed=60, strength=50),
    )

    assert p.player_id is not None
    assert p.name == "Lionel Messi"
    assert p.shirt_number == 10
    assert p.owner_id == user.id
    # el pacss anidado se guarda en columnas planas
    assert (p.power, p.agility, p.control, p.speed, p.strength) == (90, 50, 50, 60, 50)
    assert p.behavior_id == 0      # default
    assert p.team_id is None
    assert p.is_starter is False


def test_create_player_persiste_en_la_base(db):
    user = make_user(db)

    p = repo.create_player(db, user.id, make_player_in(name="Cristiano Ronaldo", shirt_number=7))

    retrieved = db.query(models.Player).filter_by(player_id=p.player_id).first()
    assert retrieved is not None
    assert retrieved.name == "Cristiano Ronaldo"
    assert retrieved.shirt_number == 7


def test_create_player_multiples_para_mismo_usuario(db):
    user = make_user(db)

    for i in range(3):
        repo.create_player(db, user.id, make_player_in(name=f"Jugador {i}", shirt_number=i + 1))

    players = db.query(models.Player).filter_by(owner_id=user.id).all()
    assert len(players) == 3


def test_create_player_shirt_number_limites(db):
    user = make_user(db)

    p1 = repo.create_player(db, user.id, make_player_in(name="Uno", shirt_number=1))
    p99 = repo.create_player(db, user.id, make_player_in(name="Noventa y nueve", shirt_number=99))

    assert p1.shirt_number == 1
    assert p99.shirt_number == 99

# --------------   TESTS DE PARTIDOS AMISTOSOS   --------------

def make_match(db, home_team_id, is_friendly=True, match_duration=3, status="open"):
    return repo.create_match(
        db,
        is_friendly=is_friendly,
        status=status,
        home_team_id=home_team_id,
        away_team_id=None,
        match_duration=match_duration,
        is_private=False,
        password=None,
        current_period=0,
        league_id=None,
        scheduled_at=None,
    )


def test_create_match_friendly_lo_guarda(db, usuario_con_jugadores):
    # 1. Creamos un equipo valido en la base para poder asociarlo al partido
    team = repo.add_team(
        db, owner_id=usuario_con_jugadores.id, name="Mi Equipo",
        starters=[(7, 0), (8, 0), (9, 0)],
        substitutes=[(10, 0), (11, 0), (12, 0)],
    )

    # 2. Creamos el partido amistoso usando el repositorio
    match = make_match(db, home_team_id=team.team_id, match_duration=3)

    # 3. Verificaciones en la base de datos real de pruebas
    assert match.id_match is not None
    assert match.is_friendly is True
    assert match.home_team_id == team.team_id
    assert match.match_duration == 3
    assert match.status == "open"
    assert db.query(models.Match).count() == 1  

# --------------   TESTS DE AMISTOSOS   --------------

def make_match(db, home_team_id, **over):
    data = dict(home_team_id=home_team_id, match_duration=10, is_friendly=True, status="open")
    data.update(over)
    match = models.Match(**data)
    db.add(match)
    db.commit()
    return match


@pytest.fixture
def equipo_local(db):
    user = make_user(db)
    return repo.add_team(db, owner_id=user.id, name="Mi Equipo", starters=[], substitutes=[])


def test_get_open_friendly_matches_devuelve_solo_amistosos_abiertos(db, equipo_local):
    abierto = make_match(db, equipo_local.team_id)
    make_match(db, equipo_local.team_id, status="started")
    make_match(db, equipo_local.team_id, status="cancelled")
    make_match(db, equipo_local.team_id, is_friendly=False)   # partido de liga

    result = repo.get_open_friendly_matches(db)

    assert [m.id_match for m in result] == [abierto.id_match]


def test_get_open_friendly_matches_sin_partidos(db):
    assert repo.get_open_friendly_matches(db) == []


def test_get_open_friendly_matches_incluye_los_privados(db, equipo_local):
    make_match(db, equipo_local.team_id, is_private=True)

    result = repo.get_open_friendly_matches(db)

    assert len(result) == 1
    assert result[0].is_private is True


def test_get_open_friendly_matches_ordenados_por_id(db, equipo_local):
    ids = [make_match(db, equipo_local.team_id).id_match for _ in range(3)]

    result = repo.get_open_friendly_matches(db)

    assert [m.id_match for m in result] == ids


def test_get_open_friendly_matches_trae_los_datos_del_partido(db, equipo_local):
    make_match(db, equipo_local.team_id, match_duration=15)

    match = repo.get_open_friendly_matches(db)[0]

    assert match.home_team_id == equipo_local.team_id
    assert match.match_duration == 15
    assert match.away_team_id is None   # espera rival