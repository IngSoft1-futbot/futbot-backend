from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from src import schemas, utils

USER_IN = schemas.UserCreate(
    club="juan",
    name="Juan",
    email="Juan@Gmail.com",
    password="Clave123!",
)


@pytest.fixture
def repo_mock():
    with patch("src.utils.repo") as mock:
        yield mock


# ---------- password_validation (función pura, sin mocks) ----------

@pytest.mark.parametrize("pwd, mensaje", [
    ("Cl1!", "between"),                  # muy corta
    ("Clave123!" + "a" * 40, "between"),  # muy larga
    ("Clavesola!", "digit"),              # sin número
    ("clave123!", "uppercase"),           # sin mayúscula
    ("CLAVE123!", "lowercase"),           # sin minúscula
    ("Clave1234", "special"),             # sin símbolo
])
def test_password_invalida(pwd, mensaje):
    with pytest.raises(schemas.PasswordValidationError) as exc:
        utils.password_validation(pwd)

    assert mensaje in str(exc.value)


def test_password_valida():
    utils.password_validation("Clave123!")   # no debe lanzar nada


# ---------- register_user ----------

def test_register_password_invalida_no_toca_la_base(repo_mock):
    bad = USER_IN.model_copy(update={"password": "abc"})

    with pytest.raises(schemas.PasswordValidationError):
        utils.register_user(MagicMock(), bad)

    repo_mock.get_user_by_email.assert_not_called()
    repo_mock.create_user.assert_not_called()


def test_register_email_ya_existe(repo_mock):
    repo_mock.get_user_by_email.return_value = object()

    with pytest.raises(schemas.EmailAlreadyExistsError):
        utils.register_user(MagicMock(), USER_IN)

    repo_mock.get_user_by_club.assert_not_called()
    repo_mock.create_user.assert_not_called()


def test_register_club_ya_existe(repo_mock):
    repo_mock.get_user_by_email.return_value = None
    repo_mock.get_user_by_club.return_value = object()

    with pytest.raises(schemas.ClubAlreadyExistsError):
        utils.register_user(MagicMock(), USER_IN)

    repo_mock.create_user.assert_not_called()


def test_register_ok(repo_mock):
    repo_mock.get_user_by_email.return_value = None
    repo_mock.get_user_by_club.return_value = None

    utils.register_user(MagicMock(), USER_IN)

    repo_mock.create_user.assert_called_once()
    kwargs = repo_mock.create_user.call_args.kwargs
    assert kwargs["email"] == "juan@gmail.com"          # en minusculas
    assert kwargs["password_hash"] != "Clave123!"       # nunca en claro
    assert "password" not in kwargs


def test_register_integrity_error_se_convierte_en_registration_error(repo_mock):
    repo_mock.get_user_by_email.return_value = None
    repo_mock.get_user_by_club.return_value = None
    repo_mock.create_user.side_effect = IntegrityError("stmt", {}, Exception())

    with pytest.raises(schemas.RegistrationError):
        utils.register_user(MagicMock(), USER_IN)