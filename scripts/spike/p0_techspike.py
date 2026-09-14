"""Phase 0 기술 검증(TechSpike) — yt-dlp 탭 목록·json3 자막·오디오·faster-whisper 실측. 등급 C.

Trigger: 수동 1회 (Phase 0 착수, 작업 프롬프트 작성 전). 결과는 docs/internal/P0_검토서_TechSpike.md 에 실제 출력으로 기록한다.
Input : --channel 채널 URL(핸들), --limit 탭당 최대 건수, --model faster-whisper 모델, --threads CPU 스레드, --out 산출 디렉토리
Output: <out>/spike_result.json (실측 요약), <out>/subs/*.json3 (자막 원본), <out>/audio/*.m4a (숏폼 오디오 1건)
⚠️ 사전 조건: backend/.venv 에 yt-dlp[default], bgutil-ytdlp-pot-provider, faster-whisper 설치. 네트워크(YouTube·HuggingFace) 필요.
    실행: backend\\.venv\\Scripts\\python.exe scripts\\spike\\p0_techspike.py --channel https://www.youtube.com/@sebasi15 --limit 60
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import time
from pathlib import Path


def _t() -> float:
    return time.perf_counter()


class _Capture:
    """yt-dlp 로거 — 경고·오류를 모아 PO 토큰/봇 차단 메시지를 검출한다."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def debug(self, msg: str) -> None:
        if msg.startswith("[debug] ") or "pot" in msg.lower():
            self.lines.append(msg)

    def info(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        self.lines.append("WARNING: " + msg)

    def error(self, msg: str) -> None:
        self.lines.append("ERROR: " + msg)


def step_list_tabs(channel: str, limit: int, result: dict) -> tuple[list[dict], list[dict]]:
    import yt_dlp

    tabs: dict[str, list[dict]] = {}
    for tab in ("videos", "shorts"):
        url = channel.rstrip("/") + "/" + tab
        cap = _Capture()
        opts = {
            "extract_flat": "in_playlist",
            "playlistend": limit,
            "quiet": True,
            "no_warnings": False,
            "logger": cap,
            "sleep_interval_requests": 1,
        }
        t0 = _t()
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            entries = [e for e in (info.get("entries") or []) if e]
            keys = sorted({k for e in entries for k, v in e.items() if v is not None})
            durations = [e.get("duration") for e in entries if e.get("duration") is not None]
            result[f"tab_{tab}"] = {
                "url": url,
                "count": len(entries),
                "elapsed_s": round(_t() - t0, 1),
                "channel_id": info.get("channel_id") or info.get("uploader_id"),
                "channel_title": info.get("channel") or info.get("title"),
                "playlist_count_reported": info.get("playlist_count"),
                "entry_keys": keys,
                "has_upload_date": any(e.get("upload_date") for e in entries),
                "has_timestamp": any(e.get("timestamp") for e in entries),
                "duration_min_max": [min(durations), max(durations)] if durations else None,
                "sample": [{k: e.get(k) for k in ("id", "title", "duration", "view_count")} for e in entries[:3]],
                "log": cap.lines[-10:],
            }
            tabs[tab] = entries
        except Exception as exc:  # noqa: BLE001 — 스파이크: 실패도 기록한다
            result[f"tab_{tab}"] = {
                "url": url,
                "error": repr(exc),
                "log": cap.lines[-10:],
                "elapsed_s": round(_t() - t0, 1),
            }
            tabs[tab] = []
    ids_v = {e["id"] for e in tabs["videos"]}
    ids_s = {e["id"] for e in tabs["shorts"]}
    result["tab_overlap_ids"] = sorted(ids_v & ids_s)
    return tabs["videos"], tabs["shorts"]


def _run_ytdlp(args: list[str], cwd: Path) -> dict:
    cmd = [sys.executable, "-m", "yt_dlp", "-v", "--js-runtimes", "node", *args]
    t0 = _t()
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600
    )
    out = proc.stdout + "\n" + proc.stderr
    pattern = re.compile(r"pot|PO Token|js runtime|EJS|deno|node|WARNING|ERROR|Sign in|bot|Destination|Downloading", re.I)
    interesting = [ln for ln in out.splitlines() if pattern.search(ln)]
    return {
        "cmd": " ".join(cmd[3:]),
        "returncode": proc.returncode,
        "elapsed_s": round(_t() - t0, 1),
        "interesting_lines": interesting[:40],
    }


def step_subtitles(video_id: str, out: Path, result: dict) -> None:
    subs_dir = out / "subs"
    subs_dir.mkdir(parents=True, exist_ok=True)
    r = _run_ytdlp(
        [
            "--skip-download", "--write-subs", "--write-auto-subs",
            "--sub-langs", "ko,en", "--sub-format", "json3",
            "-o", "%(id)s.%(ext)s", f"https://www.youtube.com/watch?v={video_id}",
        ],
        subs_dir,
    )
    files = sorted(p.name for p in subs_dir.glob(f"{video_id}*.json3"))
    r["files"] = files
    parsed = []
    for name in files:
        data = json.loads((subs_dir / name).read_text(encoding="utf-8"))
        events = [e for e in data.get("events", []) if e.get("segs")]
        text = "".join(s.get("utf8", "") for e in events for s in e["segs"])
        parsed.append(
            {
                "file": name,
                "events_with_text": len(events),
                "chars": len(text),
                "first_start_ms": events[0].get("tStartMs") if events else None,
                "last_start_ms": events[-1].get("tStartMs") if events else None,
                "preview": re.sub(r"\s+", " ", text)[:160],
            }
        )
    r["parsed"] = parsed
    result["subtitles"] = r


def step_audio(video_id: str, out: Path, result: dict) -> Path | None:
    audio_dir = out / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    r = _run_ytdlp(
        ["-f", "bestaudio[ext=m4a]/bestaudio", "-o", "%(id)s.%(ext)s", f"https://www.youtube.com/watch?v={video_id}"],
        audio_dir,
    )
    files = sorted(audio_dir.glob(f"{video_id}.*"))
    r["files"] = [{"name": p.name, "bytes": p.stat().st_size} for p in files]
    result["audio"] = r
    return files[0] if files else None


def step_whisper(audio: Path, model: str, threads: int, result: dict) -> None:
    from faster_whisper import WhisperModel

    t0 = _t()
    m = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=threads)
    load_s = _t() - t0
    t1 = _t()
    segments, info = m.transcribe(
        str(audio), language="ko", vad_filter=True, beam_size=1, condition_on_previous_text=False
    )
    segs = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments]
    trans_s = _t() - t1
    result[f"whisper_{model}"] = {
        "model": model,
        "compute_type": "int8",
        "cpu_threads": threads,
        "load_s": round(load_s, 1),
        "transcribe_s": round(trans_s, 1),
        "audio_duration_s": round(info.duration, 1),
        "x_realtime": round(info.duration / trans_s, 2) if trans_s else None,
        "language_probability": round(info.language_probability, 3),
        "segments": len(segs),
        "preview": segs[:4],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--channel", required=True)
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--model", default="small")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--out", default="data/spike")
    ap.add_argument("--skip-whisper", action="store_true")
    ap.add_argument("--skip-listing", action="store_true", help="이전 실행의 spike_result.json 목록을 재사용한다")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    import yt_dlp

    result: dict = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "yt_dlp": yt_dlp.version.__version__,
        "channel": args.channel,
    }

    videos, shorts = step_list_tabs(args.channel, args.limit, result)
    if videos:
        step_subtitles(videos[0]["id"], out, result)
    audio = None
    if shorts:
        target = min(shorts, key=lambda e: e.get("duration") or 10**9)
        result["audio_target"] = {k: target.get(k) for k in ("id", "title", "duration")}
        audio = step_audio(target["id"], out, result)
    if audio and not args.skip_whisper:
        try:
            step_whisper(audio, args.model, args.threads, result)
        except Exception as exc:  # noqa: BLE001
            result[f"whisper_{args.model}"] = {"error": repr(exc)}

    (out / "spike_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
