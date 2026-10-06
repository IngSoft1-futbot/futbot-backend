from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src import models, product_repository as repo
from src.database import seed_predefined_behaviors


def test_match_schema_supports_open_friendly_matches():
    columns = models.Match.__table__.columns

    assert {
        "in_progress",
        "is_friendly",
        "status",
        "password",
    }.issubset(columns.keys())
    assert all(
        columns[column].nullable
        for column in ("away_team_id", "league_id", "scheduled_at", "in_progress", "password")
    )
    assert str(columns["is_friendly"].server_default.arg).upper() == "TRUE"
    assert str(columns["status"].server_default.arg).strip("'") == "open"


def test_seed_predefined_behaviors_creates_and_updates_three_system_rows():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        session.add(models.Behavior(
            id_behavior=0,
            creator_id=None,
            name="Default",
            python_code="# default behavior",
            is_default=True,
        ))
        session.commit()

        seed_predefined_behaviors(session)
        seed_predefined_behaviors(session)

        behaviors = repo.get_predefined_behaviors(session)
        assert [
            (behavior.id_behavior, behavior.name, behavior.python_code, behavior.is_default)
            for behavior in behaviors
        ] == [
            (0, "Correr rapido a la pelota", "", True),
            (1, "Posicion defensiva", "", False),
            (2, "Stand-By", "", False),
        ]
        assert session.query(models.Behavior).count() == 3
    finally:
        session.close()
        engine.dispose()
