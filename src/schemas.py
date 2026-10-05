from datetime import datetime
from typing import Optional, Annotated, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints, Field

Club = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=50)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
TeamName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=30)]
PlayerName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]  # columna String(50)
ShirtNumber = Annotated[int, Field(ge=1, le=99)]

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
    avatar: Optional[str] = Field(default=None, max_length=255)  # columna String(255)

class UserOut(BaseModel):
    id: int
    club: str
    name: str
    email: EmailStr
    avatar: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)  # permite leer desde el ORM

class RegistrationError(Exception):
    pass  # {HTTPERROR} 409 (conflicto al registrar, p. ej. carrera entre dos registros)
class EmailAlreadyExistsError(RegistrationError):
    pass  # {HTTPERROR} 400
class PasswordValidationError(RegistrationError):
    pass  # {HTTPERROR} 400
class ClubAlreadyExistsError(RegistrationError):
    pass  # {HTTPERROR} 400

""" PacssAttributes Schema """

class PacssAttributes(BaseModel):
    power: int
    agility: int
    control: int
    speed: int
    strength: int

class PointAssignmentError(Exception):
    pass  # {HTTPERROR} 400


""" Player Schema """

class PlayerIn(BaseModel):
    name: PlayerName
    shirt_number: ShirtNumber
    pacss_attributes: PacssAttributes

class PlayerOut(BaseModel):
    player_id: int
    name: str
    shirt_number: int
    behavior_id: Optional[int] = 0
    pacss_attributes: PacssAttributes
    team_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)  # permite leer desde el ORM

class BehaviorOut(BaseModel):
    id_behavior: int
    name: str
    python_code: str
    is_default: bool
    model_config = ConfigDict(from_attributes=True)

class BehaviorSummaryOut(BaseModel):
    behavior_id: int
    name: str

class BehaviorsListResponse(BaseModel):
    status: Literal["200"]
    data: list[BehaviorSummaryOut]
    message: Literal["Behaviors listed successfully."]

#----------------------Teams schemas-----------------------
class PlayerAssignment(BaseModel):
    player_id: int
    behavior_id: Optional[int] = None   # None -> se asigna el 0 (default)


class TeamCreate(BaseModel):
    name: TeamName
    jugadores_titulares: list[PlayerAssignment] # (jugador_id, behavior_id)
    jugadores_suplentes: list[PlayerAssignment] = Field(default_factory=list) # (jugador_id, behavior_id)

class TeamOut(BaseModel):
    team_id: int
    name: str
    jugadores_titulares: list[PlayerOut]
    jugadores_suplentes: list[PlayerOut]


class TeamSummaryOut(BaseModel):
    team_id: int
    name: str
class TeamsListResponse(BaseModel):
    status: Literal["200"]
    data: list[TeamSummaryOut]


#---------------------- Friendly Matches schemas -----------------------

class FriendlyMatchCreate(BaseModel):
    team_name: str
    match_duration: int

class FriendlyMatchOut(BaseModel):
    id_match: int
    home_team_id: int
    away_team_id: int | None = None
    match_duration: int
    status: str
    is_friendly: bool
    is_private: bool

    model_config = ConfigDict(from_attributes=True)



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

#----------------Matches schemas-----------------------
class GETFriendlyMatchOut(BaseModel):
    id_match: int
    home_team_id: int
    match_duration: int
    is_private: bool

    model_config = ConfigDict(from_attributes=True)

class FriendlyMatchesError(Exception):         #500
    pass

class InvalidDurationError(Exception):         #400
    pass

class TeamNotFoundError(Exception):            #404
    pass

class CreateMatchError(Exception):             #409 condicion de carrera o fallo de BD
    pass

class JoinMatch(BaseModel):               #409 condicion de carrera o fallo de BD
    team_id:int 
    password: Optional[str] = Field(default=None, max_length=50)

class JoinOwnMatchError(Exception):         #400
    pass
class MatchNotAuthorizedError(Exception):         #401
    pass
class TeamNotAuthorizedError(Exception):         #403
    pass
class MatchNotFoundError(Exception):         #404
    pass
class MatchAlreadyTakenError(Exception):         #409
    pass
class MatchNotJoinableError(Exception):         #409    
    pass