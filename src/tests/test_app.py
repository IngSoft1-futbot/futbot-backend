from unittest.mock import patch, MagicMock
from src.app import app
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

@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: MagicMock()
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

    response = client.post("/auth/login/", json={
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

    response = client.post("/auth/login/", json={
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
    response = client.post("/auth/login/", json={
        "email": "correoInvalidoSinArroba",
        "password": "Pass1234!"
    })
    
    assert response.status_code == 422
    utils_mock.authenticate_and_create_token.assert_not_called() 
