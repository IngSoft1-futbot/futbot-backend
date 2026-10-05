import os

from sqlalchemy import create_engine
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


def init_db():
    """Crea las tablas que falten y siembra los datos base."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_predefined_behaviors(db)