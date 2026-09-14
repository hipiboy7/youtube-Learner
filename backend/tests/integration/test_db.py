"""repository/db 검증 — 등급 B. 대응: docs/P0_설계서_Common.md 8절, 요구사항 FR-22~FR-23."""

from __future__ import annotations

from sqlalchemy import text

from youtube_learner.config import Settings
from youtube_learner.repository.db import BUSY_TIMEOUT_MS, init_db, make_engine, make_session_factory


class TestEngine:
    def test_init_db_reports_applied_pragmas(self, tmp_settings: Settings):
        """FR-23 — '설정했다'가 아니라 '적용됐다'를 읽는다: WAL·FK ON·busy_timeout."""
        engine = make_engine(tmp_settings)
        applied = init_db(engine)
        assert applied == {"journal_mode": "wal", "foreign_keys": 1, "busy_timeout": BUSY_TIMEOUT_MS}
        assert tmp_settings.db_path.is_file()
        engine.dispose()

    def test_creates_data_dir_when_missing(self, tmp_settings: Settings):
        assert not tmp_settings.data_dir.exists()
        engine = make_engine(tmp_settings)
        init_db(engine)
        assert tmp_settings.data_dir.is_dir()
        engine.dispose()

    def test_every_connection_has_foreign_keys_on(self, tmp_settings: Settings):
        """FR-22 — foreign_keys 는 연결 단위. 풀에서 나오는 모든 연결에 켜져야 한다."""
        engine = make_engine(tmp_settings)
        init_db(engine)
        with engine.connect() as a, engine.connect() as b:
            assert a.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            assert b.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
        engine.dispose()

    def test_session_factory_roundtrip(self, tmp_settings: Settings):
        engine = make_engine(tmp_settings)
        init_db(engine)
        session_factory = make_session_factory(engine)
        with session_factory() as session:
            assert session.execute(text("SELECT 1")).scalar() == 1
        engine.dispose()

    def test_url_uses_posix_path(self, tmp_settings: Settings):
        engine = make_engine(tmp_settings)
        assert "\\" not in str(engine.url)
        engine.dispose()
