import pydantic.config
from sqlalchemy import null
from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

Club = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=50)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
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
    pass
class EmailAlreadyExistsError(RegistrationError):
    pass
class PasswordValidationError(RegistrationError):
    pass
class ClubAlreadyExistsError(RegistrationError):
    pass

""" PacssAttributes Schema """

class PacssAttributes(BaseModel):
    id: int
    power: int
    agility: int
    control: int
    speed: int
    strenght: int

class PointAssignmentError(Exception):
    pass

class PointExcessError(PointAssignmentError):
    pass

class PointDeficiencyError(PointAssignmentError):
    pass


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


class PlayerLoginError(Exception):
    pass

class BadCredentials(PlayerLoginError):
    pass

class Fobbiden(PlayerLoginError):
    pass