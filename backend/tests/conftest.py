"""공용 fixture — 최소한만. 대응: docs/P0_설계서_Common.md 0절.

무거운 fixture 는 각 테스트 파일에 지역으로 둔다. 여기에는 여러 파일이 같은 방식으로 쓰는 것만.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """격리된 DATA_DIR/STATUS_DIR 을 가진 Settings. .env 를 읽지 않도록 tmp 로 chdir 한다."""
    from youtube_learner.config import Settings

    monkeypatch.chdir(tmp_path)
    for key in ("DATA_DIR", "STATUS_DIR", "HF_HOME", "CONFIG_DIR", "LOG_LEVEL", "LOG_FORMAT", "API_PORT",
                "CORS_ORIGINS", "STT_CPU_THREADS", "ANALYZERS", "DISK_FREE_WARN_GB", "BGUTIL_SCRIPT_PATH"):
        monkeypatch.delenv(key, raising=False)
    return Settings(data_dir=tmp_path / "data", status_dir=tmp_path / "status")
