from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, ModelEntry, ModelFlags, RuntimeStatus, StateEntry


class Catalog:
    def __init__(self, database_url: str, cache_dir: Path) -> None:
        self._engine: Engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
        )
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)
        self.cache_dir = cache_dir

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_models(self, runtime: Dict[str, RuntimeStatus]) -> List[Dict]:
        active = self.get_active()
        with self.session() as session:
            entries = session.scalars(select(ModelEntry)).all()
        items: List[Dict] = []
        for entry in entries:
            rt = runtime.get(entry.name)
            items.append(
                {
                    "name": entry.name,
                    "repo": entry.repo,
                    "revision": entry.revision,
                    "default_port": entry.default_port,
                    "default_gpu": entry.default_gpu,
                    "flags": entry.flags_json,
                    "active": entry.name == active,
                    "status": rt.status if rt else "stopped",
                    "port": rt.port if rt else None,
                    "gpu_index": rt.gpu if rt else None,
                    "container_id": rt.container_id if rt else None,
                    "health": rt.health if rt else None,
                }
            )
        return items

    def get(self, name: str) -> Optional[ModelEntry]:
        with self.session() as session:
            entry = session.scalar(select(ModelEntry).where(ModelEntry.name == name))
            return entry

    def add(self, *, name: str, repo: str, revision: Optional[str], default_port: int, default_gpu: int, flags: Dict) -> ModelEntry:
        now = datetime.now(timezone.utc)
        new_entry = ModelEntry(
            name=name,
            repo=repo,
            revision=revision,
            default_port=default_port,
            default_gpu=default_gpu,
            flags_json=flags,
            created_at=now,
            updated_at=now,
        )
        with self.session() as session:
            session.add(new_entry)
        return new_entry

    def delete(self, name: str) -> None:
        with self.session() as session:
            entry = session.scalar(select(ModelEntry).where(ModelEntry.name == name))
            if entry is None:
                return
            session.delete(entry)

    def update_flags(self, name: str, values: Dict) -> None:
        with self.session() as session:
            entry = session.scalar(select(ModelEntry).where(ModelEntry.name == name))
            if entry is None:
                raise ValueError("Model not found")
            entry.flags_json = values
            entry.updated_at = datetime.now(timezone.utc)
            session.add(entry)

    def set_active(self, name: Optional[str]) -> None:
        with self.session() as session:
            if name is None:
                session.merge(StateEntry(key="active_model", value=""))
            else:
                session.merge(StateEntry(key="active_model", value=name))

    def get_active(self) -> Optional[str]:
        with self.session() as session:
            entry = session.get(StateEntry, "active_model")
            if not entry or not entry.value:
                return None
            return entry.value

    def ensure_flags(self, entry: ModelEntry) -> ModelFlags:
        data = {
            "model": entry.repo,
            "revision": entry.revision,
            "download_dir": entry.flags_json.get("download_dir", "/hf-cache"),
            **entry.flags_json,
        }
        return ModelFlags(**data)
