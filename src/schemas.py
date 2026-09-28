from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    name: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    avatar: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    name: str
    email: EmailStr
    avatar: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)  # permite leer desde el ORM