import pytest
from pydantic import ValidationError

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