import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src import models, product_repository as repo


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