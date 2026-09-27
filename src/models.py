from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from datetime import datetime, timezone
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    avatar = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class Team(Base):
    __tablename__ = "teams"

    owner_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    name = Column(String(100), nullable=False)
    accurate_league = Column(Integer, ForeignKey("leagues.id"), nullable=True)
    

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

class Match(Base):
    __tablename__ = "matches"

    id_match = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id"), nullable=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    in_progress = Column(Boolean, default=False, nullable=False)
    current_period = Column(Integer, default=0, nullable=False)  # 0=no iniciado, 1-4 tiempos

class MatchResult(Base):
    __tablename__ = "match_results"

    match_id = Column(Integer, ForeignKey("matches.id"), primary_key=True)
    home_goals = Column(Integer, default=0, nullable=False)
    away_goals = Column(Integer, default=0, nullable=False)

class Player(Base):
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    behavior_id = Column(Integer, ForeignKey("behaviors.id"), nullable=True)

    shirt_number = Column(Integer, nullable=False)
    name = Column(String(50), nullable=False)
    is_starter = Column(Boolean, default=False, nullable=False)  # titular vs suplente

    power = Column(Integer, nullable=False)
    agility = Column(Integer, nullable=False)
    control = Column(Integer, nullable=False)
    speed = Column(Integer, nullable=False)
    strength = Column(Integer, nullable=False)
 
class LeagueStanding(Base):
    __tablename__ = "league_standings"

    league_id = Column(Integer, ForeignKey("leagues.id_league"), primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.owner_id"), primary_key=True)

    points = Column(Integer, default=0, nullable=False)
    matches_won = Column(Integer, default=0, nullable=False)
    matches_drawn = Column(Integer, default=0, nullable=False)
    matches_lost = Column(Integer, default=0, nullable=False)
    goals_for = Column(Integer, default=0, nullable=False)
    goals_against = Column(Integer, default=0, nullable=False)
