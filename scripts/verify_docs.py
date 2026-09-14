#!/usr/bin/env python3
"""문서에 적힌 명령·경로·링크가 실제로 동작하는지 기계로 검사한다.

대응: docs/P0_설계서_Common.md 11절 (FR-28~FR-29), CLAUDE.md 4절. 검사 함수 등급 A, main 등급 B.

왜 필요한가
-----------
"개발할 때 쓴 명령과 문서에 적은 명령이 다르면, 실패하는 것은 독자뿐이고 작성자는 모른다."
이 저장소는 Windows 다. 시스템 python 은 3.14 라 패키지가 없고, 프로젝트 venv 는 backend\\.venv 다.
문서가 bare `python` 을 쓰면 독자는 ModuleNotFoundError 를 본다. 사람이 매번 대조하는 것은 신뢰할 수 없어 기계가 본다.

검사 항목 (kind)
---------------
1. venv       bare python/pytest/pip 앞에 활성화 안내(Activate.ps1) 또는 전체 경로(backend\\.venv\\Scripts\\python.exe)가 있는가
2. module     `python -m youtube_learner.*` 모듈을 venv python 으로 import 할 수 있는가
3. path       명령 속 저장소 경로(backend/ frontend/ scripts/ docs/ .claude/ history/ desktop/ mobile/)가 실재하는가 (백슬래시 정규화)
4. ps1        명령 속 scripts\\*.ps1 이 실재하는가 (실행 권한 대신 실재)
5. link       마크다운 상대 링크가 실제 파일을 가리키는가
6. table      표 중간 빈 줄로 표가 쪼개지지 않았는가
7. bare-path  백틱 안 저장소 경로가 실재하는가

사용법
-----
    backend\\.venv\\Scripts\\python.exe scripts\\verify_docs.py
    backend\\.venv\\Scripts\\python.exe scripts\\verify_docs.py --path README.md --quiet

종료 코드: 0 이상 없음 / 1 위반 있음
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"

#: 검사 대상. docs/prompts 는 요구사항 기록(고치지 않고 v2 를 만든다), history 는 사후 수정 금지 기록 → 제외.
DOC_GLOBS = ("README.md", "CLAUDE.md", "docs/*.md", "docs/internal/*.md", "docs/internal/templates/*.md")
SKIP_DIRS = ("docs/prompts",)

#: 저장소 경로로 취급할 접두. 이 밖(패키지 상대 표기 `domain/models.py`, 축약 표기)은 의도가 여러 가지라 판정하지 않는다.
REPO_PREFIXES = ("backend/", "frontend/", "scripts/", "docs/", ".claude/", "history/", "desktop/", "mobile/")
#: 런타임 산출물 — 새 clone 에 없는 것이 정상이다.
RUNTIME_PREFIXES = ("data/", "status/")
#: 환경·빌드 산출물 디렉토리 — git 미추적이라 실재 검사 대상이 아니다.
IGNORED_SUBSTRINGS = ("/.venv/", "/node_modules/", "/dist/", "/build/", "/__pycache__/", "/coverage/")
#: 생성 산출물 확장자.
GENERATED_EXTS = (".db", ".db-wal", ".db-shm", ".sqlite", ".m4a", ".json3", ".parquet", ".pkl", ".log")
#: 이 문자가 있으면 경로가 아니라 패턴·자리표시자·변수다.
PLACEHOLDER_CHARS = ("*", "<", ">", "{", "}", "…", "...", "$", "=", "|", "·", "%")

FENCES = {"powershell", "pwsh", "bash", "sh", "shell", "console", "cmd", "bat"}
_FENCE_START = re.compile(r"^```\s*([A-Za-z0-9_-]+)\s*$")
_FENCE_END = re.compile(r"^```\s*$")
_ANY_FENCE = re.compile(r"^```")

COMMAND_HEADS = {
    "python", "python3", "py", "pytest", "pip", "pip3", "ruff",
    "cd", "cp", "copy", "mv", "move", "rm", "del", "ls", "dir", "cat", "type", "mkdir", "git", "npm", "npx", "node",
    "docker", "echo", "set", "export", "source", "tar", "curl",
    "Set-Location", "Get-Content", "Copy-Item", "Remove-Item", "New-Item", "Push-Location", "Get-ChildItem", "Get-PSDrive",
}

#: venv 를 명시한 것으로 인정하는 표기.
VENV_MARKERS = (".venv\\Scripts\\", ".venv/Scripts/")
ACTIVATE_MARKERS = ("Activate.ps1", ".venv\\Scripts\\activate", ".venv/Scripts/activate")

_BARE = re.compile(r"(?:^|[|&;]\s*)(python3?(?:\.\d+)?(?:\.exe)?|py|pytest|pip3?)(?=\s|$)")
_DASH_M = re.compile(r"\b(?:python3?(?:\.\d+)?(?:\.exe)?|py(?:\s+-3(?:\.\d+)?)?)\s+-m\s+([A-Za-z_][\w.]*)")
_BARE_TOKEN = re.compile(r"`([^`\s]+)`")
_TABLE_ROW = re.compile(r"^\s*\|")
_TABLE_SEPARATOR = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


class Finding:
    def __init__(self, doc: Path, line_no: int, kind: str, detail: str) -> None:
        self.doc = doc
        self.line_no = line_no
        self.kind = kind
        self.detail = detail

    def __str__(self) -> str:
        try:
            rel = self.doc.relative_to(ROOT)
        except ValueError:
            rel = self.doc
        return f"  [{self.kind}] {rel}:{self.line_no}\n      {self.detail}"


# ── 공통 유틸 ─────────────────────────────────────────────────────────────────

def target_docs(explicit: str | None) -> list[Path]:
    if explicit:
        return [ROOT / explicit]
    docs: list[Path] = []
    for pattern in DOC_GLOBS:
        docs.extend(sorted(ROOT.glob(pattern)))
    return [d for d in docs if not any(d.relative_to(ROOT).as_posix().startswith(s) for s in SKIP_DIRS)]


def normalize_path_token(token: str) -> str:
    """백슬래시 → 슬래시, 앞의 ./ .\\ 제거, 따옴표·괄호·쉼표 제거."""
    cleaned = token.strip("\"'`,()[]")
    cleaned = cleaned.replace("\\", "/")
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned


def is_placeholder(token: str) -> bool:
    return any(ch in token for ch in PLACEHOLDER_CHARS)


def strip_comment(line: str) -> str:
    """따옴표 밖의 # 이후를 잘라낸다."""
    result: list[str] = []
    quote: str | None = None
    for ch in line:
        if quote:
            result.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
            result.append(ch)
            continue
        if ch == "#":
            break
        result.append(ch)
    return "".join(result).strip()


def command_lines(text: str) -> list[tuple[int, str]]:
    """셸 펜스(powershell/bash/…) 안의 명령 줄만 (줄 번호, 내용) 으로 뽑는다."""
    out: list[tuple[int, str]] = []
    inside = False
    for line_no, raw in enumerate(text.splitlines(), start=1):
        if not inside:
            match = _FENCE_START.match(raw.strip())
            if match and match.group(1).lower() in FENCES:
                inside = True
            continue
        if _FENCE_END.match(raw.strip()) or (_ANY_FENCE.match(raw.strip()) and not _FENCE_START.match(raw.strip())):
            inside = False
            continue
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for prompt in ("PS> ", "PS ", "$ ", "> "):
            if line.startswith(prompt):
                line = line[len(prompt):].strip()
                break
        head = line.split()[0] if line.split() else ""
        head_clean = head.lstrip("&").strip("\"'")
        if head_clean.startswith((".\\", "./")):
            out.append((line_no, line))
            continue
        # `backend\.venv\Scripts\python.exe` 처럼 전체 경로·.exe 로 쓴 명령도 명령이다 (역테스트가 잡은 누락)
        head_name = head_clean.split("/")[-1].split("\\")[-1].removesuffix(".exe")
        if head_name in COMMAND_HEADS or head_clean in COMMAND_HEADS:
            out.append((line_no, line))
    return out


_tracked_cache: set[str] | None = None


def tracked_files() -> set[str]:
    """git 이 추적하는 파일 목록. 추적되는데 디스크에 없으면 작업 트리가 어긋난 것이라 반드시 알린다."""
    global _tracked_cache
    if _tracked_cache is None:
        proc = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False)
        _tracked_cache = set(proc.stdout.splitlines()) if proc.returncode == 0 else set()
    return _tracked_cache


# ── 검사 1: venv 전제 ────────────────────────────────────────────────────────

def check_venv(doc: Path, text: str, commands: list[tuple[int, str]]) -> list[Finding]:
    lines = text.splitlines()
    activate_line = next(
        (index for index, content in enumerate(lines, start=1) if any(marker in content for marker in ACTIVATE_MARKERS)),
        None,
    )
    findings: list[Finding] = []
    for line_no, line in commands:
        cmd = strip_comment(line)
        if not cmd or any(marker in cmd for marker in VENV_MARKERS):
            continue
        if "-m venv" in cmd or "-0" in cmd.split():  # venv 생성·py 런처 목록은 시스템 python 으로 한다
            continue
        match = _BARE.search(cmd)
        if not match:
            continue
        if activate_line is not None and activate_line < line_no:
            continue
        findings.append(
            Finding(
                doc, line_no, "venv",
                f"`{match.group(1)}` 을 쓰는데 앞에 활성화 안내가 없다. 시스템 python 은 3.14 라 패키지가 없다.\n"
                f"      `backend\\.venv\\Scripts\\python.exe` 전체 경로로 쓰거나 앞에 `backend\\.venv\\Scripts\\Activate.ps1` 을 둔다.\n"
                f"      → {cmd}",
            )
        )
    return findings


# ── 검사 2: python -m 모듈 존재 ──────────────────────────────────────────────

_module_cache: dict[str, bool] = {}


def module_exists(module: str) -> bool:
    if module in _module_cache:
        return _module_cache[module]
    if not VENV_PYTHON.exists():
        _module_cache[module] = False
        return False
    proc = subprocess.run(
        [str(VENV_PYTHON), "-c", f"import importlib.util as u,sys; sys.exit(0 if u.find_spec({module!r}) else 1)"],
        capture_output=True, cwd=ROOT / "backend",
    )
    _module_cache[module] = proc.returncode == 0
    return _module_cache[module]


def check_modules(doc: Path, commands: list[tuple[int, str]]) -> list[Finding]:
    findings: list[Finding] = []
    for line_no, line in commands:
        for module in _DASH_M.findall(strip_comment(line)):
            if not module.startswith("youtube_learner"):
                continue
            if not module_exists(module):
                findings.append(Finding(doc, line_no, "module", f"`python -m {module}` — venv 에서 import 할 수 없다"))
    return findings


# ── 검사 3·4: 경로 실재 / .ps1 실재 ──────────────────────────────────────────

def _skip_candidate(candidate: str) -> bool:
    if not candidate or is_placeholder(candidate):
        return True
    if candidate.startswith(RUNTIME_PREFIXES):
        return True
    if any(sub in f"/{candidate}" for sub in IGNORED_SUBSTRINGS):
        return True
    return candidate.endswith(GENERATED_EXTS)


def check_paths(doc: Path, commands: list[tuple[int, str]]) -> list[Finding]:
    findings: list[Finding] = []
    tracked = tracked_files()
    for line_no, line in commands:
        cmd = strip_comment(line)
        for raw_token in re.split(r"[\s=]+", cmd):
            candidate = normalize_path_token(raw_token)
            if not candidate.startswith(REPO_PREFIXES) or _skip_candidate(candidate):
                continue
            path = ROOT / candidate
            if path.exists():
                continue
            if candidate in tracked:
                findings.append(
                    Finding(doc, line_no, "missing",
                            f"git 이 추적하는데 디스크에 없다: {candidate}\n"
                            f"      작업 트리가 어긋났다. `git checkout -- {candidate}` 로 복구한다.")
                )
            elif candidate.endswith(".ps1"):
                findings.append(Finding(doc, line_no, "ps1", f"스크립트가 없다: {candidate}"))
            else:
                findings.append(Finding(doc, line_no, "path", f"경로가 없다: {candidate}"))
    return findings


# ── 검사 5: 마크다운 링크 ────────────────────────────────────────────────────

def link_targets(line: str) -> list[str]:
    """`](...)` 안의 대상. 괄호 깊이를 세어 파일명 속 괄호를 견딘다."""
    targets: list[str] = []
    i = 0
    while True:
        start = line.find("](", i)
        if start == -1:
            return targets
        j = start + 2
        depth = 1
        while j < len(line):
            if line[j] == "(":
                depth += 1
            elif line[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= len(line):
            return targets
        targets.append(line[start + 2 : j])
        i = j + 1


def check_links(doc: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    in_fence = False
    for line_no, raw in enumerate(text.splitlines(), start=1):
        if _ANY_FENCE.match(raw.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for target in link_targets(raw):
            target = target.split()[0].split("#")[0] if target.split() else ""
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (doc.parent / unquote(target)).exists():
                findings.append(Finding(doc, line_no, "link", f"깨진 링크: {target}"))
    return findings


# ── 검사 6: 표 쪼개짐 ────────────────────────────────────────────────────────

def check_tables(doc: Path, text: str) -> list[Finding]:
    """표 행 → 빈 줄 → 표 행 이고 뒤 표에 구분선이 없으면 쪼개진 것이다. 구분선이 있으면 별개의 표."""
    findings: list[Finding] = []
    lines = text.splitlines()
    in_fence = False
    for index in range(len(lines) - 2):
        stripped = lines[index].strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        if in_fence:
            continue
        before, blank, after = lines[index], lines[index + 1], lines[index + 2]
        if not (_TABLE_ROW.match(before) and blank.strip() == "" and _TABLE_ROW.match(after)):
            continue
        following = lines[index + 3] if index + 3 < len(lines) else ""
        if _TABLE_SEPARATOR.match(following):
            continue
        findings.append(
            Finding(doc, index + 2, "table", "표 중간에 빈 줄이 있어 두 개로 쪼개진다 — 빈 줄을 지워야 행이 표에 붙는다")
        )
    return findings


# ── 검사 7: 백틱 경로 실재 ───────────────────────────────────────────────────

def check_bare_paths(doc: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    tracked = tracked_files()
    in_fence = False
    for line_no, raw in enumerate(text.splitlines(), start=1):
        if _ANY_FENCE.match(raw.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for token in _BARE_TOKEN.findall(raw):
            if is_placeholder(token):
                continue
            normalized = normalize_path_token(token)
            if not normalized.startswith(REPO_PREFIXES):
                continue
            candidate = normalized.split("#")[0].split(":")[0].rstrip("/")
            if _skip_candidate(candidate):
                continue
            if candidate in tracked or (ROOT / candidate).exists() or (doc.parent / candidate).exists():
                continue
            findings.append(Finding(doc, line_no, "bare-path", f"백틱 경로가 실재하지 않는다: {token}"))
    return findings


# ── 실행 ─────────────────────────────────────────────────────────────────────

def verify(doc: Path) -> list[Finding]:
    text = doc.read_text(encoding="utf-8")
    commands = command_lines(text)
    return (
        check_venv(doc, text, commands)
        + check_modules(doc, commands)
        + check_paths(doc, commands)
        + check_links(doc, text)
        + check_tables(doc, text)
        + check_bare_paths(doc, text)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--path", help="특정 문서만 검사 (저장소 기준 상대경로)")
    parser.add_argument("--quiet", action="store_true", help="위반만 출력")
    args = parser.parse_args(argv)

    docs = target_docs(args.path)
    all_findings: list[Finding] = []
    for doc in docs:
        if not doc.is_file():
            all_findings.append(Finding(doc, 0, "missing", "문서가 없다"))
            continue
        findings = verify(doc)
        all_findings.extend(findings)
        if not args.quiet and not findings:
            print(f"  OK  {doc.relative_to(ROOT)}")

    if not all_findings:
        print(f"\n문서 {len(docs)}개 — 위반 없음")
        return 0

    print(f"\n{'=' * 70}\n위반 {len(all_findings)}건\n{'=' * 70}")
    for finding in all_findings:
        print(finding)
    print(
        "\n문서에 적은 명령은 **적은 그대로** 실행해 확인한다 (CLAUDE.md 4절).\n"
        "실행한 명령과 문서에 적은 명령이 다르면 독자만 실패한다."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
