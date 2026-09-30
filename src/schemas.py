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

    model_config = ConfigDict(from_attributes=True)  # permite leer desde el ORM

class RegistrationError(Exception):
    pass
class EmailAlreadyExistsError(RegistrationError):
    pass
class PasswordValidationError(RegistrationError):
    pass
class ClubAlreadyExistsError(RegistrationError):
    pass