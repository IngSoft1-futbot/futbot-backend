import os
import jwt
import bcrypt
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Optional
from . import product_repository as repo
from . import schemas

DEFAULT_BEHAVIOR_ID = 0

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("Falta la variable de entorno SECRET_KEY. Definila antes de arrancar la app (make env la genera).")
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

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

def authenticate_user(db: Session, email: str, password: str):
    # 1. Buscar al usuario por email (normalizado en minusculas)
    user = repo.get_user_by_email(db, email=email.lower())
    if not user:
        return None # podes lanzar una excepcion personalizada de credenciales invalidas

    # 2. Verificar la contraseña usando bcrypt
    # bcrypt.checkpw requiere bytes, por eso codificamos ambos
    if not verify_password(password, user.password_hash):
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
    except (jwt.PyJWTError, TypeError, ValueError):
        # PyJWTError: firma/formato invalido. TypeError: falta "sub". ValueError: "sub" no numerico.
        raise schemas.InvalidTokenError("User not authorized.")

#-----------------Crear Jugador-----------------------


def validate_pacss(pacss)-> bool:
    
    attributes: list[int] = [pacss.power, pacss.agility, pacss.control, pacss.speed, pacss.strength]
    if not all(20 <= attr <= 100 for attr in attributes):
        return False

    if sum(attributes) != 300:
        return False

    return True


def verify_player(player: schemas.PlayerIn) -> bool:

    pacss: schemas.PacssAttributes = player.pacss_attributes

    return validate_pacss(pacss)




def check_composition_and_duplicated(team_in: schemas.TeamCreate):      # composicion y duplicados dentro de peticion
    num_titulares = len(team_in.jugadores_titulares)
    num_suplentes =len(team_in.jugadores_suplentes)
    
    if not (num_titulares == 3 and num_suplentes == 3): # revisa 3 titulares y 3 suplentes
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
        if behavior.creator_id is not None and behavior.creator_id != user_id:
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
        jugadores_titulares=[
            build_player_out(p) for p in players if p.is_starter
        ],
        jugadores_suplentes=[
            build_player_out(p) for p in players if not p.is_starter
        ],
    )


def create_player(db: Session, user_id: int, player: schemas.PlayerIn):
    if not repo.get_user(db, user_id):
        raise schemas.UserNotFoundError()
    if not verify_player(player):
        raise schemas.PointAssignmentError()
    return build_player_out(repo.create_player(db, user_id, player))


def get_players(db: Session, user_id: int):
    if not repo.get_user(db,user_id):
        raise schemas.UserNotFoundError()
    players = repo.get_players(db,user_id)
    return [build_player_out(p) for p in players]


def get_behaviors(db: Session, user_id: int) -> list[schemas.BehaviorOut]:
    if not repo.get_user(db, user_id):
        raise schemas.UserNotFoundError()

    behaviors = repo.get_predefined_behaviors(db)
    return [
        schemas.BehaviorOut(
            id_behavior=behavior.id_behavior,
            name=behavior.name,
            python_code="",
            is_default=behavior.is_default,
        )
        for behavior in behaviors
    ]


def build_player_out(player) -> schemas.PlayerOut:
    """Convierte un models.Player (columnas planas) en PlayerOut (pacss anidado)."""
    return schemas.PlayerOut(
        player_id=player.player_id,
        name=player.name,
        shirt_number=player.shirt_number,
        behavior_id=player.behavior_id,
        team_id=player.team_id,
        pacss_attributes=schemas.PacssAttributes(
            power=player.power,
            agility=player.agility,
            control=player.control,
            speed=player.speed,
            strength=player.strength,
        ),
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

#---------------------- Friendly Matches schemas -----------------------

def check_friendly_match_duration(match_duration: int):
    if not (1 <= match_duration <= 5):
        raise schemas.InvalidDurationError("Match duration must be between 1 and 5 minutes.")

def check_friendly_team(team) -> int:
    if not team:
        raise schemas.TeamNotFoundError()
    
    starters = [p for p in team.players if p.is_starter]
    if len(starters) != 3:
        raise schemas.TeamIncompleteError()
    
    return team.team_id

def create_friendly_match(db: Session, user_id: int, match_in: schemas.FriendlyMatchCreate):
    # 1. Validaciones puras
    check_friendly_match_duration(match_in.match_duration)

    # 2. Validación de usuario (inline)
    if not repo.get_user(db, user_id):
        raise schemas.UserNotFoundError()

    # 3. Validación de equipo
    team = repo.get_team_by_owner_and_name(db, owner_id=user_id, name=match_in.team_name)
    check_friendly_team(team)

    # 4. Creación con try/except
    try:
        match = repo.create_match(
            db,
            is_friendly=True,
            status="open",
            home_team_id=team.team_id,
            away_team_id=None,
            match_duration=match_in.match_duration,
            is_private=False,
            password=None,
            current_period=0,
            league_id=None,
            scheduled_at=None,
        )
    except IntegrityError:
        raise schemas.CreateMatchError()

    return match
def get_available_friendly_matches(db: Session):
    """Amistosos disponibles: los que esperan a otro jugador (status open)."""
    try:
        return repo.get_open_friendly_matches(db)
    except SQLAlchemyError:
        raise schemas.FriendlyMatchesError()

def check_match_password(match, password: Optional[str]):
    """Si el partido es privado, la contraseña tiene que venir y coincidir con el hash."""
    if not match.is_private:
        return
    if not password or not match.password or not verify_password(password, match.password):
        raise schemas.MatchNotAuthorizedError()
    
def join_friendly_match(db: Session, user_id: int, match_id: int, join_in: schemas.JoinMatch):
    # El partido existe y es amistoso
    match = repo.get_match(db, match_id)
    if match is None or not match.is_friendly:
        raise schemas.MatchNotFoundError()

    # El equipo existe y es del usuario
    team = repo.get_team(db, join_in.team_id)
    if team is None:
        raise schemas.TeamNotFoundError()
    if team.owner_id != user_id:
        raise schemas.TeamNotAuthorizedError()

    # Estado del partido
    if match.home_team.owner_id == user_id:
        raise schemas.JoinOwnMatchError()
    
    check_match_password(match, join_in.password)
    
    if match.away_team_id == team.team_id:      # reintento del mismo equipo 
        return match
    if match.away_team_id is not None:          # ya tiene rival, por lo tanto esta started
        raise schemas.MatchAlreadyTakenError()
    if match.status != "open":                  # finished / cancelled
        raise schemas.MatchNotJoinableError()

    # Plantel completo (reutiliza la validacion de amistosos)
    check_friendly_team(team)

    # Ocupar la plaza de forma atomica
    updated = repo.join_match(db, match_id=match_id, away_team_id=team.team_id)
    if updated is None:                         # otro se unio entre el chequeo y el UPDATE
        raise schemas.MatchAlreadyTakenError()
    return updated