import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base

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


def init_db():
    """Crea en Postgres las tablas definidas en models.py que todavia no existan."""
    Base.metadata.create_all(bind=engine)