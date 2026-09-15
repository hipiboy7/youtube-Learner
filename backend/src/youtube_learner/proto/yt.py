"""프로토타입 — yt-dlp 접근(탭 목록·메타·원어 자막 json3·오디오). 등급 C. 대응: docs/internal/검토서_Prototype.md 3절.

CLAUDE.md 8절 규칙을 그대로 따른다: 탭 URL flat 추출, 원어 트랙만(`subtitles[lang]` → `automatic_captions[lang-orig]`),
언어 한 번에 하나, bestaudio m4a 후처리 없음, JS 런타임 node, bgutil 스크립트 모드(extractor_args 로 경로 명시).
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yt_dlp

from youtube_learner.config import Settings
from youtube_learner.constants import ORIGINAL_CAPTION_SUFFIX, TranscriptSource, VideoKind
from youtube_learner.domain.models import TranscriptSegment, VideoStub
from youtube_learner.exceptions import YouTubeAccessError

TAB_PATH = {VideoKind.LONG: "videos", VideoKind.SHORT: "shorts"}
_CHANNEL_ID_RE = re.compile(r"^UC[A-Za-z0-9_-]{22}$")


class _QuietLogger:
    """yt-dlp 출력을 삼킨다(프로토타입). 경고는 마지막 것만 보관해 실패 메시지에 붙인다."""

    def __init__(self) -> None:
        self.last_warning = ""

    def debug(self, msg: str) -> None:
        pass

    def info(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        self.last_warning = msg

    def error(self, msg: str) -> None:
        self.last_warning = msg


def _opts(settings: Settings, **extra: Any) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "logger": _QuietLogger(),
        "js_runtimes": {settings.ytdlp_js_runtime: {}},
        "extractor_args": {"youtubepot-bgutilscript": {"script_path": [str(settings.bgutil_script_path)]}},
        "sleep_interval_requests": 1,
    }
    opts.update(extra)
    return opts


#: 네트워크 작업은 한 번에 하나(CLAUDE.md 8절 "워커 1개"). yt-dlp 인스턴스는 스레드 안전이 아니다.
NET_LOCK = threading.Lock()
_ydl_cache: dict[str, yt_dlp.YoutubeDL] = {}


def _ydl(settings: Settings, purpose: str, **extra: Any) -> yt_dlp.YoutubeDL:
    """용도별 YoutubeDL 인스턴스를 재사용한다.

    왜 — 인스턴스를 만들 때마다 bgutil 플러그인이 `node generate_once.js --version` 을 15초 제한으로 실행한다.
    1코어 VM 이 바쁘면(프로토타입 검증 중 CPU 97%) 그 검사가 타임아웃돼 요청이 통째로 실패했다. 재사용하면 검사와
    PO 토큰 메모리 캐시가 프로세스 수명 동안 유지된다. 호출부는 NET_LOCK 안에서 쓴다.
    """
    if purpose not in _ydl_cache:
        _ydl_cache[purpose] = yt_dlp.YoutubeDL(_opts(settings, **extra))
    return _ydl_cache[purpose]


def normalize_channel_url(raw: str) -> str:
    """'@handle' · 'https://www.youtube.com/@handle' · 채널 ID 를 채널 페이지 URL 로."""
    text = raw.strip().rstrip("/")
    if _CHANNEL_ID_RE.match(text):
        return f"https://www.youtube.com/channel/{text}"
    if text.startswith("@"):
        return f"https://www.youtube.com/{text}"
    if not text.startswith("http"):
        return f"https://www.youtube.com/@{text}"
    for suffix in ("/videos", "/shorts", "/streams", "/featured"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
    return text


def list_tab(settings: Settings, channel_url: str, kind: VideoKind, limit: int) -> tuple[dict[str, Any], list[VideoStub]]:
    """탭 flat 목록. (채널 정보, VideoStub 목록). 숏폼 flat 에는 duration 이 없다(TechSpike 3.1절)."""
    url = f"{channel_url}/{TAB_PATH[kind]}"
    try:
        with NET_LOCK:
            ydl = _ydl(settings, "list", extract_flat="in_playlist", playlistend=200)
            ydl.params["playlistend"] = limit
            info = ydl.extract_info(url, download=False)
    except Exception as exc:  # noqa: BLE001 — yt-dlp·플러그인(node 타임아웃 등) 예외를 한 종류로
        raise YouTubeAccessError(f"채널 탭 목록 실패: {url} — {type(exc).__name__}: {exc}") from exc
    channel = {
        "yt_channel_id": info.get("channel_id") or info.get("uploader_id") or "",
        "title": info.get("channel") or info.get("uploader") or info.get("title") or channel_url,
        "url": channel_url,
    }
    stubs: list[VideoStub] = []
    for entry in info.get("entries") or []:
        if not entry or not entry.get("id"):
            continue
        thumbs = entry.get("thumbnails") or []
        stubs.append(
            VideoStub(
                yt_video_id=entry["id"],
                kind=kind,
                title=entry.get("title") or entry["id"],
                url=entry.get("url") or f"https://www.youtube.com/watch?v={entry['id']}",
                duration_s=int(entry["duration"]) if entry.get("duration") is not None else None,
                view_count=entry.get("view_count"),
                thumbnail_url=(thumbs[-1].get("url") if thumbs else None),
            )
        )
    return channel, stubs


def fetch_meta(settings: Settings, video_id: str) -> dict[str, Any]:
    """영상별 메타 + 자막 트랙 목록 (한 요청)."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with NET_LOCK:
            info = _ydl(settings, "meta", skip_download=True).extract_info(url, download=False)
    except Exception as exc:  # noqa: BLE001
        raise YouTubeAccessError(f"영상 메타 실패: {video_id} — {type(exc).__name__}: {exc}") from exc
    return {
        "duration_s": info.get("duration"),
        "upload_date": info.get("upload_date"),
        "language": info.get("language"),
        "live_status": info.get("live_status"),
        "title": info.get("title"),
        "manual_langs": sorted((info.get("subtitles") or {}).keys()),
        "auto_keys": sorted((info.get("automatic_captions") or {}).keys()),
    }


def pick_caption_track(meta: dict[str, Any], lang_priority: Sequence[str]) -> tuple[str, str, TranscriptSource] | None:
    """(트랙 키, 언어, source). 영상 원어 → 우선순위 언어 순으로 수동 → 원어 자동. 번역 트랙은 절대 고르지 않는다."""
    candidates = [lang for lang in [meta.get("language"), *lang_priority] if lang]
    manual, auto = set(meta["manual_langs"]), set(meta["auto_keys"])
    for lang in dict.fromkeys(candidates):
        if lang in manual:
            return lang, lang, TranscriptSource.MANUAL
        orig = f"{lang}{ORIGINAL_CAPTION_SUFFIX}"
        if orig in auto:
            return orig, lang, TranscriptSource.AUTO
    return None


def download_caption_json3(settings: Settings, video_id: str, track_key: str, out_dir: Path) -> Path:
    """원어 트랙 하나만 json3 로 받는다(언어 한 번에 하나 — 429 회피). 파일은 보존한다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{video_id}.{track_key}.json3"
    if target.exists():
        return target
    try:
        with NET_LOCK:
            ydl = _ydl(
                settings, "captions",
                skip_download=True, writesubtitles=True, writeautomaticsub=True,
                subtitlesformat="json3", outtmpl=str(out_dir / "%(id)s.%(ext)s"),
            )
            ydl.params["subtitleslangs"] = [track_key]  # 언어 한 번에 하나 (429 회피)
            ydl.params["outtmpl"] = {"default": str(out_dir / "%(id)s.%(ext)s")}
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
    except Exception as exc:  # noqa: BLE001
        status = 429 if "429" in str(exc) else None
        raise YouTubeAccessError(f"자막 다운로드 실패: {video_id} {track_key} — {type(exc).__name__}: {exc}", status=status) from exc
    if not target.exists():
        raise YouTubeAccessError(f"자막 파일이 생기지 않았다: {target.name}")
    return target


def parse_json3(path: Path) -> list[TranscriptSegment]:
    """json3 events → 세그먼트. 빈 텍스트 제외, start 오름차순, idx 0..n-1."""
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[tuple[int, int, str]] = []
    for event in data.get("events", []):
        segs = event.get("segs")
        if not segs:
            continue
        text = re.sub(r"\s+", " ", "".join(s.get("utf8", "") for s in segs)).strip()
        if not text:
            continue
        start = int(event.get("tStartMs", 0))
        end = start + int(event.get("dDurationMs", 0))
        rows.append((start, end, text))
    rows.sort(key=lambda r: r[0])
    return [TranscriptSegment(idx=i, start_ms=s, end_ms=max(e, s), text=t) for i, (s, e, t) in enumerate(rows)]


def download_audio(settings: Settings, video_id: str, out_dir: Path) -> Path:
    """bestaudio m4a, 후처리 없음(ffmpeg 불필요). 있으면 재사용."""
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = list(out_dir.glob(f"{video_id}.*"))
    if existing:
        return existing[0]
    try:
        with NET_LOCK:
            ydl = _ydl(settings, "audio", format="bestaudio[ext=m4a]/bestaudio", outtmpl=str(out_dir / "%(id)s.%(ext)s"))
            ydl.params["outtmpl"] = {"default": str(out_dir / "%(id)s.%(ext)s")}
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
    except Exception as exc:  # noqa: BLE001
        raise YouTubeAccessError(f"오디오 다운로드 실패: {video_id} — {type(exc).__name__}: {exc}") from exc
    files = list(out_dir.glob(f"{video_id}.*"))
    if not files:
        raise YouTubeAccessError(f"오디오 파일이 생기지 않았다: {video_id}")
    return files[0]


def fetch_via_transcript_api(video_id: str, lang_priority: Sequence[str]) -> tuple[str, TranscriptSource, list[TranscriptSegment]] | None:
    """2순위 폴백 — youtube-transcript-api. (언어, source, 세그먼트) 또는 None(없음)."""
    from youtube_transcript_api import YouTubeTranscriptApi  # 지연 import: 프로토타입 외 경로에 부담을 주지 않게

    try:
        listing = YouTubeTranscriptApi().list(video_id)
        track = listing.find_transcript(list(lang_priority))
    except Exception:  # noqa: BLE001 — 프로토타입: 없음/차단 모두 None
        return None
    if track.is_translatable and getattr(track, "translation_languages", None) and track.language_code not in lang_priority:
        return None
    snippets = list(track.fetch())
    segments = [
        TranscriptSegment(idx=i, start_ms=int(s.start * 1000), end_ms=int((s.start + s.duration) * 1000), text=s.text)
        for i, s in enumerate(snippets)
        if s.text.strip()
    ]
    if not segments:
        return None
    source = TranscriptSource.AUTO if track.is_generated else TranscriptSource.MANUAL
    return track.language_code, source, segments
