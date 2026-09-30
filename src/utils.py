import bcrypt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import product_repository as repo
from . import schemas

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
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def register_user(db: Session, user_in: schemas.UserCreate):
    # valida antes de tocar la base de datos
    password_validation(user_in.password)

    email = user_in.email.lower()
    # 1. Chequeo previo (optimizacion: evita hashear si ya existe)
    if repo.get_user_by_email(db, email=email):
        raise schemas.EmailAlreadyExistsError()
    if repo.get_user_by_club(db, club=user_in.club):
        raise schemas.ClubAlreadyExistsError()
    # 2. Hash (nunca se guarda la contraseña en texto plano)
    password_hash = hash_password(user_in.password)

    # 3. Usuario 
    try:
        return repo.create_user(
            db,
            club=user_in.club,
            name=user_in.name,
            email=email,
            password_hash=password_hash,
            avatar=user_in.avatar,
        )
    except IntegrityError:
        raise schemas.RegistrationError()

def authenticate_user(db: Session, email: str, password: str):
    # 1. Buscar al usuario por email (normalizado en minusculas)
    user = repo.get_user_by_email(db, email=email.lower())
    if not user:
        return None # podes lanzar una excepcion personalizada de credenciales invalidas

    # 2. Verificar la contraseña usando bcrypt
    # bcrypt.checkpw requiere bytes, por eso codificamos ambos
    is_valid = bcrypt.checkpw(
        password.encode("utf-8"), 
        user.password_hash.encode("utf-8")
    )
    
    if not is_valid:
        return None

    return user

