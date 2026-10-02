from .schemas import PlayerIn
import os
import jwt
import bcrypt


from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import product_repository as repo
from . import schemas
DEFAULT_BEHAVIOR_ID = 0

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

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

    email= user_in.email.lower()
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



#-----------------Login-----------------------
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

def create_jwt_token(user_id: int) -> str:
    # Definimos el payload con el ID del usuario ("sub")
    payload = {
        "sub": str(user_id),
    }
    # Firmamos y retornamos el token JWT
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def authenticate_and_create_token(db, email: str, password: str):
    # 1. Usamos la funcion que verifica email y contraseña (bcrypt)
    user = authenticate_user(db, email=email, password=password)
    if not user:
        return None

    # 2. Si las credenciales son validas, generamos y retornamos el JWT firmado 
    return create_jwt_token(user.id)


def verify_jwt_token(token: str) -> int:
    """
    Decodifica y valida el token JWT. 
    Retorna el user_id si es valido, o lanza excepciones si expiro o es invalido.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        return user_id
    except jwt.PyJWTError:
        raise schemas.InvalidTokenError("User not authoriced.")

#-----------------Crear Jugador-----------------------


def validate_pacss(pacss)-> bool:
    
    attributes: list[int] = [pacss.power, pacss.agility, pacss.control, pacss.speed, pacss.strength]
    if not all(20 <= attr <= 100 for attr in attributes):
        return False

    if sum(attributes) != 300:
        return False

    return True

def verify_player(player: PlayerIn)-> bool:

    pacss: schemas.PacssAttributes = player.pacss_attributes

    return validate_pacss(pacss)



#-----------------Crear Equipo-----------------------

def check_composition_and_duplicated(team_in: schemas.TeamCreate):      # composicion y duplicados dentro de peticion
    num_titulares = len(team_in.jugadores_titulares)
    num_suplentes =len(team_in.jugadores_suplentes)
    
    if not (num_titulares == 3 and num_suplentes == 3): # revisa 3 titulares y 3 jugadores en total
        raise schemas.TeamIncompleteError()
    
    ids = [p.player_id for p in team_in.jugadores_titulares + team_in.jugadores_suplentes]
    if len(ids) != len(set(ids)):  
        raise schemas.PlayerAlreadyInUseError()


def check_players(db: Session, user_id: int, player_ids: list[int]):
    """Los jugadores existen, son del usuario y no tienen equipo (una sola consulta)."""
    players = {p.player_id: p for p in repo.get_players_by_ids(db, ids=player_ids)}
 
    for player_id in player_ids:
        player = players.get(player_id)
        if player is None:
            raise schemas.PlayerNotFoundError()
        if player.owner_id != user_id:
            raise schemas.PlayerNotAuthorizedError()
        if player.team_id is not None:
            raise schemas.PlayerAlreadyInUseError()

def check_behaviors(db: Session, user_id: int, behavior_ids: set[int]):
    """Los behaviors existen y son del usuario, salvo el default que es de todos."""
    behaviors = {b.id_behavior: b for b in repo.get_behaviors_by_ids(db, ids=list(behavior_ids))}
 
    for behavior_id in behavior_ids:
        behavior = behaviors.get(behavior_id)
        if behavior is None:
            raise schemas.BehaviorNotFoundError()
        if not behavior.is_default and behavior.creator_id != user_id:
            raise schemas.BehaviorNotAuthorizedError()
 
 
def resolve_behavior_id(assignment: schemas.PlayerAssignment) -> int:
    """Si el usuario no eligio behavior, se usa el default."""
    if assignment.behavior_id is None:
        return DEFAULT_BEHAVIOR_ID
    return assignment.behavior_id
 
 
def build_team_out(team) -> schemas.TeamOut:
    """Separa los jugadores del equipo en titulares y suplentes."""
    players = sorted(team.players, key=lambda p: p.player_id)
    return schemas.TeamOut(
        team_id=team.team_id,
        name=team.name,
        jugadores_titulares=[schemas.PlayerOut.model_validate(p) for p in players if p.is_starter],
        jugadores_suplentes=[schemas.PlayerOut.model_validate(p) for p in players if not p.is_starter],
    )
 
 
def create_team(db: Session, user_id: int, team_in: schemas.TeamCreate):
    # Validaciones sin base
    check_composition_and_duplicated(team_in)
 
    # Validaciones con base
    if not repo.get_user(db, user_id):
        raise schemas.UserNotFoundError()
 
    starters = [(a.player_id, resolve_behavior_id(a)) for a in team_in.jugadores_titulares]
    substitutes = [(a.player_id, resolve_behavior_id(a)) for a in team_in.jugadores_suplentes]
 
    check_players(db, user_id, [pid for pid, _ in starters + substitutes])
    check_behaviors(db, user_id, {bid for _, bid in starters + substitutes})
 
    if repo.get_team_by_owner_and_name(db, owner_id=user_id, name=team_in.name):     
        raise schemas.TeamNameAlreadyInUseError()
 
    # Crear (el repository hace commit/rollback)
    try:
        team = repo.add_team(
            db,
            owner_id=user_id,
            name=team_in.name,
            starters=starters,
            substitutes=substitutes,
        )
    except IntegrityError:
        raise schemas.CreateTeamError()
 
    return build_team_out(team)

