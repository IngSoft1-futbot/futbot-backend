from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import product_repository as repo
from . import schemas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def password_validation(password: str):
    if len(password) < 8 or len(password) > 12:
        raise schemas.PasswordValidationError("Password must be between 8 and 12 characters long.")
    if any(char.isspace() for char in password):
       raise schemas.PasswordValidationError("Password must not contain spaces.")
    if not any(char.isdigit() for char in password):
        raise schemas.PasswordValidationError("Password must contain at least one digit.")
    if not any(char.isupper() for char in password):
        raise schemas.PasswordValidationError("Password must contain at least one uppercase letter.")
    if not any(char.islower() for char in password):
        raise schemas.PasswordValidationError("Password must contain at least one lowercase letter.")
    if not any(not char.isalnum() for char in password):
        raise schemas.PasswordValidationError("Password must contain at least one special character.")
    
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def register_user(db: Session, user_in: schemas.UserCreate):
    # valida antes de tocar la base de datos
    password_validation(user_in.password)

    email = user_in.email.lower()
    # 1. Chequeo previo (optimizacion: evita hashear si ya existe)
    if repo.get_user_by_email(db, email=email):
        raise schemas.EmailAlreadyExistsError()
    if repo.get_user_by_username(db, username=user_in.username):
        raise schemas.UsernameAlreadyExistsError()
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
        raise schemas.RegistrationError()