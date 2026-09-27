from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from datetime import datetime, timezone
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    avatar = Column(String(255), nullable=True)
    created_at = Column(DateTime(Timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class Team(Base):
    __tablename__ = "teams"

    owner_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    name = Column(String(100), nullable=False)
    

class Record(Base):
    __tablename__ = "records"

    team_id = Column(Integer, ForeignKey("teams.id"), primary_key=True)
    leagues_won = Column(Integer, default=0, nullable=False)
    total_points = Column(Integer, default=0, nullable=False)
    matches_won = Column(Integer, default=0, nullable=False)
    matches_lost = Column(Integer, default=0, nullable=False)
    matches_drawn = Column(Integer, default=0, nullable=False)

class Behavior(Base):
    __tablename__ = "behaviors"

    id_behavior = Column(Integer, primary_key=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(50), nullable=False)
    python_code = Column(Text, nullable=False)              # se usa Txt para permitir código más largo
    is_default = Column(Boolean, default=False, nullable=False)
