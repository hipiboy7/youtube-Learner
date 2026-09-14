# P0 테스트결과서 — Common

- 상위 문서: `docs/P0_요구사항정의서_Common.md` (초안 2026-09-14) 7절, `docs/P0_설계서_Common.md` (초안 2026-09-14)
- 규칙: `CLAUDE.md` 4절 4단계 산출물. 다음은 `docs/internal/P0_검토서_SelfReview.md` (1절 6단계)
- 실행일: 2026-09-14 / 작성 LLM: Fable 5.1 / 브랜치: `impl-phase0`
- 결과: **전 항목 통과 (PASS)** — 백엔드 226건, 프론트 13건, 환경 검사 READY, 문서 검사 위반 0

> 숫자는 전부 실측이다. 커버리지 표는 `pytest --cov` 출력을 옮겼고, 명령 출력은 그대로 복사했다.

## 1. 실행 환경

| 항목 | 값 |
|---|---|
| OS | Windows Server 2022 Standard (10.0.20348) |
| CPU / RAM / 디스크 여유 | Intel Xeon (Icelake) 물리 1 / 논리 2, 16GB, C: 4.17GB · D: 4.09GB (모델 캐시 464MB 이동 후) |
| Python | 3.12.10 (`backend\.venv\Scripts\python.exe`) |
| Node / npm | v24.14.0 / 11.9.0 |
| 테스트 도구 | pytest 8.4.2, pytest-cov 7.1.0, ruff 0.16.7 / vitest 3.2.7, @vitest/coverage-v8 |
| 주요 패키지 | pydantic 2.13.5, pydantic-settings 2.15.0, SQLAlchemy 2.0.52, yt-dlp 2026.8.19, faster-whisper 1.2.1, ctranslate2 4.8.2, av 18.1.0, youtube-transcript-api 1.2.4, bgutil-ytdlp-pot-provider 2.0.0 |
| 외부 상태 | `scripts\check_env.ps1` → `==> READY` (5.1절). 네트워크 호출 없음(P0 는 외부 서비스 코드를 만들지 않는다) |

## 2. 테스트 결과 요약

| 구분 | 테스트 수 | 결과 |
|---|---|---|
| 등급 A (`backend/tests/unit/`) — constants 34 · exceptions 15 · domain_models 45 · interfaces 5 · run_context 15 · null_analyzer 6 | 120 | PASS |
| 등급 B (`backend/tests/integration/`) — config 27 · logging 9 · db 5 · analysis_registry 7 · check_env 25 · docs 33 | 106 | PASS |
| 프론트 (`frontend/`, vitest) — time 9 · api 3 · App 1 | 13 | PASS |
| E2E (`backend/tests/e2e/`, `-m e2e`) | 0 | 해당 없음 — P0 는 실호출 코드가 없다 |
| **합계 (기본 pytest)** | **226** | **PASS** |

## 3. 등급별 커버리지

`backend\.venv\Scripts\python.exe -m pytest --cov --cov-report=term` (branch 포함). 측정 대상 `youtube_learner` + `scripts/`(spike 제외).

### 3.1 등급 A — 목표 ≥ 90%

| 모듈 | Stmts | Miss | Branch | BrPart | Cover |
|---|---|---|---|---|---|
| `constants.py` | 45 | 0 | 8 | 0 | 100% |
| `domain/models.py` | 122 | 0 | 22 | 0 | 100% |
| `workflow/run_context.py` | 55 | 0 | 2 | 0 | 100% |
| `analysis/null_analyzer.py` | 14 | 0 | 0 | 0 | 100% |
| `scripts/verify_docs.py` (검사 함수 + main) | 275 | 6 | 138 | 7 | 97% |
| **소계** | **511** | **6** | | | **98.8%** (문 기준) → 목표 대비 +8.8%p |

`verify_docs.py` 미커버 6문: venv python 부재 분기(223-224), `--path` 로 없는 파일 이외의 드문 분기(250·269·302·424). 이 VM 에서는 재현할 수 없는 환경 분기다.

### 3.2 등급 B — 목표 ≥ 70%

| 모듈 | Stmts | Miss | Branch | BrPart | Cover |
|---|---|---|---|---|---|
| `cli/check_env.py` | 151 | 11 | 28 | 1 | 93% |
| `config.py` | 84 | 3 | 14 | 1 | 96% |
| `logging_config.py` | 49 | 1 | 8 | 2 | 95% |
| `analysis/registry.py` | 30 | 0 | 6 | 0 | 100% |
| `repository/db.py` | 25 | 0 | 0 | 0 | 100% |
| **소계** | **339** | **15** | | | **95.6%** (문 기준) → 목표 대비 +25.6%p |

`check_env.py` 미커버: 필수 모듈 import 실패 분기(82-83), 디렉토리 쓰기 실패(132-133), 디스크 OSError(150-151), `.env` ValidationError 진입(216-219), `__main__`(226). `config.py`: PyInstaller frozen 분기(36), `ensure_dirs` OSError(104-105) — P4 에서 실증.

### 3.3 A+B 가중 평균 — 목표 ≥ 80%

**97.5%** = (511 − 6 + 339 − 15) / (511 + 339). 도구가 보고한 TOTAL(`__init__` 포함, 872문)은 **97%**.

프론트(`frontend/src/lib/`): `time.ts`·`api.ts` Stmts/Branch/Funcs/Lines **100%** (vitest v8).

### 3.4 측정 제외

| 대상 | 이유 |
|---|---|
| `domain/interfaces.py` | Protocol 선언만 — 실행 로직 없음 (`pyproject.toml` omit). 구조적 서브타이핑은 `test_interfaces.py` 5건으로 검증 |
| `scripts/spike/p0_techspike.py` | 등급 C — 산출물은 `docs/internal/P0_검토서_TechSpike.md` |
| `frontend/src/App.tsx`·`main.tsx` | 자리 화면(P3 에서 교체). 렌더 테스트 1건으로 파이프라인만 확인 |

## 4. 요구사항 대응 검증

| FR | 내용(요약) | 검증 방법 | 결과 |
|---|---|---|---|
| FR-1 | Settings 키 확정·기본값 | `test_config.py::TestDefaults`, `TestDotEnv` | PASS |
| FR-2 | 파생 경로 절대화 | `TestDefaults::test_paths_are_absolute_and_tilde_expanded`, `test_derived_paths`, `test_hf_home_override` | PASS |
| FR-3 | `ensure_dirs`·`apply_process_env` 명시 호출 | `TestSideEffects` (3건 — 생성자 무부작용 포함) | PASS |
| FR-4 | 잘못된 값 로딩 시 거부 | `TestRejects::test_invalid_values` ×6 | PASS |
| FR-5 | `_comment` 필수 JSON 로더 | `TestJsonConfig` (실파일 3종 + 거부 4종) | PASS |
| FR-6 | StrEnum 4종 값 집합 | `test_constants.py::TestEnums` ×6 | PASS |
| FR-7 | 고정 상수·패턴 | `TestFixedValues` ×12 | PASS |
| FR-8 | `split_caption_key`·역함수 | `TestCaptionKey` ×10 | PASS |
| FR-9 | frozen·extra=forbid | `test_domain_models.py::TestVideoStub::test_rejects_unknown_field`, `test_frozen`, `test_model_copy_update_produces_new_object` | PASS |
| FR-10 | `ChannelRef` 식별자 규칙 | `TestChannelRef` ×8 | PASS |
| FR-11 | `VideoStub` flat 규칙 | `TestVideoStub` ×13 | PASS |
| FR-12 | `Video` 보충 필드 | `TestVideo` ×4 | PASS |
| FR-13 | `TranscriptSegment` 거부 규칙 | `TestTranscriptSegment` ×8 | PASS |
| FR-14 | `TranscriptResult` 연속·비감소·파생 | `TestTranscriptResult` ×8 | PASS |
| FR-15 | `AnalyzerInfo`·`AnalysisResult` | `TestAnalysisModels` ×3 | PASS |
| FR-16 | Protocol 4종 runtime_checkable | `test_interfaces.py` ×5, `test_null_analyzer.py::test_satisfies_analyzer_protocol_without_inheritance` | PASS |
| FR-17 | 예외 계층·속성 | `test_exceptions.py` ×15 | PASS |
| FR-18 | JSON 한 줄·멱등·레벨 | `test_logging_config.py::TestSetupLogging` ×5 | PASS |
| FR-19 | 어댑터 병합·bind·예약 키 | `TestContextLoggerAdapter` ×4 | PASS |
| FR-20 | run_id 형식·started/succeeded/failed·재전파 | `test_run_context.py::TestRunId`, `TestRunContext` ×8 | PASS |
| FR-21 | 스키마·덮어쓰기 거부·stage 패턴 | `TestStatusPath`, `test_refuses_to_overwrite_existing_run`, `TestReadStatus` | PASS |
| FR-22 | 엔진·PRAGMA 연결 단위 | `test_db.py::test_every_connection_has_foreign_keys_on`, `test_url_uses_posix_path`, `test_creates_data_dir_when_missing` | PASS |
| FR-23 | `init_db` 적용값 반환 | `test_init_db_reports_applied_pragmas`, `test_session_factory_roundtrip` | PASS |
| FR-24 | `NullAnalyzer` | `test_null_analyzer.py` ×6 | PASS |
| FR-25 | 레지스트리·`build_registry` | `test_analysis_registry.py` ×7 | PASS |
| FR-26 | `check_env` 항목·판정·출력 형식 | `test_check_env.py` ×24 (fake 주입) + 5.1절 실행 출력 | PASS |
| FR-27 | `.ps1` 래퍼 | `test_wrapper_script_exists` + 5.1절 실행(종료 0) | PASS |
| FR-28 | 검사 대상·제외·`--path`·`--quiet` | `test_docs.py::TestRepository::test_prompts_and_history_are_not_checked`, `TestHelpersAndMain` ×4 | PASS |
| FR-29 | 검사 7종 (Windows 규칙) | `TestVenvCheck` ×6, `TestModuleCheck` ×3, `TestPathCheck` ×5, `TestLinkCheck` ×2, `TestTableCheck` ×3, `TestBarePathCheck` ×5, `TestCommandLines` ×2 | PASS |
| FR-30 | 저장소 전체 통과 + 역테스트 + 오탐 방지 | `test_all_docs_pass_verification` + 위 역테스트 | PASS |
| FR-31 | 프론트 스캐폴드·`formatTimestamp`·API URL | `time.test.ts` ×9, `api.test.ts` ×3, `App.test.tsx` ×1, 5.3절 빌드 | PASS |
| FR-32 | pyproject extras·pytest·coverage 설정 | 수동 — 5.4절 설치 출력, 3절 측정이 설정대로(omit·source) 동작 | PASS |
| FR-33 | `.env.example` 전 키 | `TestEnvExample::test_env_example_keys_match_settings_fields` | PASS |
| FR-34 | config JSON 3종 기본값·`_comment` | `TestJsonConfig::test_real_config_files_load_and_strip_comment` ×3, `test_stt_default_values`, `check_env` config OK ×3 | PASS |

## 5. 실연동 검증

### 5.1 환경 검사 — `scripts\check_env.ps1`

```powershell
.\scripts\check_env.ps1
```

```
[OK] python — 3.12.10 (venv D:\claude\youtubeLearner\backend\.venv)
[OK] import yt_dlp — yt-dlp 2026.8.19
[OK] import faster_whisper — faster-whisper 1.2.1
[OK] import ctranslate2 — ctranslate2 4.8.2
[OK] import av — av 18.1.0
[OK] import youtube_transcript_api — youtube-transcript-api 1.2.4
[OK] import sqlalchemy — SQLAlchemy 2.0.52
[OK] import pydantic_settings — pydantic-settings 2.15.0
[OK] node — v24.14.0 (C:\Program Files\nodejs\node.EXE)
[OK] bgutil script — C:\Users\SYSADMIN\bgutil-ytdlp-pot-provider\server\build\generate_once.js
[OK] dirs — DATA_DIR=D:\claude\youtubeLearner\data STATUS_DIR=D:\claude\youtubeLearner\status HF_HOME=D:\claude\youtubeLearner\data\models
[WARN] disk — 4.09 GB 여유 (D:\) — 기준 10 GB 미달. 모델 캐시·P4 빌드 공간 확보 필요 (보류 결정 8)
[OK] config stt_default — 8 keys
[OK] config ytdlp_default — 9 keys
[OK] config sync_default — 5 keys
[OK] whisper model cache — Systran--faster-whisper-small
==> READY
exit=0
```

확인 일자 2026-09-14. 첫 실행에서는 모델 캐시가 `[WARN]`(없음)이었고, 스파이크가 C: 기본 캐시에 내려받은 `small` 을 `data/models/hub/` 로 옮긴 뒤 `[OK]` 가 됐다(6.4절). 디스크 WARN 은 보류 결정 8.

거부 케이스(bgutil 스크립트 경로를 없는 곳으로): `test_check_env.py::TestThisMachine::test_bgutil_removed_makes_not_ready` — 마지막 줄 `==> NOT READY (1 failures)`, 종료 1.

### 5.2 문서 실검사 — `scripts\verify_docs.py`

```powershell
backend\.venv\Scripts\python.exe scripts\verify_docs.py
```

최종 실행 출력(산출물 전부 작성 후, 2026-09-14):

```
  OK  README.md
  OK  CLAUDE.md
  OK  docs\P0_설계서_Common.md
  OK  docs\P0_요구사항정의서_Common.md
  OK  docs\P0_테스트결과서_Common.md
  OK  docs\scope-definition.md
  OK  docs\설계서_Architecture.md
  OK  docs\internal\P0_검토서_SelfReview.md
  OK  docs\internal\P0_검토서_TechSpike.md
  OK  docs\internal\P0_학습가이드_Common.md
  OK  docs\internal\README.md
  OK  docs\internal\검토서_트러블슈팅.md
  OK  docs\internal\설계서_Agents.md
  OK  docs\internal\용어집.md
  OK  docs\internal\templates\README.md
  OK  docs\internal\templates\템플릿_검토서_SelfReview.md
  OK  docs\internal\templates\템플릿_검토서_TechSpike.md
  OK  docs\internal\templates\템플릿_설계서.md
  OK  docs\internal\templates\템플릿_요구사항정의서.md
  OK  docs\internal\templates\템플릿_테스트결과서.md
  OK  docs\internal\templates\템플릿_학습가이드.md

문서 21개 — 위반 없음
exit=0
```

작성 도중의 중간 실행은 **의도대로 위반을 잡았다**: 아직 없던 `docs/P0_테스트결과서_Common.md`·SelfReview·`history/` 참조 9건과, 설계서 8.1절이 P3 예정 파일 `dev.ps1` 을 실재 경로처럼 적은 1건(6.6절).

### 5.3 프론트 — `npm test` · `npm run build`

```
 ✓ src/lib/time.test.ts (9 tests) 7ms
 ✓ src/lib/api.test.ts (3 tests) 6ms
 ✓ src/App.test.tsx (1 test) 132ms
 Test Files  3 passed (3)
      Tests  13 passed (13)
```
```
> tsc --noEmit -p tsconfig.json && vite build
vite v7.3.6 building client environment for production...
✓ 29 modules transformed.
dist/index.html                  0.33 kB │ gzip:  0.24 kB
dist/assets/index-Bm__X34J.js  223.12 kB │ gzip: 69.80 kB │ map: 1,055.11 kB
✓ built in 1.50s
```
커버리지(`npm run test:coverage`): `api.ts` 100/100/100/100, `time.ts` 100/100/100/100. `node_modules` 155 패키지 102MB.

### 5.4 패키지 설치 — `pip install -e "backend[youtube,stt,dev]"`

```
pydantic                  2.13.5
pydantic-settings         2.15.0
pytest                    8.4.2
pytest-cov                7.1.0
ruff                      0.16.7
SQLAlchemy                2.0.52
youtube-learner           0.1.0     D:\claude\youtubeLearner\backend
```
ruff: `All checks passed!` (line-length 140 — 6.3절).

## 6. 재작업·특이사항

### 6.1 등급 A 는 Red 를 확인한 뒤 Green (구현 순서 기록)

테스트 5파일을 먼저 쓰고 실행: `ModuleNotFoundError: No module named 'youtube_learner.constants'` — `ERROR tests/unit/test_constants.py … test_run_context.py`, `Interrupted: 5 errors during collection`, 종료 2. 구현 후 115 passed. (interfaces 5건은 SelfReview 3절 누락 보강으로 추가.)

### 6.2 `pyproject.toml` `readme = "../README.md"` 로 설치 실패 (구현 중 발견) ⚠️

- 증상: `distutils.errors.DistutilsOptionError: Cannot access 'D:\\claude\\youtubeLearner\\backend\\../README.md' (or anything outside 'D:\\claude\\youtubeLearner\\backend')`
- 조치: `readme` 줄 제거.

### 6.3 ruff 위반 24건 → 줄 길이 기준 140 으로 (구현 중 결정)

E501 23건(한국어 메시지·docstring)·E741 1건. 120 은 의미 없는 줄바꿈을 강요해 **140** 으로 정하고 근거를 `backend/pyproject.toml` 주석에 남겼다. 140 초과 1줄 분할, `l` → `content`.

### 6.4 Whisper `small` 캐시 위치 (조용한 디스크 낭비) ⚠️

TechSpike 는 `HF_HOME` 미설정으로 실행돼 464MB 가 `C:\Users\…\.cache\huggingface` 에 있었고 `check_env` 는 `data/models` 를 보므로 WARN. 캐시를 이동해 재다운로드를 막았다. 기록: `docs/internal/검토서_트러블슈팅.md` T-002, SelfReview 1.4.

### 6.5 `verify_docs` 가 전체 경로 명령을 놓쳤다 — 역테스트가 잡음 ⚠️

`test_detects_missing_project_module` 실패(`assert 'module' in set()`). 원인·조치는 SelfReview 1.2. 커버리지 85% → 인프로세스 테스트 5건 추가 → 97%.

### 6.6 설계서와 구현의 차이 2건 정정

`run_context(run_id=)` 인자, `make_engine` 의 `data_dir` 생성 — 구현이 맞고 문서가 뒤처짐. 설계서 7.1·8.1·8.2절 정정(SelfReview 1.1). 설계서 8.1절 `dev.ps1` 표기도 `verify_docs` 지적으로 수정.

### 6.7 최종 검증 실행 (산출물 전부 작성 후)

아래 9절 명령을 순서대로 실행한 결과(2026-09-14, `backend` 디렉토리에서):

```
== pytest --cov ==
D:\claude\youtubeLearner\scripts\verify_docs.py     275      6    138      7    97%   223-224, 250, 269, 293->301, 302, 406->400, 424
TOTAL                                               872     21    226     11    97%
226 passed in 4.82s

== ruff check src tests ..\scripts\verify_docs.py ==
All checks passed!

== scripts\verify_docs.py ==
문서 21개 — 위반 없음   (exit 0 — 전체 목록은 5.2절)

== scripts\check_env.ps1 ==
==> READY   (WARN 1: disk 4.09 GB — 보류 결정 8)

== frontend ==
Tests 13 passed (13) / ✓ built in 1.50s
```

주의 — 저장소 루트에서 `pytest --rootdir backend backend\tests --cov` 로 돌리면 테스트 결과는 같지만 coverage `source` 의 `../scripts` 가 CWD 기준으로 어긋나 TOTAL 이 1835문(98%)으로 부풀어 보인다. 커버리지는 `backend` 에서 측정한 값만 인정한다.

## 7. 완료 기준 대조 (요구사항정의서 7절)

- [x] FR-1~34 전건에 대응하는 테스트가 존재하고 통과한다 — 4절
- [x] 등급 A ≥ 90% (98.8%), B ≥ 70% (95.6%), A+B ≥ 80% (97.5%) — 3절
- [x] `.\scripts\check_env.ps1` 마지막 줄 `==> READY`, 종료 0 — 5.1절
- [x] bgutil 스크립트를 없는 경로로 바꾸면 `[FAIL]`·`NOT READY` — `test_bgutil_removed_makes_not_ready`
- [x] `scripts\verify_docs.py` 종료 0, pytest 포함 — 5.2절·6.7절, `test_all_docs_pass_verification`
- [x] 검사 7종 역테스트 통과 — `test_docs.py` 33건
- [x] `frontend`: `npm test` 13 passed, `npm run build` 성공 — 5.3절
- [x] `build_registry` `available()` 빈 목록, `get("summary")` → `AnalyzerNotConfiguredError` — `TestBuildRegistry`
- [x] 상태 파일 덮어쓰기 `OutputExistsError`; 예외 시 `failed` 기록 후 재전파 — `TestRunContext`
- [x] `.env.example` 키 집합 == `Settings` 필드 집합 — `TestEnvExample`
- [x] `backend/config/*.json` 3종 `_comment` 보유, 로더 통과 — `TestJsonConfig`, 5.1절
- [x] 모듈·테스트 docstring 첫 줄 규약 전 파일 — 수동 대조(SelfReview 2절 12항; 기계 검사는 P1 보류 후보)
- [x] `scripts/verify_docs.py` 종료 0 — 6.7절

## 8. 다음 Phase 인계 사항

| 항목 | 내용 | 받는 Phase |
|---|---|---|
| `Settings.apply_process_env()` 호출 계약 | faster-whisper import **전에** 진입점이 호출 | P2 |
| `Base` 빈 스키마 | 첫 테이블(`channels`·`videos`·`analyses` 예약)·Alembic 초기 리비전. `VideoStub`/`Video` ↔ ORM 변환은 저장소 계층 | P1 |
| `build_registry` 미구현 이름 예외 | 이름→팩토리 표로 대체 | P5 |
| `resource_root()` frozen 분기·`.env` 탐색 위치(CWD) | 사이드카 실행 디렉토리 확인 후 `env_file` 기준 결정 | P4 |
| `check_env` 디스크 기준 10GB(임시)·모델 캐시 위치 | P4 빌드 실측 후 갱신 (보류 결정 8) | P4 |
| `verify_docs` docstring 규약 기계 검사 | 파일이 늘기 전에 규칙 추가 (P1 보류 후보) | P1 |
| P1 TechSpike 질문 | 채널 전량 페이지네이션·숏폼 100+·메타 보충 속도·`curl_cffi` 효과 (`P0_검토서_TechSpike` 6절) | P1 |

## 9. 재현 명령

```powershell
.\scripts\check_env.ps1
Push-Location backend
.\.venv\Scripts\python.exe -m pytest --cov --cov-report=term
.\.venv\Scripts\python.exe -m ruff check src tests ..\scripts\verify_docs.py
Pop-Location
backend\.venv\Scripts\python.exe scripts\verify_docs.py
Push-Location frontend; npm test; npm run build; Pop-Location
```

기대값: READY(종료 0) / 226 passed, TOTAL 97% / All checks passed / 문서 21개 — 위반 없음(종료 0) / 13 passed, built. 소요 약 2분(프론트 빌드 포함).
pytest 는 **`backend` 디렉토리에서** 실행한다 — coverage `source` 의 `../scripts` 가 그 디렉토리 기준이다(6.7절).
