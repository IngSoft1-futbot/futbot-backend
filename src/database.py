import os

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from .models import Base, Behavior

# Direccion de la base. Se lee de una variable de entorno para no dejar la
# contraseña escrita en el codigo. El valor por defecto es solo para desarrollo local.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/futbot",
)

# Conexión con Postgres (mantiene un pool de conexiones reutilizables).
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Fabrica de sesiones: cada sesión es un "espacio de trabajo" con la base.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """Dependencia de FastAPI: abre una sesion por request y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
PREDEFINED_BEHAVIORS = (
    (0, "Correr rapido a la pelota", True),
    (1, "Posicion defensiva", False),
    (2, "Stand-By", False),
)


def seed_predefined_behaviors(db) -> None:
    """Crea o actualiza los tres behaviors del sistema con código vacío."""
    for behavior_id, name, is_default in PREDEFINED_BEHAVIORS:
        behavior = db.get(Behavior, behavior_id)
        if behavior is None:
            behavior = Behavior(id_behavior=behavior_id)
            db.add(behavior)
        behavior.creator_id = None
        behavior.name = name
        behavior.python_code = ""
        behavior.is_default = is_default

    try:
        db.commit()
    except IntegrityError:
        # Otro proceso pudo insertar los mismos IDs al iniciar simultáneamente.
        db.rollback()
        if not all(db.get(Behavior, behavior_id) for behavior_id, _, _ in PREDEFINED_BEHAVIORS):
            raise


def migrate_match_schema() -> None:
    """Actualiza la tabla matches existente con las columnas de amistosos."""
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE matches ADD COLUMN IF NOT EXISTS in_progress BOOLEAN"
        ))
        connection.execute(text(
            "ALTER TABLE matches ADD COLUMN IF NOT EXISTS is_friendly BOOLEAN DEFAULT TRUE"
        ))
        connection.execute(text(
            "ALTER TABLE matches ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'open'"
        ))
        connection.execute(text(
            "ALTER TABLE matches ADD COLUMN IF NOT EXISTS password VARCHAR(255)"
        ))
        connection.execute(text(
            "UPDATE matches SET is_friendly = TRUE WHERE is_friendly IS NULL"
        ))
        connection.execute(text(
            "ALTER TABLE matches ALTER COLUMN is_friendly SET DEFAULT TRUE, "
            "ALTER COLUMN is_friendly SET NOT NULL"
        ))
        connection.execute(text(
            "UPDATE matches SET status = 'open' WHERE status IS NULL"
        ))
        connection.execute(text(
            "ALTER TABLE matches ALTER COLUMN status SET DEFAULT 'open', "
            "ALTER COLUMN status SET NOT NULL"
        ))
        connection.execute(text(
            "ALTER TABLE matches "
            "ALTER COLUMN away_team_id DROP NOT NULL, "
            "ALTER COLUMN league_id DROP NOT NULL, "
            "ALTER COLUMN scheduled_at DROP NOT NULL, "
            "ALTER COLUMN in_progress DROP NOT NULL"
        ))


def reset_db() -> None:
    """Elimina el esquema public y lo recrea para limpiar dependencias FK."""
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE;"))
            connection.execute(text("CREATE SCHEMA public;"))
    else:
        Base.metadata.drop_all(bind=engine)

    init_db()


def init_db():
    """Crea las tablas que falten y siembra los datos base."""
    Base.metadata.create_all(bind=engine)
    migrate_match_schema()
    with SessionLocal() as db:
        seed_predefined_behaviors(db)