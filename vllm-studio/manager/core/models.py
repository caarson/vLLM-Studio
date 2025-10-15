from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ModelEntry(Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    repo: Mapped[str] = mapped_column(String(256), nullable=False)
    revision: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    default_port: Mapped[int] = mapped_column(Integer, nullable=False)
    default_gpu: Mapped[int] = mapped_column(Integer, nullable=False)
    flags_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StateEntry(Base):
    __tablename__ = "state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class ModelStatus(str, Enum):
    running = "running"
    starting = "starting"
    stopped = "stopped"
    error = "error"


class ProgressPhase(str, Enum):
    resolving = "resolving"
    downloading = "downloading"
    loading = "loading"
    ready = "ready"
    error = "error"


class ModelFlags(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str
    revision: Optional[str] = None
    download_dir: str = "/hf-cache"
    host: str = "0.0.0.0"
    port: int = 8001
    served_model_name: Optional[str] = None


class ModelCreateRequest(BaseModel):
    name: str = Field(pattern=r"^[a-zA-Z0-9-_.]+$")
    repo: str
    revision: Optional[str] = None
    default_port: int = 8001
    default_gpu: int = 0
    flags: Dict[str, Any] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    name: str
    repo: str
    revision: Optional[str]
    default_port: int
    default_gpu: int
    flags: Dict[str, Any]
    status: ModelStatus
    port: Optional[int]
    gpu_index: Optional[int]
    container_id: Optional[str]
    health: Optional[str]
    active: bool = False


class StartRequest(BaseModel):
    name: str


class StopRequest(BaseModel):
    name: str


class RouteRequest(BaseModel):
    name: str


class SettingsUpdateRequest(BaseModel):
    values: Dict[str, Any]


@dataclass
class RuntimeStatus:
    status: ModelStatus
    port: Optional[int] = None
    gpu: Optional[int] = None
    container_id: Optional[str] = None
    health: Optional[str] = None
