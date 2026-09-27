from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
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

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

class Record(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), unique=True, nullable=False)
    leagues_won = Column(Integer, default=0, nullable=False)
    total_points = Column(Integer, default=0, nullable=False)
    matches_won = Column(Integer, default=0, nullable=False)
    matches_lost = Column(Integer, default=0, nullable=False)
    matches_drawn = Column(Integer, default=0, nullable=False)