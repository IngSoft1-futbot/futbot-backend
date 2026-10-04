import pytest
from pydantic import ValidationError
from types import SimpleNamespace
from src import schemas


def make(**over):
    data = {
        "club": "juan",
        "name": "Juan",
        "email": "juan@gmail.com",
        "password": "Clave123!",
    }
    data.update(over)
    return schemas.UserCreate(**data)


def test_usuario_valido():
    user = make()
    assert user.club == "juan"


def test_avatar_es_opcional():
    assert make().avatar is None


def test_club_se_recorta():
    assert make(club="  juan  ").club == "juan"


@pytest.mark.parametrize("club", ["ab", "   ", "a" * 51])
def test_club_invalido(club):
    with pytest.raises(ValidationError):
        make(club=club)


@pytest.mark.parametrize("name", ["", "   ", "a" * 51])
def test_name_invalido(name):
    with pytest.raises(ValidationError):
        make(name=name)


@pytest.mark.parametrize("email", ["hola", "a@", "@gmail.com"])
def test_email_invalido(email):
    with pytest.raises(ValidationError):
        make(email=email)


def test_falta_password():
    with pytest.raises(ValidationError):
        schemas.UserCreate(club="juan", name="Juan", email="juan@gmail.com")


def test_schema_no_valida_la_fuerza_de_la_password():
    # Es responsabilidad de utils.password_validation, no de Pydantic
    assert make(password="abc").password == "abc"


# --------------   TESTS DE LOGIN   --------------

def make_login(**over):
    data = {
        "email": "joaco2@gmail.com",
        "password": "Pass1234!",
    }
    data.update(over)
    return schemas.LoginRequest(**data)


def test_login_valido():
    login_data = make_login()
    assert login_data.email == "joaco2@gmail.com"
    assert login_data.password == "Pass1234!"


@pytest.mark.parametrize("email", ["hola", "a@", "@gmail.com", "correoSinArroba"])
def test_login_email_invalido(email):
    with pytest.raises(ValidationError):
        make_login(email=email)


def test_login_falta_email():
    with pytest.raises(ValidationError):
        schemas.LoginRequest(password="Pass1234!")


def test_login_falta_password():
    with pytest.raises(ValidationError):
        schemas.LoginRequest(email="joaco2@gmail.com")

# --------------   TESTS DE EQUIPOS   --------------
 
TEAM = {
    "name": "Mi Equipo",
    "jugadores_titulares": [
        {"player_id": 7, "behavior_id": 0},
        {"player_id": 8},
        {"player_id": 9},
    ],
    "jugadores_suplentes": [
        {"player_id": 10},
        {"player_id": 11},
        {"player_id": 12},
    ],
}
 
 
# ---------- PlayerAssignment ----------
 
def test_player_assignment_behavior_es_opcional():
    p = schemas.PlayerAssignment(player_id=7)
 
    assert p.player_id == 7
    assert p.behavior_id is None   # utils lo resuelve al default (0)
 
 
def test_player_assignment_con_behavior():
    assert schemas.PlayerAssignment(player_id=7, behavior_id=5).behavior_id == 5
 
 
def test_player_assignment_falta_player_id():
    with pytest.raises(ValidationError):
        schemas.PlayerAssignment(behavior_id=5)
 
 
@pytest.mark.parametrize("campo", ["player_id", "behavior_id"])
def test_player_assignment_ids_no_numericos(campo):
    with pytest.raises(ValidationError):
        schemas.PlayerAssignment(**{"player_id": 7, "behavior_id": 5, campo: "abc"})
 
 
# ---------- TeamCreate ----------
 
def test_team_create_valido():
    team = schemas.TeamCreate(**TEAM)
 
    assert team.name == "Mi Equipo"
    assert len(team.jugadores_titulares) == 3
    assert len(team.jugadores_suplentes) == 3
    assert team.jugadores_titulares[0].behavior_id == 0
    assert team.jugadores_titulares[1].behavior_id is None
 
 
def test_team_name_se_recorta():
    assert schemas.TeamCreate(**{**TEAM, "name": "  Mi Equipo  "}).name == "Mi Equipo"
 
 
@pytest.mark.parametrize("name", ["abc", "a" * 30])   # justo en los limites
def test_team_name_limites_validos(name):
    assert schemas.TeamCreate(**{**TEAM, "name": name}).name == name
 
 
@pytest.mark.parametrize("name", ["", "   ", "ab", " ab ", "a" * 31])
def test_team_name_invalido(name):
    with pytest.raises(ValidationError):
        schemas.TeamCreate(**{**TEAM, "name": name})
 
 
@pytest.mark.parametrize("campo", ["name", "jugadores_titulares"])
def test_team_create_falta_campo_obligatorio(campo):
    data = {k: v for k, v in TEAM.items() if k != campo}
 
    with pytest.raises(ValidationError):
        schemas.TeamCreate(**data)
 
 
def test_suplentes_es_opcional_y_queda_vacio():
    data = {k: v for k, v in TEAM.items() if k != "jugadores_suplentes"}
 
    assert schemas.TeamCreate(**data).jugadores_suplentes == []
 
 
def test_jugador_sin_player_id_dentro_de_la_lista():
    with pytest.raises(ValidationError):
        schemas.TeamCreate(**{**TEAM, "jugadores_suplentes": [{}]})
 
 
def test_schema_no_valida_la_composicion_del_equipo():
    # El "3 titulares + 3 suplentes" se valida en utils, no en el schema
    team = schemas.TeamCreate(name="Mi Equipo", jugadores_titulares=[{"player_id": 7}])
 
    assert len(team.jugadores_titulares) == 1
    assert team.jugadores_suplentes == []
 
 
# ---------- PlayerIn ----------

PLAYER_IN = {
    "name": "Jugador",
    "shirt_number": 10,
    "pacss_attributes": {"power": 60, "agility": 60, "control": 60,
                         "speed": 60, "strength": 60},
}


def test_player_in_valido():
    p = schemas.PlayerIn(**PLAYER_IN)

    assert p.shirt_number == 10


@pytest.mark.parametrize("campo", ["name", "shirt_number", "pacss_attributes"])
def test_player_in_falta_campo_obligatorio(campo):
    data = {k: v for k, v in PLAYER_IN.items() if k != campo}

    with pytest.raises(ValidationError):
        schemas.PlayerIn(**data)


def test_player_in_atributo_faltante():
    data = {**PLAYER_IN, "pacss_attributes": {"power": 60, "agility": 60}}

    with pytest.raises(ValidationError):
        schemas.PlayerIn(**data)


# ---------- PlayerOut ----------

def test_player_out_se_construye_desde_un_objeto_orm():
        orm_player = SimpleNamespace(
        player_id=7, name="Lionel Messi", shirt_number=10, behavior_id=0,
        team_id=None, owner_id=1,                  # owner_id sobra: se ignora
        power=90, agility=95, control=60, speed=30, strength=25,
    )


def test_player_out_acepta_pacss_ya_anidado():
    out = schemas.PlayerOut(
        player_id=7, name="X", shirt_number=10,
        pacss_attributes=schemas.PacssAttributes(
            power=60, agility=60, control=60, speed=60, strength=60),
    )

    assert out.behavior_id == 0      # default
    assert out.team_id is None

# --------------   TESTS DE PARTIDOS AMISTOSOS   --------------
 
FRIENDLY_MATCH = {
    "team_name": "Mi Equipo",
    "match_duration": 3,
}
 
 
def test_friendly_match_create_valido():
    match_in = schemas.FriendlyMatchCreate(**FRIENDLY_MATCH)
 
    assert match_in.team_name == "Mi Equipo"
    assert match_in.match_duration == 3
 
 
@pytest.mark.parametrize("campo", ["team_name", "match_duration"])
def test_friendly_match_create_falta_campo_obligatorio(campo):
    data = {k: v for k, v in FRIENDLY_MATCH.items() if k != campo}
 
    with pytest.raises(ValidationError):
        schemas.FriendlyMatchCreate(**data)
 
 
@pytest.mark.parametrize("campo, valor_invalido", [
    ("match_duration", "tres"),
])
def test_friendly_match_create_tipos_invalidos(campo, valor_invalido):
    data = {**FRIENDLY_MATCH, campo: valor_invalido}
 
    with pytest.raises(ValidationError):
        schemas.FriendlyMatchCreate(**data)