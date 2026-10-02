import pydantic.config
from sqlalchemy import null
from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints,Field

Club = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=50)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
TeamName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=30)]

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenError(Exception):
    pass  # {HTTPERROR} 401
class InvalidTokenError(TokenError):
    pass  # {HTTPERROR} 401

class UserCreate(BaseModel):
    club: Club
    name: Name
    email: EmailStr
    password: str
    avatar: Optional[str] = None

class UserOut(BaseModel):
    id: int
    club: str
    name: str
    email: EmailStr
    avatar: Optional[str]
    created_at: datetime

    model_config: pydantic.config.ConfigDict = ConfigDict(from_attributes=True)  # permite leer desde el ORM

class RegistrationError(Exception):
    pass  # {HTTPERROR} 400
class EmailAlreadyExistsError(RegistrationError):
    pass  # {HTTPERROR} 409
class PasswordValidationError(RegistrationError):
    pass  # {HTTPERROR} 400
class ClubAlreadyExistsError(RegistrationError):
    pass  # {HTTPERROR} 409

""" PacssAttributes Schema """

class PacssAttributes(BaseModel):
    id: int
    power: int
    agility: int
    control: int
    speed: int
    strenght: int

class PointAssignmentError(Exception):
    pass  # {HTTPERROR} 400

class PointExcessError(PointAssignmentError):
    pass  # {HTTPERROR} 400

class PointDeficiencyError(PointAssignmentError):
    pass  # {HTTPERROR} 400


""" Player Schema """

class PlayerIn(BaseModel):
    name: str
    shirt_numb: Optional[int] = None
    pacss_attributes: PacssAttributes
    team_id: Optional[int] = None

class PlayerOut(BaseModel):
    player_id: int
    name: str
    shirt_numb: Optional[int] = None
    pacss_attributes: PacssAttributes
    team_id: Optional[int] = None
    
""" User Login Schema """

class UserLoginIn(BaseModel):
    email: EmailStr
    password: str

class UserLoginOut(BaseModel):
    accessToken: str
    tokenType: str


class PlayerLoginError(Exception):  # {HTTPERROR} 401
    pass

class BadCredentials(PlayerLoginError):  # {HTTPERROR} 401
    pass

class Fobbiden(PlayerLoginError):  # {HTTPERROR} 403
    pass

#----------------------Teams schemas-----------------------
class PlayerAssignment(BaseModel):
    player_id: int
    behavior_id: Optional[int] = None   # None -> se asigna el 0 (default)

class PlayerOut(BaseModel):
    player_id: int
    name: str
    behavior_id: int

    model_config = ConfigDict(from_attributes=True)  # permite leer desde el ORM

class TeamCreate(BaseModel):
    name: TeamName
    jugadores_titulares: list[PlayerAssignment] # (jugador_id, behavior_id)
    jugadores_suplentes: list[PlayerAssignment] = Field(default_factory=list) # (jugador_id, behavior_id)

class TeamOut(BaseModel):
    team_id: int
    name: str
    jugadores_titulares: list[PlayerOut]
    jugadores_suplentes: list[PlayerOut]


class UserNotFoundError(Exception):         #404
    pass
class BehaviorNotFoundError(Exception):         #404
    pass
class PlayerNotFoundError(Exception):         #404
    pass


class PlayerNotAuthorizedError(Exception):         #403
    pass
class BehaviorNotAuthorizedError(Exception):         #403
    pass


class TeamIncompleteError(Exception):         #400
    pass
class PlayerAlreadyInUseError(Exception):         #400
    pass
class TeamNameAlreadyInUseError(Exception):         #400
    pass

class CreateTeamError(Exception):         #409 condicion de carrera
    pass