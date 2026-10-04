from unittest.mock import patch, MagicMock
from src.app import app, get_current_user_id
from src.database import get_db
from fastapi.testclient import TestClient
import pytest

from src import schemas

VALID = {
    "club": "juan",
    "name": "Juan Perez",
    "email": "juan@gmail.com",
    "password": "Clave123!",
    "avatar": "avatar1",
}

FAKE_USER = {
    "id": 1,
    "club": "juan",
    "name": "Juan Perez",
    "email": "juan@gmail.com",
    "avatar": "avatar1",
    "created_at": "2026-01-01T00:00:00Z",
}

TEAM_BODY = {
    "name": "Mi Equipo",
    "jugadores_titulares": [
        {"player_id": 7, "behavior_id": 0},
        {"player_id": 8, "behavior_id": 0},
        {"player_id": 9},  # sin behavior_id -> opcional
    ],
    "jugadores_suplentes": [
        {"player_id": 10, "behavior_id": 0},
        {"player_id": 11, "behavior_id": 0},
        {"player_id": 12, "behavior_id": 0},
    ],
}
 
PACSS = {"power": 60, "agility": 60, "control": 60, "speed": 60, "strength": 60}

PLAYER_BODY = {
    "name": "Lionel Messi",
    "shirt_number": 10,
    "pacss_attributes": PACSS,
    "team_id": None,
}

FAKE_PLAYER = {
    "player_id": 7,
    "name": "Lionel Messi",
    "shirt_number": 10,
    "behavior_id": 0,
    "pacss_attributes": PACSS,
    "team_id": None,
}

FAKE_PLAYERS = [
    {
        "player_id": 7,
        "name": "Lionel Messi",
        "shirt_number": 10,
        "behavior_id": 0,
        "pacss_attributes": PACSS,
        "team_id": None,
    },
    {
        "player_id": 8,
        "name": "Cristiano Ronaldo",
        "shirt_number": 9,
        "behavior_id": 0,
        "pacss_attributes": PACSS,
        "team_id": None,
    },
]

FAKE_TEAM = {
    "team_id": 1,
    "name": "Mi Equipo",
    "jugadores_titulares": [
        {"player_id": 7, "name": "Lionel Messi", "shirt_number": 10, "behavior_id": 0, "pacss_attributes": PACSS},
        {"player_id": 8, "name": "Cristiano Ronaldo", "shirt_number": 9, "behavior_id": 0, "pacss_attributes": PACSS},
        {"player_id": 9, "name": "Erling Haaland", "shirt_number": 8, "behavior_id": 0, "pacss_attributes": PACSS},
    ],
    "jugadores_suplentes": [
        {"player_id": 10, "name": "Kevin De Bruyne", "shirt_number": 7, "behavior_id": 0, "pacss_attributes": PACSS},
        {"player_id": 11, "name": "Virgil van Dijk", "shirt_number": 6, "behavior_id": 0, "pacss_attributes": PACSS},
        {"player_id": 12, "name": "Emiliano Martinez", "shirt_number": 5, "behavior_id": 0, "pacss_attributes": PACSS},
    ],
}

@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: MagicMock()
    app.dependency_overrides[get_current_user_id] = lambda: 1
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def utils_mock():
    with patch("src.app.utils") as mock:
        yield mock


def test_register_ok(client, utils_mock):
    utils_mock.register_user.return_value = FAKE_USER

    r = client.post("/auth/register", json=VALID)

    assert r.status_code == 201
    body = r.json()
    assert body["club"] == "juan"
    assert "password" not in body
    assert "password_hash" not in body
    utils_mock.register_user.assert_called_once()


def test_register_sin_avatar_es_valido(client, utils_mock):
    utils_mock.register_user.return_value = {**FAKE_USER, "avatar": None}
    body = {k: v for k, v in VALID.items() if k != "avatar"}

    r = client.post("/auth/register", json=body)

    assert r.status_code == 201


def test_register_email_duplicado(client, utils_mock):
    utils_mock.register_user.side_effect = schemas.EmailAlreadyExistsError

    r = client.post("/auth/register", json=VALID)

    assert r.status_code == 400
    assert r.json()["detail"] == "Email already in use."


def test_register_club_duplicado(client, utils_mock):
    utils_mock.register_user.side_effect = schemas.ClubAlreadyExistsError

    r = client.post("/auth/register", json=VALID)

    assert r.status_code == 400
    assert r.json()["detail"] == "Club already in use."


def test_register_password_invalida(client, utils_mock):
    utils_mock.register_user.side_effect = schemas.PasswordValidationError(
        "Password must contain at least one digit."
    )

    r = client.post("/auth/register", json=VALID)

    assert r.status_code == 400
    assert r.json()["detail"] == "Password must contain at least one digit."


def test_register_conflicto_concurrente(client, utils_mock):
    utils_mock.register_user.side_effect = schemas.RegistrationError

    r = client.post("/auth/register", json=VALID)

    assert r.status_code == 409
    assert r.json()["detail"] == "Conflict in register time."


@pytest.mark.parametrize("campo", ["club", "name", "email", "password"])
def test_register_falta_campo_obligatorio(client, utils_mock, campo):
    body = {k: v for k, v in VALID.items() if k != campo}

    r = client.post("/auth/register", json=body)

    assert r.status_code == 422
    utils_mock.register_user.assert_not_called()


def test_register_email_con_formato_invalido(client, utils_mock):
    r = client.post("/auth/register", json={**VALID, "email": "hola"})

    assert r.status_code == 422
    utils_mock.register_user.assert_not_called()

# --------------   TESTS DE LOGIN   --------------

def test_login_endpoint_exitoso(client, utils_mock):
    # Simulamos que la utilidad valida y devuelve el token de acceso
    utils_mock.authenticate_and_create_token.return_value = "abc123token"

    response = client.post("/auth/login", json={
        "email": "joaco3@gmail.com",
        "password": "Pass1234!"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Login successful."
    assert "access_token" in data["data"]
    assert data["data"]["access_token"] == "abc123token"
    utils_mock.authenticate_and_create_token.assert_called_once()


def test_login_endpoint_credenciales_invalidas(client, utils_mock):
    # Simulamos que la autenticación falla y devuelve None
    utils_mock.authenticate_and_create_token.return_value = None

    response = client.post("/auth/login", json={
        "email": "joaco3@gmail.com",
        "password": "PasswordMala1!"
    })
    
    assert response.status_code == 401
    data = response.json()
    assert "message" in data
    assert data["message"] == "Invalid email or password."
    utils_mock.authenticate_and_create_token.assert_called_once()


def test_login_endpoint_email_invalido_por_pydantic(client, utils_mock):
    # Aca no hace falta mockear nada porque Pydantic frena la peticion antes
    response = client.post("/auth/login", json={
        "email": "correoInvalidoSinArroba",
        "password": "Pass1234!"
    })
    
    assert response.status_code == 422
    utils_mock.authenticate_and_create_token.assert_not_called()
    
    
#------------------------------------------Crear Jugador------------------------------------------


def test_create_player_ok(client, utils_mock):
    utils_mock.create_player.return_value = FAKE_PLAYER

    r = client.post("/users/1/players", json=PLAYER_BODY)

    assert r.status_code == 201
    body = r.json()
    assert body["player_id"] == 7
    assert body["shirt_number"] == 10
    assert body["pacss_attributes"]["power"] == 60
    utils_mock.create_player.assert_called_once()


def test_create_player_pasa_user_id_y_schema_a_utils(client, utils_mock):
    app.dependency_overrides[get_current_user_id] = lambda: 42
    utils_mock.create_player.return_value = FAKE_PLAYER

    client.post("/users/42/players", json=PLAYER_BODY)

    _, user_id, player_in = utils_mock.create_player.call_args.args
    assert user_id == 42
    assert isinstance(player_in, schemas.PlayerIn)
    assert player_in.shirt_number == 10


def test_create_player_sin_shirt_number_es_422(client, utils_mock):
    body = {k: v for k, v in PLAYER_BODY.items() if k != "shirt_number"}

    r = client.post("/users/1/players", json=body)

    assert r.status_code == 422        # antes era un 500 por NotNullViolation
    utils_mock.create_player.assert_not_called()


@pytest.mark.parametrize(
    "error, status_code, detail",
    [
        (schemas.UserNotFoundError, 404, "User could not be found."),
        (schemas.PointAssignmentError, 400, "Points must total 300, each between 20 and 100."),
    ],
)
def test_create_player_errores_de_negocio(client, utils_mock, error, status_code, detail):
    utils_mock.create_player.side_effect = error

    r = client.post("/users/1/players", json=PLAYER_BODY)

    assert r.status_code == status_code
    assert r.json()["detail"] == detail

def test_create_player_token_de_otro_usuario(client, utils_mock):
    r = client.post("/users/2/players", json=PLAYER_BODY)

    assert r.status_code == 403
    utils_mock.create_player.assert_not_called()
    
#------------------------------------------Crear Equipo------------------------------------------
 
def test_create_team_ok(client, utils_mock):
    utils_mock.create_team.return_value = FAKE_TEAM
 
    r = client.post("/users/1/teams", json=TEAM_BODY)
 
    assert r.status_code == 201
    body = r.json()
    assert body["team_id"] == 1
    assert body["name"] == "Mi Equipo"
    assert len(body["jugadores_titulares"]) == 3
    assert len(body["jugadores_suplentes"]) == 3
    utils_mock.create_team.assert_called_once()
 
 
def test_create_team_pasa_user_id_y_schema_a_utils(client, utils_mock):
    app.dependency_overrides[get_current_user_id] = lambda: 42
    utils_mock.create_team.return_value = FAKE_TEAM 
    client.post("/users/42/teams", json=TEAM_BODY)
 
    _, user_id, team_in = utils_mock.create_team.call_args.args
    assert user_id == 42
    assert isinstance(team_in, schemas.TeamCreate)
    assert team_in.name == "Mi Equipo"
    assert team_in.jugadores_titulares[2].behavior_id is None  # default
 
 
@pytest.mark.parametrize(
    "error, status_code, detail",
    [
        (schemas.UserNotFoundError, 404, "User can not find."),
        (schemas.PlayerNotFoundError, 404, "Player can not find."),
        (schemas.BehaviorNotFoundError, 404, "Behavior can not find."),
        (schemas.PlayerNotAuthorizedError, 403, "User is not the owner of the player."),
        (schemas.BehaviorNotAuthorizedError, 403, "User is not the owner of the behavior."),
        (schemas.TeamNameAlreadyInUseError, 400, "Team name already in use for this user."),
        (schemas.TeamIncompleteError, 400, "Team incomplete, must be 3 starters & 3 subtitutes."),
        (schemas.PlayerAlreadyInUseError, 400, "Some players are already in use."),
        (schemas.CreateTeamError, 409, "Conflict in creation time."),
    ],
)
def test_create_team_errores_de_negocio(client, utils_mock, error, status_code, detail):
    utils_mock.create_team.side_effect = error
 
    r = client.post("/users/1/teams", json=TEAM_BODY)
 
    assert r.status_code == status_code
    assert r.json()["detail"] == detail
 
 
@pytest.mark.parametrize("campo", ["name", "jugadores_titulares"])
def test_create_team_falta_campo_obligatorio(client, utils_mock, campo):
    body = {k: v for k, v in TEAM_BODY.items() if k != campo}
 
    r = client.post("/users/1/teams", json=body)
 
    assert r.status_code == 422
    utils_mock.create_team.assert_not_called()
 
 
def test_create_team_user_id_no_numerico(client, utils_mock):
    r = client.post("/users/abc/teams", json=TEAM_BODY)
 
    assert r.status_code == 422
    utils_mock.create_team.assert_not_called()
 
 
def test_create_team_sin_token(client, utils_mock):
    app.dependency_overrides.pop(get_current_user_id)
 
    r = client.post("/users/1/teams", json=TEAM_BODY)
 
    assert r.status_code in (401, 403)   # depende de la version de FastAPI
    utils_mock.create_team.assert_not_called()
 
 
def test_create_team_token_invalido(client, utils_mock):
    app.dependency_overrides.pop(get_current_user_id)
    utils_mock.verify_jwt_token.side_effect = schemas.InvalidTokenError
 
    r = client.post("/users/1/teams", json=TEAM_BODY, headers={"Authorization": "Bearer basura"})
 
    assert r.status_code == 401
    utils_mock.create_team.assert_not_called()
 
 
def test_create_team_token_de_otro_usuario(client, utils_mock):
    r = client.post("/users/2/teams", json=TEAM_BODY)   # el token simulado es del usuario 1
 
    assert r.status_code == 403
    utils_mock.create_team.assert_not_called()
 
#------------------------------------------Obtener Jugadores------------------------------------------


def test_get_players_ok(client, utils_mock):
    utils_mock.get_players.return_value = FAKE_PLAYERS

    r = client.get("/users/1/players")

    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 2
    assert body[0]["player_id"] == 7
    assert body[1]["player_id"] == 8
    assert all("pacss_attributes" in p for p in body)
    utils_mock.get_players.assert_called_once()


def test_get_players_lista_vacia(client, utils_mock):
    utils_mock.get_players.return_value = []

    r = client.get("/users/1/players")

    assert r.status_code == 200
    body = r.json()
    assert body == []


def test_get_players_pasa_user_id_a_utils(client, utils_mock):
    app.dependency_overrides[get_current_user_id] = lambda: 42
    utils_mock.get_players.return_value = []

    client.get("/users/42/players")

    _, user_id = utils_mock.get_players.call_args.args
    assert user_id == 42


def test_get_players_usuario_inexistente(client, utils_mock):
    utils_mock.get_players.side_effect = schemas.UserNotFoundError

    r = client.get("/users/1/players")

    assert r.status_code == 404
    assert r.json()["detail"] == "User could not be found."


def test_get_players_token_de_otro_usuario(client, utils_mock):
    r = client.get("/users/2/players")

    assert r.status_code == 403
    assert r.json()["detail"] == "Not allowed to view players of another user."
    utils_mock.get_players.assert_not_called()


def test_get_players_sin_token(client, utils_mock):
    app.dependency_overrides.pop(get_current_user_id)

    r = client.get("/users/1/players")

    assert r.status_code in (401, 403)
    utils_mock.get_players.assert_not_called()

#------------------------------------------Crear Partido Amistoso------------------------------------------

FAKE_FRIENDLY_MATCH = {
    "id_match": 10,
    "is_friendly": True,
    "status": "open",
    "home_team_id": 1,
    "away_team_id": None,
    "match_duration": 3,
    "is_private": False,
    "password": None,
    "current_period": 0,
    "league_id": None,
    "scheduled_at": None,
}

FRIENDLY_MATCH_BODY = {
    "team_name": "Mi Equipo",
    "match_duration": 3,
}


def test_create_friendly_match_ok(client, utils_mock):
    utils_mock.create_friendly_match.return_value = FAKE_FRIENDLY_MATCH

    r = client.post("/users/1/friendly-matches", json=FRIENDLY_MATCH_BODY)

    assert r.status_code == 201
    body = r.json()
    assert body["id_match"] == 10
    assert body["is_friendly"] is True
    assert body["home_team_id"] == 1
    utils_mock.create_friendly_match.assert_called_once()


@pytest.mark.parametrize(
    "error, status_code, detail",
    [
        (schemas.UserNotFoundError, 404, "User not found."),
        (schemas.TeamNotFoundError, 404, "Team not found or does not belong to the user."),
        (schemas.InvalidDurationError("Match duration must be between 1 and 5 minutes."), 400, "Match duration must be between 1 and 5 minutes."),
        (schemas.TeamIncompleteError, 400, "Team incomplete, must have exactly 3 starters."),
        (schemas.CreateMatchError, 409, "Conflict in match creation."),
    ],
)
def test_create_friendly_match_errores_de_negocio(client, utils_mock, error, status_code, detail):
    utils_mock.create_friendly_match.side_effect = error

    r = client.post("/users/1/friendly-matches", json=FRIENDLY_MATCH_BODY)

    assert r.status_code == status_code
    assert r.json()["detail"] == detail


@pytest.mark.parametrize("campo", ["team_name", "match_duration"])
def test_create_friendly_match_falta_campo_obligatorio(client, utils_mock, campo):
    body = {k: v for k, v in FRIENDLY_MATCH_BODY.items() if k != campo}

    r = client.post("/users/1/friendly-matches", json=body)

    assert r.status_code == 422
    utils_mock.create_friendly_match.assert_not_called()


def test_create_friendly_match_token_de_otro_usuario(client, utils_mock):
    # Como ya no hay user_id en el body, pasamos directamente FRIENDLY_MATCH_BODY limpio
    r = client.post("/users/2/friendly-matches", json=FRIENDLY_MATCH_BODY)

    assert r.status_code == 403
    assert r.json()["detail"] == "Not allowed to create matches for another user."
    utils_mock.create_friendly_match.assert_not_called()


# --------------   TESTS DE AMISTOSOS   --------------

FAKE_FRIENDLIES = [
    {"id_match": 1, "home_team_id": 3, "match_duration": 10, "is_private": False},
    {"id_match": 2, "home_team_id": 4, "match_duration": 15, "is_private": True},
]


def test_friendly_matches_ok(client, utils_mock):
    utils_mock.get_available_friendly_matches.return_value = FAKE_FRIENDLIES

    r = client.get("/friendlymatches")

    assert r.status_code == 200
    assert r.json() == FAKE_FRIENDLIES
    utils_mock.get_available_friendly_matches.assert_called_once()


def test_friendly_matches_lista_vacia(client, utils_mock):
    utils_mock.get_available_friendly_matches.return_value = []

    r = client.get("/friendlymatches")

    assert r.status_code == 200
    assert r.json() == []


def test_friendly_matches_no_expone_la_password(client, utils_mock):
    utils_mock.get_available_friendly_matches.return_value = [{**FAKE_FRIENDLIES[1], "password": "secreta"}]

    body = client.get("/friendlymatches").json()

    assert "password" not in body[0]


def test_friendly_matches_error_de_base(client, utils_mock):
    utils_mock.get_available_friendly_matches.side_effect = schemas.FriendlyMatchesError

    r = client.get("/friendlymatches")

    assert r.status_code == 500
    assert r.json()["detail"] == "Error retrieving teams."