"""프로토타입 — faster-whisper 전사. 등급 C. 대응: docs/internal/검토서_Prototype.md 3절.

settings.apply_process_env() 를 faster_whisper import 전에 호출한다(P0_설계서_Common 15절 계약).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from youtube_learner.config import Settings, load_json_config
from youtube_learner.domain.models import TranscriptSegment

ProgressCallback = Callable[[float], None]


def transcribe(
    settings: Settings, audio_path: Path, language: str | None, on_progress: ProgressCallback | None = None
) -> tuple[str, list[TranscriptSegment]]:
    """(모델 이름, 세그먼트). stt_default.json 의 model·vad·beam 을 그대로 쓴다."""
    settings.apply_process_env()
    from faster_whisper import WhisperModel  # noqa: PLC0415 — HF_HOME 적용 뒤에 import 해야 한다

    cfg = load_json_config("stt_default", settings)
    model_name = cfg["model"]
    repo = cfg["model_repos"].get(model_name, model_name)
    model = WhisperModel(
        repo, device="cpu", compute_type=cfg["compute_type"], cpu_threads=cfg["cpu_threads"] or settings.stt_cpu_threads
    )
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=cfg["vad_filter"],
        beam_size=cfg["beam_size"],
        condition_on_previous_text=cfg["condition_on_previous_text"],
    )
    duration = max(info.duration or 0.0, 0.001)
    out: list[TranscriptSegment] = []
    for seg in segments_iter:
        text = seg.text.strip()
        if not text:
            continue
        start_ms, end_ms = int(seg.start * 1000), int(seg.end * 1000)
        out.append(TranscriptSegment(idx=len(out), start_ms=start_ms, end_ms=max(end_ms, start_ms), text=text))
        if on_progress:
            on_progress(min(seg.end / duration, 0.99))
    if on_progress:
        on_progress(1.0)
    return model_name, out
