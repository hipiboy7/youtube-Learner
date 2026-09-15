"""프로토타입 — SQLite 테이블(proto_ 접두). 등급 C. 대응: docs/internal/검토서_Prototype.md 3절.

Phase 1 의 정식 스키마와 섞이지 않게 proto_ 접두를 쓴다. 세그먼트는 JSON 텍스트로 넣는다(프로토타입).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from youtube_learner.repository.db import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


class ProtoChannel(Base):
    __tablename__ = "proto_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    yt_channel_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    url: Mapped[str] = mapped_column(String(512))
    title: Mapped[str] = mapped_column(String(256))
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProtoVideo(Base):
    __tablename__ = "proto_videos"
    __table_args__ = (UniqueConstraint("yt_video_id", name="uq_proto_video"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("proto_channels.id"), index=True)
    yt_video_id: Mapped[str] = mapped_column(String(16), index=True)
    kind: Mapped[str] = mapped_column(String(8))
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(512))
    duration_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    view_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    upload_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    transcript_status: Mapped[str] = mapped_column(String(8), default="none")  # none|pending|done|failed
    transcript_source: Mapped[str | None] = mapped_column(String(16), nullable=True)  # manual|auto|whisper
    transcript_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    transcript_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transcript_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # [{idx,start_ms,end_ms,text}]
    transcript_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class ProtoSummary(Base):
    """'요약 및 정리' — 사용자가 외부 AI 챗에서 받아 붙여 넣은 글. analyzer_name='manual' 의 프로토타입."""

    __tablename__ = "proto_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    yt_video_id: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    service: Mapped[str] = mapped_column(String(64), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
