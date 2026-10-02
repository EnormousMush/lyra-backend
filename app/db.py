"""SQLite persistence. Feature dicts and AI outputs are stored as JSON columns."""
from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy import Column, JSON
from sqlmodel import Field, Session, SQLModel, create_engine, select  # noqa: F401

from .config import DB_PATH


def _id() -> str:
    return uuid.uuid4().hex[:16]


def now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: str = Field(default_factory=_id, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str
    password_hash: str
    created_at: datetime = Field(default_factory=now)


class AuthSession(SQLModel, table=True):
    token_hash: str = Field(primary_key=True)
    user_id: str = Field(index=True, foreign_key="user.id")
    expires_at: datetime


class Track(SQLModel, table=True):
    id: str = Field(default_factory=_id, primary_key=True)
    user_id: str = Field(index=True, foreign_key="user.id")
    title: str
    filename: str
    audio_path: str
    # queued -> decoding -> features -> structure -> listening -> ready | error
    stage: str = "queued"
    error: Optional[str] = None
    duration_s: Optional[float] = None
    features: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    sections: Optional[list] = Field(default=None, sa_column=Column(JSON))
    waveform: Optional[list] = Field(default=None, sa_column=Column(JSON))
    dna: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    listening: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)


class Generation(SQLModel, table=True):
    id: str = Field(default_factory=_id, primary_key=True)
    user_id: str = Field(index=True, foreign_key="user.id")
    track_id: str = Field(index=True, foreign_key="track.id")
    batch_id: str = Field(index=True)
    mode: str                      # cover | scenes | variation
    style: str
    aspect: str
    direction: Optional[str] = None
    section_index: Optional[int] = None
    parent_id: Optional[str] = None
    # planning -> rendering -> done | error
    status: str = "planning"
    error: Optional[str] = None
    title: Optional[str] = None
    prompt: Optional[str] = None
    rationale: Optional[str] = None
    palette: Optional[list] = Field(default=None, sa_column=Column(JSON))
    image_path: Optional[str] = None
    mock: bool = False
    favorite: bool = False
    created_at: datetime = Field(default_factory=now)


engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as s:
        yield s
