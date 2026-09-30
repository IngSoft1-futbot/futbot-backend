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


def make_user(db, username="juan", email="juan@gmail.com"):
    return repo.create_user(
        db, username=username, name="Juan",
        email=email, password_hash="hash", avatar=None,
    )


def test_create_user_lo_guarda(db):
    make_user(db)
    assert db.query(models.User).count() == 1


def test_get_user_by_email(db):
    make_user(db)
    assert repo.get_user_by_email(db, email="juan@gmail.com").username == "juan"
    assert repo.get_user_by_email(db, email="nadie@gmail.com") is None


def test_get_user_by_username(db):
    make_user(db)
    assert repo.get_user_by_username(db, username="juan").email == "juan@gmail.com"
    assert repo.get_user_by_username(db, username="nadie") is None


def test_create_user_duplicado_lanza_integrity_error(db):
    make_user(db)
    with pytest.raises(IntegrityError):
        make_user(db, username="otro", email="juan@gmail.com")   # mismo email