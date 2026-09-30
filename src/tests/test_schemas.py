import pytest
from pydantic import ValidationError

from src import schemas


def make(**over):
    data = {
        "username": "juan",
        "name": "Juan",
        "email": "juan@gmail.com",
        "password": "Clave123!",
    }
    data.update(over)
    return schemas.UserCreate(**data)


def test_usuario_valido():
    user = make()
    assert user.username == "juan"


def test_avatar_es_opcional():
    assert make().avatar is None


def test_username_se_recorta():
    assert make(username="  juan  ").username == "juan"


@pytest.mark.parametrize("username", ["ab", "   ", "a" * 51])
def test_username_invalido(username):
    with pytest.raises(ValidationError):
        make(username=username)


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
        schemas.UserCreate(username="juan", name="Juan", email="juan@gmail.com")


def test_schema_no_valida_la_fuerza_de_la_password():
    # Es responsabilidad de utils.password_validation, no de Pydantic
    assert make(password="abc").password == "abc"