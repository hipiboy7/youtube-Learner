"""SQLite 엔진·세션 — 대응: docs/P0_설계서_Common.md 8절 (FR-22~FR-23). 등급 B.

WAL(읽는 동안 쓰기), busy_timeout(짧은 잠금 경합은 대기), foreign_keys ON(SQLite 기본은 OFF, 연결 단위).
테이블은 P1 이 Base 아래에 정의한다. Alembic 도 P1 부터.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from youtube_learner.config import Settings

BUSY_TIMEOUT_MS = 5000


class Base(DeclarativeBase):
    """모든 ORM 모델의 베이스. P0 에는 테이블이 없다."""


def make_engine(settings: Settings, *, echo: bool = False) -> Engine:
    """파일 SQLite 엔진. 연결마다 PRAGMA 를 건다 — foreign_keys 는 연결 단위라 여기서만 켤 수 있다."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{settings.db_path.as_posix()}", echo=echo)

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(engine: Engine) -> dict[str, Any]:
    """테이블을 만들고, PRAGMA 가 **실제로 적용됐는지** 읽어 돌려준다 — "설정했다"와 "적용됐다"는 다르다."""
    Base.metadata.create_all(engine)
    with engine.connect() as connection:
        return {
            "journal_mode": connection.exec_driver_sql("PRAGMA journal_mode").scalar(),
            "foreign_keys": connection.exec_driver_sql("PRAGMA foreign_keys").scalar(),
            "busy_timeout": connection.exec_driver_sql("PRAGMA busy_timeout").scalar(),
        }
