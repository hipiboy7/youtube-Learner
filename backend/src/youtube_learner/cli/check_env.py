"""환경 검사 — 대응: docs/P0_설계서_Common.md 10절 (FR-26). 등급 B.

Trigger: 매 세션·매 Phase 시작에 수동 (scripts\\check_env.ps1 → 이 모듈). CLAUDE.md 1절 0단계.
Input : .env (config.Settings). 외부 네트워크 호출은 없다 — PO 토큰 서버 검사만 루프백(127.0.0.1)을 1초 두드린다.
Output: stdout 에 `[OK]|[WARN]|[FAIL] <항목> — <실측>` 줄들 + 마지막 줄 `==> READY` (종료 0) 또는
        `==> NOT READY (<n> failures)` (종료 1). --json 은 항목 배열, --strict 는 WARN 도 실패.
⚠️ 사전 조건: backend\\.venv 의 python 으로 실행 (3.12). 시스템 python(3.14) 은 패키지가 없다.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from youtube_learner.config import Settings, get_settings, load_json_config
from youtube_learner.exceptions import ConfigError

REQUIRED_PYTHON = (3, 12)
MIN_NODE_MAJOR = 20
#: 필수 모듈과 배포 이름 (버전 표기용)
REQUIRED_MODULES: dict[str, str] = {
    "yt_dlp": "yt-dlp",
    "faster_whisper": "faster-whisper",
    "ctranslate2": "ctranslate2",
    "av": "av",
    "youtube_transcript_api": "youtube-transcript-api",
    "sqlalchemy": "SQLAlchemy",
    "pydantic_settings": "pydantic-settings",
}
CONFIG_FILES = ("stt_default", "ytdlp_default", "sync_default")
BGUTIL_BUILD_HINT = (
    "저장소 루트에서 git clone --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider tools\\bgutil-ytdlp-pot-provider "
    "→ server/ 에서 npm ci && npx tsc (D: 우선 — 홈 디렉토리에 두지 않는다; docs/internal/검토서_트러블슈팅.md T-001)"
)

Runner = Callable[..., subprocess.CompletedProcess[str]]


class Level(StrEnum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class CheckResult:
    name: str
    level: Level
    detail: str


def check_python(
    version: tuple[int, ...] = tuple(sys.version_info[:3]),
    prefix: str = sys.prefix,
    base_prefix: str = sys.base_prefix,
) -> CheckResult:
    version_text = ".".join(str(part) for part in version[:3])
    in_venv = prefix != base_prefix
    if version[:2] != REQUIRED_PYTHON:
        return CheckResult("python", Level.FAIL, f"{version_text} — 3.12 가 필요하다 (py -3.12 -m venv backend\\.venv)")
    if not in_venv:
        return CheckResult("python", Level.FAIL, f"{version_text} 이지만 venv 가 아니다 — backend\\.venv\\Scripts\\python.exe 로 실행")
    return CheckResult("python", Level.OK, f"{version_text} (venv {prefix})")


def _dist_version(dist_name: str) -> str:
    try:
        return importlib.metadata.version(dist_name)
    except importlib.metadata.PackageNotFoundError:
        return "?"


def check_imports(modules: dict[str, str] | None = None) -> list[CheckResult]:
    results: list[CheckResult] = []
    for module_name, dist_name in (modules or REQUIRED_MODULES).items():
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # noqa: BLE001 — import 실패 원인은 다양하다(DLL 누락 등). 전부 FAIL 로 보고한다
            results.append(CheckResult(f"import {module_name}", Level.FAIL, f"{type(exc).__name__}: {exc}"))
        else:
            results.append(CheckResult(f"import {module_name}", Level.OK, f"{dist_name} {_dist_version(dist_name)}"))
    return results


def check_node(which: Callable[[str], str | None] = shutil.which, run: Runner = subprocess.run) -> CheckResult:
    path = which("node")
    if not path:
        return CheckResult(
            "node", Level.FAIL, f"node 를 PATH 에서 찾을 수 없다 — Node ≥ {MIN_NODE_MAJOR} 설치 필요 (yt-dlp JS 런타임·bgutil)"
        )
    try:
        proc = run([path, "--version"], capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult("node", Level.FAIL, f"node --version 실행 실패: {exc}")
    raw = (proc.stdout or proc.stderr or "").strip()
    match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", raw)
    if proc.returncode != 0 or not match:
        return CheckResult("node", Level.FAIL, f"버전을 읽을 수 없다: {raw!r} (exit {proc.returncode})")
    major = int(match.group(1))
    if major < MIN_NODE_MAJOR:
        return CheckResult("node", Level.FAIL, f"{raw} — {MIN_NODE_MAJOR} 이상이 필요하다")
    return CheckResult("node", Level.OK, f"{raw} ({path})")


def check_bgutil_script(settings: Settings) -> CheckResult:
    path = settings.bgutil_script_path
    if path.is_file():
        return CheckResult("bgutil script", Level.OK, str(path))
    return CheckResult("bgutil script", Level.FAIL, f"없음: {path} — {BGUTIL_BUILD_HINT}")


#: 상주 PO 토큰 서버를 띄우는 명령 (tools/ 안 빌드 산출물 — T-001·T-007).
BGUTIL_SERVE_HINT = "node tools\\bgutil-ytdlp-pot-provider\\server\\build\\main.js (scripts\\dev.ps1 이 첫 창으로 띄운다)"
PING_TIMEOUT_S = 1.0


def check_pot_server(
    settings: Settings,
    urlopen: Callable[..., Any] | None = None,
) -> CheckResult:
    """PO 토큰 상주 서버(`GET <base_url>/ping`) 가 응답하는가. 등급 B.

    왜 FAIL 이 아니라 WARN 인가 — 이 서버는 `scripts\\dev.ps1` 이 띄운다. check_env 는 그 **전에** 돌리는
    것이 정상이므로 꺼져 있는 것이 곧 결함은 아니다. 다만 꺼진 채로 자막을 요청하면 script 모드로 내려가
    요청마다 Node 를 띄우고 1코어에서 15초 제한을 넘겨 "코드 문제"로 오진하게 된다(T-007). 그래서 조용히
    넘기지 않고 띄우는 명령까지 같이 보여 준다. `--strict` 면 실패로 본다.
    """
    if not settings.bgutil_http_enabled:
        return CheckResult("pot server", Level.WARN, "BGUTIL_HTTP_ENABLED=false — script 모드로 동작한다 (요청마다 Node 기동, T-007)")
    opener = urlopen or urllib.request.urlopen
    url = f"{settings.bgutil_http_base_url.rstrip('/')}/ping"
    try:
        with opener(url, timeout=PING_TIMEOUT_S) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 — URLError·ConnectionRefused·타임아웃·JSON 오류를 한 줄로 보고한다
        return CheckResult("pot server", Level.WARN, f"{url} 응답 없음 ({type(exc).__name__}) — {BGUTIL_SERVE_HINT}")
    version = payload.get("version", "?")
    uptime = payload.get("server_uptime")
    uptime_text = f", uptime {float(uptime):.0f}s" if isinstance(uptime, (int, float)) else ""
    return CheckResult("pot server", Level.OK, f"{url} — bgutil {version}{uptime_text}")


def check_dirs(settings: Settings) -> CheckResult:
    try:
        settings.ensure_dirs()
        for directory in (settings.data_dir, settings.status_dir, settings.models_dir):
            probe = directory / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
    except (ConfigError, OSError) as exc:
        return CheckResult("dirs", Level.FAIL, f"쓰기 불가: {exc}")
    return CheckResult(
        "dirs", Level.OK, f"DATA_DIR={settings.data_dir} STATUS_DIR={settings.status_dir} HF_HOME={settings.models_dir}"
    )


def _existing_ancestor(path: Path) -> Path:
    current = path
    while not current.exists() and current.parent != current:
        current = current.parent
    return current


def check_disk(settings: Settings, disk_usage: Callable[[Path], Any] = shutil.disk_usage) -> CheckResult:
    target = _existing_ancestor(settings.models_dir)
    try:
        free_gb = disk_usage(target).free / (1024**3)
    except OSError as exc:
        return CheckResult("disk", Level.WARN, f"여유 공간을 읽을 수 없다: {exc}")
    threshold = settings.disk_free_warn_gb
    detail = f"{free_gb:.2f} GB 여유 ({target.anchor or target}) — 기준 {threshold:g} GB"
    if free_gb < threshold:
        return CheckResult("disk", Level.WARN, detail + " 미달. 모델 캐시·P4 빌드 공간 확보 필요 (보류 결정 8)")
    return CheckResult("disk", Level.OK, detail)


def check_config_files(settings: Settings) -> list[CheckResult]:
    results: list[CheckResult] = []
    for name in CONFIG_FILES:
        try:
            data = load_json_config(name, settings)
        except ConfigError as exc:
            results.append(CheckResult(f"config {name}", Level.FAIL, str(exc)))
        else:
            results.append(CheckResult(f"config {name}", Level.OK, f"{len(data)} keys"))
    return results


def check_model_cache(settings: Settings) -> CheckResult:
    hub = settings.models_dir / "hub"
    models = sorted(p.name.removeprefix("models--") for p in hub.glob("models--*")) if hub.is_dir() else []
    if models:
        return CheckResult("whisper model cache", Level.OK, ", ".join(models))
    return CheckResult("whisper model cache", Level.WARN, f"{hub} 에 모델 없음 — 최초 STT 실행 시 다운로드 (small ≈ 464MB)")


def run_checks(
    settings: Settings,
    *,
    which: Callable[[str], str | None] = shutil.which,
    run: Runner = subprocess.run,
    disk_usage: Callable[[Path], Any] = shutil.disk_usage,
) -> list[CheckResult]:
    results: list[CheckResult] = [check_python()]
    results.extend(check_imports())
    results.append(check_node(which=which, run=run))
    results.append(check_bgutil_script(settings))
    results.append(check_pot_server(settings))
    results.append(check_dirs(settings))
    results.append(check_disk(settings, disk_usage=disk_usage))
    results.extend(check_config_files(settings))
    results.append(check_model_cache(settings))
    return results


def render(results: Sequence[CheckResult], *, as_json: bool = False, strict: bool = False) -> tuple[str, int]:
    """(출력 텍스트, 종료 코드). 텍스트 모드의 마지막 줄은 `==> READY` 또는 `==> NOT READY (n failures)`."""
    failing = [r for r in results if r.level is Level.FAIL or (strict and r.level is Level.WARN)]
    exit_code = 1 if failing else 0
    if as_json:
        payload = {"results": [asdict(r) for r in results], "ready": exit_code == 0, "failures": len(failing)}
        return json.dumps(payload, ensure_ascii=False, indent=2), exit_code
    lines = [f"[{r.level}] {r.name} — {r.detail}" for r in results]
    lines.append("==> READY" if exit_code == 0 else f"==> NOT READY ({len(failing)} failures)")
    return "\n".join(lines), exit_code


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="youtubeLearner 환경 검사 — 마지막 줄 ==> READY 가 나와야 작업을 시작한다")
    parser.add_argument("--json", action="store_true", help="항목 배열을 JSON 으로 출력")
    parser.add_argument("--strict", action="store_true", help="WARN 도 실패로 본다")
    args = parser.parse_args(argv)
    try:
        settings = get_settings()
    except ValidationError as exc:
        text, code = render([CheckResult("settings", Level.FAIL, f".env 값이 잘못됐다: {exc.errors()}")], as_json=args.json)
        print(text)
        return code
    text, code = render(run_checks(settings), as_json=args.json, strict=args.strict)
    print(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
