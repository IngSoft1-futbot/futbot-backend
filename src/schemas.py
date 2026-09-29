from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=50)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class UserCreate(BaseModel):
    username: Username
    name: Name
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    avatar: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    name: str
    email: EmailStr
    avatar: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)  # permite leer desde el ORM

class RegistrationError(Exception):
    pass
class EmailAlreadyExistsError(RegistrationError):
    pass
class UsernameAlreadyExistsError(RegistrationError):
    pass