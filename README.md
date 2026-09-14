# youtubeLearner

유튜브 채널을 선택하면 **롱폼·숏폼 영상 목록**과 각 영상의 **전체 스크립트**(자막 → 없으면 로컬 Whisper 음성 인식)를 확보해 학습에 활용하는 프로그램.
요약·핵심 도출은 v1 에 없고 붙일 자리(분석 슬롯)만 있다 — Phase 5.

- **무엇을/왜**: [`docs/scope-definition.md`](docs/scope-definition.md)
- **어떻게**: [`docs/설계서_Architecture.md`](docs/설계서_Architecture.md)
- **작업 규칙**: [`CLAUDE.md`](CLAUDE.md)
- **기획서(승인 2026-09-14)**: [`docs/prompts/phase0/project-plan-v1.md`](docs/prompts/phase0/project-plan-v1.md)

---

## 개발 환경 준비 (Windows · PowerShell)

### ⚠️ Python 3.12 가상환경이 필수다

이 PC 의 기본 `python` 은 **3.14** 이고 프로젝트는 **3.12** 를 요구한다(`backend/pyproject.toml`). 가상환경 없이 실행하면 패키지가 없어 `ModuleNotFoundError` 가 난다.
문서의 모든 명령은 `backend\.venv\Scripts\python.exe` 전체 경로를 쓴다 — 활성화를 잊어도 실패하지 않게.

### 최초 1회

```powershell
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -e "backend[youtube,stt,dev]"
Copy-Item .env.example .env          # .env 는 커밋하지 않는다

# PO 토큰 제공자(bgutil) — pip 패키지만으로는 동작하지 않는다 (docs/internal/검토서_트러블슈팅.md T-001)
git clone --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider "$env:USERPROFILE\bgutil-ytdlp-pot-provider"
Push-Location "$env:USERPROFILE\bgutil-ytdlp-pot-provider\server"; npm ci; npx tsc; Pop-Location

# 프론트
Push-Location frontend; npm install; Pop-Location
```

Node ≥ 20 이 필요하다(yt-dlp JS 런타임·bgutil·프론트 빌드). 이 PC 는 v24.

### 매 세션 — 환경 확인

```powershell
.\scripts\check_env.ps1              # 마지막 줄 ==> READY 가 나와야 작업을 시작한다
```

READY 가 아니면 출력의 `[FAIL]` 줄이 무엇이 빠졀는지 말해준다. `[WARN]`(디스크 여유·모델 캐시 없음)은 작업을 막지 않는다.

---

## 실행

Phase 0 에는 사용자 기능이 없다. 채널 동기화(P1)·스크립트(P2)·화면(P3) 명령은 각 Phase 에서 여기에 추가된다.

### 테스트

```powershell
Push-Location backend
.\.venv\Scripts\python.exe -m pytest                              # 등급 A+B (E2E 제외) — 226건
.\.venv\Scripts\python.exe -m pytest --cov --cov-report=term      # 커버리지 (A ≥ 90%, B ≥ 70%)
.\.venv\Scripts\python.exe -m ruff check src tests ..\scripts\verify_docs.py
Pop-Location
Push-Location frontend; npm test; npm run build; Pop-Location    # 프론트 (Vitest) + 빌드
```

pytest 는 **`backend` 디렉토리에서** 실행한다 — `pyproject.toml` 의 pytest·coverage 설정(측정 대상 `../scripts` 포함)이 그 디렉토리 기준이다. 저장소 루트에서 `--rootdir backend` 로 돌리면 테스트는 같지만 커버리지 대상 경로가 어긋난다.

### 문서 검증

```powershell
backend\.venv\Scripts\python.exe scripts\verify_docs.py
```

문서에 적힌 명령·경로·링크·표가 실제로 동작하는지 검사한다. `pytest` 에 포함되어 있어(`backend/tests/integration/test_docs.py`) 따로 실행하지 않아도 되지만, 문서만 고쳤을 때 빠르게 확인할 수 있다.

> **왜 있는가**: 개발할 때 쓴 명령과 문서에 적은 명령이 다르면 실패하는 것은 독자뿐이고 작성자는 모른다. 사람이 매번 대조하는 것은 신뢰할 수 없어 기계에 맡겼다(`CLAUDE.md` 4절).

---

## 진행 상황

| Phase | 명칭 | 상태 |
|---|---|---|
| 0 | 범위 정의 + 공통 모듈 | 🔄 구현·테스트 완료, Direct 리뷰 대기 (`impl-phase0`) |
| 1 | 채널·영상 목록 | 예정 |
| 2 | 스크립트 파이프라인 | 예정 |
| 3 | 웹 UI | 예정 |
| 4 | 빌드·배포 | 예정 |
| 5 | 분석 플러그인 | 예정 |
| 6 | 모바일 | 예정 |

---

## 디렉토리

```
backend/src/youtube_learner/   백엔드 (Python 3.12) — 설계서_Architecture 2절
  ├── config.py constants.py exceptions.py logging_config.py   [P0] 설정·고정값·예외·로깅
  ├── domain/                 [P0] pydantic 모델 + Protocol 4종 (바깥을 모른다)
  ├── workflow/               [P0] run_context — status/<stage>_<run_id>.json
  ├── repository/             [P0] SQLite 엔진 (테이블은 P1)
  ├── analysis/               [P0] 분석 슬롯 — NullAnalyzer·레지스트리 (구현체는 P5)
  └── cli/                    [P0] check_env
backend/tests/{unit,integration,e2e}/   등급 A / 등급 B / 실호출(-m e2e)
backend/config/                실행마다 조절하는 값 (stt·ytdlp·sync, 각 _comment)
frontend/                      React + Vite + TS (Vitest) — 화면은 P3
scripts/                       check_env.ps1 · verify_docs.py · spike/(등급 C 실측)
docs/                          산출물 (scope-definition · 설계서_Architecture · P{N}_요구사항정의서/설계서/테스트결과서)
docs/internal/                 내부 자료 (TechSpike · SelfReview · 학습가이드 · 용어집 · 트러블슈팅 · templates/)
docs/prompts/phase{N}/         작업 프롬프트·기획서 (요구사항 기록)
history/                       세션별 작업 기록
data/ status/                  런타임 (git 미추적)
```
