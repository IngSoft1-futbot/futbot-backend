from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import product_repository as repo
from . import schemas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def register_user(db: Session, user_in: schemas.UserCreate):
    email = user_in.email.lower()

    # 1. Chequeo previo (optimizacion: evita hashear si ya existe)
    if repo.get_user_by_email_or_username(db, email=email, username=user_in.username):
        raise schemas.UserAlreadyExistsError()

    # 2. Hash (nunca se guarda la contraseña en texto plano)
    password_hash = hash_password(user_in.password)

    # 3. Usuario 
    try:
        return repo.create_user(
            db,
            username=user_in.username,
            name=user_in.name,
            email=email,
            password_hash=password_hash,
            avatar=user_in.avatar,
        )
    except IntegrityError:
        raise schemas.UserAlreadyExistsError()