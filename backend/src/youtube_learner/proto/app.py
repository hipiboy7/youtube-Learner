"""프로토타입 — FastAPI. 등급 C. 대응: docs/internal/검토서_Prototype.md 3절.

Trigger: `backend\\.venv\\Scripts\\python.exe -m uvicorn youtube_learner.proto.app:app --port 8765` (scripts/dev_proto.ps1)
Input : .env (DATA_DIR·CORS_ORIGINS·bgutil), backend/config/{sync,stt}_default.json
Output: SQLite proto_* 테이블, data/channels/<cid>/{captions,audio}/ 파일
⚠️ 사전 조건: scripts\\check_env.ps1 → READY. Whisper 는 백그라운드 스레드 1개(동시 1건).
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from youtube_learner.config import Settings, get_settings, load_json_config
from youtube_learner.constants import MANUAL_ANALYZER_NAME, TranscriptSource, VideoKind
from youtube_learner.exceptions import YoutubeLearnerError
from youtube_learner.logging_config import setup_logging
from youtube_learner.proto import stt, yt
from youtube_learner.proto.store import ProtoChannel, ProtoSummary, ProtoVideo, now_utc
from youtube_learner.repository.db import init_db, make_engine, make_session_factory

settings: Settings = get_settings()
settings.ensure_dirs()
logger = setup_logging(settings)
engine = make_engine(settings)
init_db(engine)
SessionLocal = make_session_factory(engine)
sync_cfg = load_json_config("sync_default", settings)
LANG_PRIORITY: list[str] = list(sync_cfg["lang_priority"])
_whisper_lock = threading.Lock()  # CPU 1개 — STT 동시 1건
_active: set[str] = set()  # 지금 이 프로세스가 처리 중인 영상 — DB 의 stale 'pending' 과 구분해 재시도를 허용한다
_active_lock = threading.Lock()
CAPTIONS_DIR = settings.data_dir / "proto" / "captions"
AUDIO_DIR = settings.data_dir / "proto" / "audio"

app = FastAPI(title="youtubeLearner prototype", version="0.0.1")
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"]
)


class ChannelIn(BaseModel):
    url: str
    limit: int = Field(default=20, ge=1, le=200)


class SummaryIn(BaseModel):
    text: str
    service: str = ""


class TranscriptIn(BaseModel):
    force_whisper: bool = False


def _video_out(v: ProtoVideo, with_transcript: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": v.id, "yt_video_id": v.yt_video_id, "kind": v.kind, "title": v.title, "url": v.url,
        "duration_s": v.duration_s, "view_count": v.view_count, "thumbnail_url": v.thumbnail_url,
        "upload_date": v.upload_date, "language": v.language,
        "transcript_status": v.transcript_status, "transcript_source": v.transcript_source,
        "transcript_language": v.transcript_language, "transcript_model": v.transcript_model,
        "transcript_error": v.transcript_error, "progress": v.progress,
    }
    if with_transcript:
        segments = json.loads(v.transcript_json) if v.transcript_json else []
        out["segments"] = segments
        out["full_text"] = " ".join(s["text"] for s in segments)
    return out


def _get_video(session: Session, yt_video_id: str) -> ProtoVideo:
    video = session.scalar(select(ProtoVideo).where(ProtoVideo.yt_video_id == yt_video_id))
    if not video:
        raise HTTPException(404, f"영상 없음: {yt_video_id}")
    return video


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "prototype": True, "time": datetime.now(UTC).isoformat()}


@app.get("/analyzers")
def analyzers() -> list[dict[str, Any]]:
    """자동 분석기 목록 — v1 은 빈 목록(NullAnalyzer 만). 수동 요약은 /proto/videos/{id}/summary."""
    return []


@app.get("/proto/channels")
def list_channels() -> list[dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.scalars(select(ProtoChannel).order_by(ProtoChannel.id)).all()
        result = []
        for ch in rows:
            videos = session.scalars(select(ProtoVideo).where(ProtoVideo.channel_id == ch.id)).all()
            result.append({
                "id": ch.id, "yt_channel_id": ch.yt_channel_id, "title": ch.title, "url": ch.url,
                "synced_at": ch.synced_at.isoformat() if ch.synced_at else None,
                "counts": {k.value: sum(1 for v in videos if v.kind == k.value) for k in (VideoKind.LONG, VideoKind.SHORT)},
            })
        return result


@app.post("/proto/channels")
def add_channel(body: ChannelIn) -> dict[str, Any]:
    """채널 URL/핸들 → 롱폼·숏폼 탭 flat 목록(limit 씩) → upsert. 멱등(yt_video_id)."""
    channel_url = yt.normalize_channel_url(body.url)
    try:
        info_long, long_stubs = yt.list_tab(settings, channel_url, VideoKind.LONG, body.limit)
        _, short_stubs = yt.list_tab(settings, channel_url, VideoKind.SHORT, body.limit)
    except YoutubeLearnerError as exc:
        raise HTTPException(502, str(exc)) from exc
    if not info_long["yt_channel_id"]:
        raise HTTPException(502, "채널 ID 를 확인할 수 없다")
    with SessionLocal() as session:
        channel = session.scalar(select(ProtoChannel).where(ProtoChannel.yt_channel_id == info_long["yt_channel_id"]))
        if not channel:
            channel = ProtoChannel(yt_channel_id=info_long["yt_channel_id"], url=channel_url, title=info_long["title"])
            session.add(channel)
            session.flush()
        channel.title, channel.url, channel.synced_at = info_long["title"], channel_url, now_utc()
        added = 0
        for stub in [*long_stubs, *short_stubs]:
            row = session.scalar(select(ProtoVideo).where(ProtoVideo.yt_video_id == stub.yt_video_id))
            if row is None:
                row = ProtoVideo(channel_id=channel.id, yt_video_id=stub.yt_video_id, kind=stub.kind.value, title=stub.title, url=stub.url)
                session.add(row)
                added += 1
            row.title, row.url = stub.title, stub.url
            row.duration_s = stub.duration_s if stub.duration_s is not None else row.duration_s
            row.view_count, row.thumbnail_url = stub.view_count, stub.thumbnail_url
        session.commit()
        logger.info(
            "채널 동기화",
            extra={"yt_channel_id": channel.yt_channel_id, "long": len(long_stubs), "short": len(short_stubs), "added": added},
        )
        return {"id": channel.id, "yt_channel_id": channel.yt_channel_id, "title": channel.title,
                "counts": {"long": len(long_stubs), "short": len(short_stubs)}, "added": added}


@app.get("/proto/channels/{channel_id}/videos")
def list_videos(channel_id: int, kind: str = "long") -> list[dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(ProtoVideo).where(ProtoVideo.channel_id == channel_id, ProtoVideo.kind == kind).order_by(ProtoVideo.id)
        ).all()
        summaries = {s.yt_video_id for s in session.scalars(select(ProtoSummary).where(ProtoSummary.text != "")).all()}
        return [{**_video_out(v), "has_summary": v.yt_video_id in summaries} for v in rows]


@app.get("/proto/videos/{yt_video_id}")
def get_video(yt_video_id: str) -> dict[str, Any]:
    with SessionLocal() as session:
        return _video_out(_get_video(session, yt_video_id), with_transcript=True)


def _save_transcript(yt_video_id: str, source: TranscriptSource, language: str, model: str | None, segments) -> None:
    with SessionLocal() as session:
        video = _get_video(session, yt_video_id)
        video.transcript_status, video.transcript_source = "done", source.value
        video.transcript_language, video.transcript_model = language, model
        video.transcript_json = json.dumps([s.model_dump() for s in segments], ensure_ascii=False)
        video.transcript_error, video.progress = None, 1.0
        session.commit()


def _fail_transcript(yt_video_id: str, message: str) -> None:
    with SessionLocal() as session:
        video = _get_video(session, yt_video_id)
        video.transcript_status, video.transcript_error = "failed", message[:2000]
        session.commit()


def _set_progress(yt_video_id: str, value: float) -> None:
    with SessionLocal() as session:
        video = _get_video(session, yt_video_id)
        video.progress = round(value, 3)
        session.commit()


def _whisper_worker(yt_video_id: str, language: str | None) -> None:
    """백그라운드 1스레드. 오디오 → Whisper → 저장. 어떤 실패든 failed 로 기록하고 _active 에서 뺀다."""
    try:
        with _whisper_lock:
            audio = yt.download_audio(settings, yt_video_id, AUDIO_DIR)
            _set_progress(yt_video_id, 0.05)
            model, segments = stt.transcribe(
                settings, audio, language, on_progress=lambda p: _set_progress(yt_video_id, 0.05 + 0.95 * p)
            )
            if not segments:
                _fail_transcript(yt_video_id, "Whisper 결과가 비어 있다")
                return
            _save_transcript(yt_video_id, TranscriptSource.WHISPER, language or "auto", model, segments)
            logger.info("whisper 완료", extra={"yt_video_id": yt_video_id, "segments": len(segments)})
    except Exception as exc:  # noqa: BLE001 — 프로토타입: 실패 사유를 화면에 보인다
        logger.error("whisper 실패", extra={"yt_video_id": yt_video_id, "error": str(exc)})
        _fail_transcript(yt_video_id, f"{type(exc).__name__}: {exc}")
    finally:
        with _active_lock:
            _active.discard(yt_video_id)


@app.post("/proto/videos/{yt_video_id}/transcript")
def fetch_transcript(yt_video_id: str, body: TranscriptIn | None = None) -> dict[str, Any]:
    """원어 자막(yt-dlp json3) → 폴백(youtube-transcript-api) → Whisper(백그라운드). CLAUDE.md 8절 규칙.

    실패는 500 이 아니라 영상 상태 `failed` + 사유로 돌려준다(화면이 보여 준다). DB 에 stale 'pending' 이 남아 있어도
    이 프로세스가 처리 중이 아니면 다시 시도한다.
    """
    force = bool(body and body.force_whisper)
    with _active_lock:
        if yt_video_id in _active:
            return get_video(yt_video_id)
        _active.add(yt_video_id)
    with SessionLocal() as session:
        video = _get_video(session, yt_video_id)
        video.transcript_status, video.transcript_error, video.progress = "pending", None, 0.0
        session.commit()

    language: str | None = None
    try:
        meta = yt.fetch_meta(settings, yt_video_id)
        language = meta.get("language")
        with SessionLocal() as session:
            v = _get_video(session, yt_video_id)
            v.duration_s = meta.get("duration_s") or v.duration_s
            v.upload_date, v.language = meta.get("upload_date"), language
            session.commit()
        if not force:
            picked = yt.pick_caption_track(meta, LANG_PRIORITY)
            if picked:
                key, lang, source = picked
                path = yt.download_caption_json3(settings, yt_video_id, key, CAPTIONS_DIR)
                segments = yt.parse_json3(path)
                if segments:
                    _save_transcript(yt_video_id, source, lang, None, segments)
                    with _active_lock:
                        _active.discard(yt_video_id)
                    return get_video(yt_video_id)
            fallback = yt.fetch_via_transcript_api(yt_video_id, [language, *LANG_PRIORITY] if language else LANG_PRIORITY)
            if fallback:
                lang, source, segments = fallback
                _save_transcript(yt_video_id, source, lang, "youtube-transcript-api", segments)
                with _active_lock:
                    _active.discard(yt_video_id)
                return get_video(yt_video_id)
    except Exception as exc:  # noqa: BLE001 — 메타·자막 경로 실패는 기록하고 Whisper 로 넘어간다 (오디오도 실패하면 worker 가 failed 기록)
        logger.warning("자막 경로 실패 — Whisper 로 넘어간다", extra={"yt_video_id": yt_video_id, "error": f"{type(exc).__name__}: {exc}"})

    threading.Thread(target=_whisper_worker, args=(yt_video_id, language), daemon=True).start()
    return get_video(yt_video_id)


def _summary_out(yt_video_id: str, row: ProtoSummary) -> dict[str, Any]:
    return {
        "yt_video_id": yt_video_id, "text": row.text, "service": row.service,
        "updated_at": row.updated_at.isoformat(), "analyzer_name": MANUAL_ANALYZER_NAME,
    }


@app.get("/proto/videos/{yt_video_id}/summary")
def get_summary(yt_video_id: str) -> dict[str, Any]:
    with SessionLocal() as session:
        row = session.scalar(select(ProtoSummary).where(ProtoSummary.yt_video_id == yt_video_id))
        if not row:
            return {"yt_video_id": yt_video_id, "text": "", "service": "", "updated_at": None, "analyzer_name": MANUAL_ANALYZER_NAME}
        return _summary_out(yt_video_id, row)


@app.put("/proto/videos/{yt_video_id}/summary")
def put_summary(yt_video_id: str, body: SummaryIn) -> dict[str, Any]:
    """'요약 및 정리' 저장 — 사용자가 외부 AI 챗에서 받아 붙여 넣은 글(analyzer_name='manual')."""
    with SessionLocal() as session:
        _get_video(session, yt_video_id)
        row = session.scalar(select(ProtoSummary).where(ProtoSummary.yt_video_id == yt_video_id))
        if not row:
            row = ProtoSummary(yt_video_id=yt_video_id)
            session.add(row)
        row.text, row.service, row.updated_at = body.text, body.service, now_utc()
        session.commit()
        return _summary_out(yt_video_id, row)
