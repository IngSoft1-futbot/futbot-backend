from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean, UniqueConstraint, text
from datetime import datetime, timezone
from sqlalchemy.orm import relationship, declarative_base
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    club = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    avatar = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
 
    teams = relationship("Team", back_populates="owner")  # un usuario puede tener varios equipos
    record = relationship("Record", back_populates="user", uselist=False)  # historial del club
    behaviors = relationship("Behavior", back_populates="creator")
    players = relationship("Player", back_populates="owner")
    created_leagues = relationship("League", back_populates="creator")

class Player(Base):
    __tablename__ = "players"

    player_id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.team_id"), default=None, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    behavior_id = Column(Integer, ForeignKey("behaviors.id_behavior"), default=0, nullable=True)  # 0 = behavior por defecto

    shirt_number = Column(Integer, nullable=False)
    name = Column(String(50), nullable=False)
    is_starter = Column(Boolean, default=False, nullable=True)

    power = Column(Integer, nullable=False)
    agility = Column(Integer, nullable=False)
    control = Column(Integer, nullable=False)
    speed = Column(Integer, nullable=False)
    strength = Column(Integer, nullable=False)

    team = relationship("Team", back_populates="players")
    owner = relationship("User", back_populates="players")
    behavior = relationship("Behavior", back_populates="players")

class Team(Base):
    __tablename__ = "teams"

    # un usuario no puede tener dos equipos con el mismo nombre.
    __table_args__ = ( UniqueConstraint('owner_id', 'name', name='uix_owner_team_name'),)

    team_id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    current_league_id = Column(Integer, ForeignKey("leagues.id_league"), nullable=True)  # una liga a la vez

    owner = relationship("User", back_populates="teams")
    current_league = relationship("League", back_populates="teams")
    players = relationship("Player", back_populates="team")
    standings = relationship("LeagueStanding", back_populates="team")
    home_matches = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")

class Behavior(Base):
    __tablename__ = "behaviors"

    id_behavior = Column(Integer, primary_key=True)  # empieza desde 1, 0 es el behavior por defecto
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(50), nullable=False)
    python_code = Column(Text, nullable=False)  # se usa Text para permitir código más largo
    is_default = Column(Boolean, default=False, nullable=False)

    creator = relationship("User", back_populates="behaviors")
    players = relationship("Player", back_populates="behavior")
class Record(Base):
    """Historial del club (del usuario), no de un equipo."""
    __tablename__ = "records"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    leagues_won = Column(Integer, default=0, nullable=False)
    total_points = Column(Integer, default=0, nullable=False)
    matches_won = Column(Integer, default=0, nullable=False)
    matches_lost = Column(Integer, default=0, nullable=False)
    matches_drawn = Column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="record")

class Match(Base):
    __tablename__ = "matches"

    id_match = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.id_league"), nullable=True)  # null si es amistoso
    home_team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=False)  # equipo local / creador
    away_team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=True)  # visitante / oponente; null mientras el amistoso espera rival
    match_duration = Column(Integer, nullable=False)  # duracion del partido(min).
    in_progress = Column(Boolean, nullable=True)
    is_private= Column(Boolean, default=False, nullable=False)
    password = Column(String(255), nullable=True)  # solo si es amistoso y el creador puso password
    # cambiamos Date por Int para almacena solo la "fecha" del partido a manera de secuencia
    scheduled_at = Column(Integer, nullable=True)  # null si es amistoso
    status = Column(String(20), default="open", server_default=text("'open'"), nullable=False)  # open / started / finished / cancelled
    current_period = Column(Integer, default=0, nullable=False)  # 0=no iniciado, 1-4 tiempos
    is_friendly = Column(Boolean, default=True, server_default=text("TRUE"), nullable=False)  # true si es amistoso, false si es de liga

    league = relationship("League", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    result = relationship("MatchResult", back_populates="match", uselist=False)
    
class MatchResult(Base):
    __tablename__ = "match_results"

    match_id = Column(Integer, ForeignKey("matches.id_match"), primary_key=True)
    home_goals = Column(Integer, default=0, nullable=False)
    away_goals = Column(Integer, default=0, nullable=False)

    match = relationship("Match", back_populates="result")
class League(Base):
    __tablename__ = "leagues"

    id_league = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # la crea un usuario
    name = Column(String(100), nullable=False)
    is_private = Column(Boolean, default=False, nullable=False)
    password_hash = Column(String(255), nullable=True)  # solo si is_private=True
    min_teams = Column(Integer, nullable=False, default=3)
    max_teams = Column(Integer, nullable=False)
    match_duration = Column(Integer, nullable=False)  # minutos por tiempo, o duración total, a definir
    status = Column(String(20), default="pending", nullable=False)  # pending / in_progress / finished

    creator = relationship("User", back_populates="created_leagues")
    teams = relationship("Team", back_populates="current_league")
    matches = relationship("Match", back_populates="league")
    standings = relationship("LeagueStanding", back_populates="league")

class LeagueStanding(Base):
    __tablename__ = "league_standings"

    league_id = Column(Integer, ForeignKey("leagues.id_league"), primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.team_id"), primary_key=True)

    points = Column(Integer, default=0, nullable=False)
    matches_won = Column(Integer, default=0, nullable=False)
    matches_drawn = Column(Integer, default=0, nullable=False)
    matches_lost = Column(Integer, default=0, nullable=False)
    goals_for = Column(Integer, default=0, nullable=False)
    goals_against = Column(Integer, default=0, nullable=False)

    league = relationship("League", back_populates="standings")
    team = relationship("Team", back_populates="standings")
