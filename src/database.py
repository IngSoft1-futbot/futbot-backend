import os

from sqlalchemy import create_engine
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
        
def seed_default_behavior(db) -> None:
    """Crea el behavior por defecto (id 0) si todavía no existe."""
    if db.get(Behavior, 0) is None:
        db.add(Behavior(
            id_behavior=0,
            creator_id=None,          # es del sistema, no de un usuario
            name="Default",
            python_code="# default behavior",
            is_default=True,
        ))
        db.commit()


def init_db():
    """Crea las tablas que falten y siembra los datos base."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_default_behavior(db)