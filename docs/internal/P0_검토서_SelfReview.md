# P0 검토서 — 자체 점검 (SelfReview)

- 점검일: 2026-09-14 / 작성 LLM: Fable 5.1 / 브랜치: `impl-phase0`
- 규칙: `CLAUDE.md` 1절 6단계. **Direct 리뷰 전에** 수행. 내부 자료(9절 경계)
- 점검 대상: `docs/P0_요구사항정의서_Common.md` 7절 완료 기준 13항, FR-1~FR-34, 코드 12파일, 테스트 13파일(+프론트 3)
- 결론: 결함 8건 발견·전부 수정(🟡 4 · 🟢 4). 요구사항 누락 1건(Protocol 3종 테스트 부재) 보강. 남은 위험 6건, 보류 등재 2건(기존 8번에 흡수 1·P4 인계 1). 완료 기준 13항 충족 — 최종 실측은 `docs/P0_테스트결과서_Common.md`.

> 이 문서의 목적은 자랑이 아니라 **결함 찾기**다.

## 1. 점검에서 찾은 결함 — 8건 (수정 8건 · 남김 0건)

### 1.1 🟡 설계서 시그니처와 구현이 어긋났다 (2곳)

- 증상: `P0_설계서_Common` 7.1절 `run_context(stage, settings, logger=None, *, extra=None)` 인데 구현은 `run_id=None` 키워드 인자가 있다(덮어쓰기 거부 테스트에 결정적 run_id 가 필요해 추가). 8.1절은 "`init_db`가 `DATA_DIR`을 만든다"인데 구현은 `make_engine`이 만든다(SQLite 는 부모 디렉토리 없이는 파일을 못 만들고, 엔진 생성이 경로를 처음 아는 지점).
- 원인: 설계서를 쓴 뒤 **테스트를 쓰다가** 필요가 드러났고 그 자리에서 설계서로 돌아가지 않았다. "문서 → 코드" 방향만 챙기고 "코드 → 문서" 역방향을 놓친 전형.
- 조치: 설계서 7.1·8.1·8.2절 정정(정정 사유 표기). 구현이 맞고 문서가 뒤처진 경우라 코드는 그대로.
- 재발 방지: 테스트 작성 중 시그니처를 바꾸면 **같은 커밋에서** 설계서를 고친다 — SelfReview 체크 항목으로 남긴다(2절 표에 "설계서 시그니처 == 구현" 행).

### 1.2 🟡 `verify_docs` 가 전체 경로 명령(`…\python.exe -m …`)을 명령으로 인식하지 못했다

- 증상: 역테스트 `test_detects_missing_project_module` 실패 — `backend\.venv\Scripts\python.exe -m youtube_learner.cli.nope_module` 줄에서 `module` 위반이 나오지 않았다.
- 원인: `command_lines` 가 명령 머리를 `COMMAND_HEADS` 와 비교할 때 `python.exe` 의 `.exe` 접미를 떼지 않았다. 참조 구현은 Linux(`.venv/bin/python`)라 이 분기가 없었다. **이 프로젝트 문서의 표준 표기 자체**가 검사에서 빠지는 심각한 누락이었고, 저장소 전체 검사에서는 "위반 0"으로 보여 조용했다.
- 조치: `head_name.removesuffix(".exe")`. 역테스트 `test_full_path_python_exe_is_a_command` 추가.
- 재발 방지: 역테스트. **"통과만 확인하면 아무것도 검사하지 않는 검사기도 통과한다"** — 요구사항 FR-30(b) 가 이 사고를 위해 있었고 실제로 잡았다.

### 1.3 🟡 `verify_docs.py` 커버리지 85% — 등급 A 기준(90%) 미달

- 증상: `main()` 이 subprocess 로만 실행되어 커버리지에 잡히지 않았고, `strip_comment` 의 따옴표 분기·`Finding.__str__` 의 저장소 밖 경로 분기가 테스트되지 않았다.
- 조치: 인프로세스 테스트 5건(`TestHelpersAndMain` 4 + `TestCommandLines` 1) 추가 → **97%**. `pyproject.toml` coverage `source` 에 `../scripts` 추가(측정 대상에 넣지 않으면 등급 A 선언이 공허하다), `*/spike/*` 는 omit(등급 C).
- 재발 방지: 커버리지 측정 대상 목록 == 요구사항 5절 등급 표. 테스트결과서 3.4절 "측정 제외"에 이유를 적는다.

### 1.4 🟡 Whisper `small` 모델 캐시가 C: 기본 HF 경로에 남아 P2 에서 재다운로드될 상태였다

- 증상: `check_env` → `[WARN] whisper model cache — …\data\models\hub 에 모델 없음`. TechSpike 는 `HF_HOME` 미설정 상태로 실행돼 464MB 가 `C:\Users\…\.cache\huggingface` 에 있었다.
- 원인: 설계(`HF_HOME` = `DATA_DIR/models`)가 TechSpike **이후**에 정해졌다. 조용한 디스크 낭비 유형(T-002 와 같은 뿌리).
- 조치: 캐시 디렉토리를 `data/models/hub/` 로 이동 → `[OK] whisper model cache — Systran--faster-whisper-small`. C: HF 캐시 디렉토리 비움.
- 재발 방지: `check_env` 모델 캐시 항목이 이제 `HF_HOME` 기준으로 본다. P2 진입점은 `apply_process_env()` 를 import 전에 호출(설계서 15절 인계).

### 1.5 🟢 `pyproject.toml` 의 `readme = "../README.md"` 가 설치를 깨뜨렸다

- 증상: `pip install -e` → `DistutilsOptionError: Cannot access '…\\backend\\../README.md' (or anything outside 'backend')`.
- 조치: `readme` 줄 제거. 패키지 설명은 `description` 으로 충분.

### 1.6 🟢 ruff 줄 길이 120 위반 23건 + 모호한 변수명 1건

- 원인: 한국어 메시지·docstring 이 많아 120 이 의미 없는 줄바꿈을 강요했다.
- 조치: `line-length = 140` (근거를 `pyproject.toml` 주석에), 140 초과 1줄 분할, `l` → `content`. 결과 `All checks passed`.

### 1.7 🟢 설계서 8.1절이 P3 예정 스크립트를 실재 경로처럼 백틱으로 적었다

- 증상: `verify_docs` → `[bare-path] docs\설계서_Architecture.md:276 scripts/dev.ps1`.
- 조치: 문구를 "P3 에서 `scripts/` 아래에 추가한다"로. **검사기가 설계 의도(미래 파일)와 오류(오타)를 구분할 수 없으므로 표기 규칙으로 해결** — 미래 파일은 백틱 대신 코드펜스 트리나 평문.

### 1.8 🟢 요구사항정의서 초안 오기 2건

- FR 범위 "FR-1~35" → 실제 34건. FR-32 의존성 목록에 `python-json-logger` 가 있었으나 설계 판단(6.2절)으로 제거 → 요구사항을 정정(초안 단계라 정정 이력 없이 본문 수정, 변경 사유는 설계서 6.2절에).

## 2. 완료 기준 대비 점검 (요구사항정의서 7절 13항)

| # | 완료 기준 | 충족 | 근거 |
|---|---|---|---|
| 1 | FR-1~34 전건 테스트 존재·통과 | ✅ | 테스트결과서 4절 |
| 2 | 커버리지 A ≥ 90 / B ≥ 70 / A+B ≥ 80 | ✅ | A 97~100%, B 93~100%, 총 97% — 테스트결과서 3절 |
| 3 | `check_env.ps1` → `==> READY` 종료 0 | ✅ | 테스트결과서 5.1절 (WARN 1: 디스크 4.09GB) |
| 4 | bgutil 스크립트 없으면 FAIL·NOT READY | ✅ | `test_check_env.py::TestThisMachine::test_bgutil_removed_makes_not_ready` |
| 5 | `verify_docs.py` 종료 0, pytest 포함 | ✅ | 테스트결과서 5.2절 (최종 실행) |
| 6 | 검사 7종 역테스트 통과 | ✅ | `test_docs.py` 33건 |
| 7 | 프론트 `npm test`·`npm run build` | ✅ | 13 passed, built in 1.50s — 테스트결과서 5.3절 |
| 8 | `build_registry` available 빈 목록, `get("summary")` 예외 | ✅ | `test_analysis_registry.py::TestBuildRegistry` |
| 9 | 상태 파일 덮어쓰기 `OutputExistsError`, 예외 시 failed 재전파 | ✅ | `test_run_context.py` |
| 10 | `.env.example` 키 == Settings 필드 | ✅ | `test_config.py::TestEnvExample` |
| 11 | config JSON 3종 `_comment` + 로더 통과 | ✅ | `test_config.py::TestJsonConfig`, `check_env` config 항목 OK |
| 12 | docstring 첫 줄 규약 전 파일 | ✅ | 수동 대조(3절 표) — 기계 검사는 P1 보류 후보 |
| 13 | `verify_docs.py` 종료 0 (중복 항목) | ✅ | = 5 |
| + | **설계서 시그니처 == 구현** (1.1 에서 추가) | ✅ | 설계서 7.1·8.1 정정 후 대조 |

## 3. 요구사항 누락 점검

| FR | 검증 존재 | 거부 케이스 | 판정 |
|---|---|---|---|
| FR-1~5 (config) | ✅ `test_config.py` 27건 | ✅ 잘못된 값 6종, `_comment` 없음, 비객체 | OK |
| FR-6~8 (constants) | ✅ 34건 | ✅ 빈 키·접미사만·미지 값 | OK |
| FR-9~15 (models) | ✅ 45건 | ✅ 패턴·빈 제목·음수·시간 역행·idx 불연속·frozen·extra | OK |
| FR-16 (Protocol 4종) | ❌→✅ | — | **누락 발견**: `NullAnalyzer` 로 `Analyzer` 만 검증했고 나머지 3종은 테스트가 없었다. `test_interfaces.py` 5건 추가(fake 만족 + 멤버 누락 객체 거부) |
| FR-17 (exceptions) | ✅ 15건 | — (거부 대상 없음) | OK |
| FR-18~19 (logging) | ✅ 9건 | ✅ 예약 키 충돌 | OK |
| FR-20~21 (run_context) | ✅ 15건 | ✅ 덮어쓰기·stage 패턴 | OK |
| FR-22~23 (db) | ✅ 5건 | — | OK (거부 대상 없음) |
| FR-24~25 (analysis) | ✅ 6+7건 | ✅ 중복·비Analyzer·미구현 이름 | OK |
| FR-26~27 (check_env) | ✅ 25건 + 실행 출력 | ✅ 버전·venv·Node 없음/구버전·스크립트 없음·설정 없음 | OK |
| FR-28~30 (verify_docs) | ✅ 33건 | ✅ 7종 역테스트 + 오탐 방지 6종 | OK |
| FR-31 (frontend) | ✅ 13건 | ✅ 음수·NaN·Infinity | OK |
| FR-32~34 (패키징·설정) | ✅ 간접(설치 성공·`_comment`·키 대조) | ✅ | OK — pytest 마커 `-m 'not e2e'` 는 수동 확인(e2e 0건이라 판별 불가, P2 에서 실증) |

## 4. 남은 위험

| # | 위험 | 왜 지금 못 닫나 | 드러나는 시점 | 감지 방법 |
|---|---|---|---|---|
| 1 | `verify_docs` 휴리스틱(`COMMAND_HEADS` 목록, `-0` 예외, 자리표시자 문자) — 새 명령 형태에서 오탐·누락 | 문서가 늘어야 사례가 나온다 | 매 Phase | 위반이 나오면 역테스트 추가 후 규칙 수정 |
| 2 | `check_env` 가 YouTube 차단 상태를 못 본다 | 의도된 범위(READY 가 외부 상태에 흔들리지 않게) | P2 | 작업 실패 카운트(P2 설계) |
| 3 | `Settings` 가 `.env` 를 **현재 디렉토리**에서 읽는다 — 데스크톱 앱(P4)은 실행 디렉토리가 다르다 | 사이드카 실행 방식이 P4 에서 정해진다 | P4 | P4 TechSpike: 사이드카 CWD 확인, 필요 시 `env_file` 을 `resource_root()` 기준으로 |
| 4 | pydantic frozen 모델 ↔ SQLAlchemy ORM 변환 비용·중복 정의 | 첫 테이블이 P1 | P1 | P1 설계서에 변환 함수 위치 명시 |
| 5 | 디스크 여유 C 4.17 / D 4.09GB — P1·P2 오디오 캐시·모델 프리셋이 들어갈 자리가 없다 | 증설은 사용자 결정 | P2 벤치마크(모델 2개 이상 보유 시) | `check_env` disk WARN, 보류 결정 8 |
| 6 | docstring 첫 줄 규약(대응 절·FR·등급)을 사람이 대조했다 | 기계 검사 규칙(정규식)이 아직 없다 | P1 부터 파일이 늘 때 | P1 보류 후보: `verify_docs` 에 docstring 검사 추가 |

## 5. 문서 정합성 점검

- 변경 요약(doc-consistency 에 넘긴 문장): 설계서 정정 2건 · ruff 140 · 모델 캐시 이동 · 보류 결정 3 종료 · python-json-logger 제거 · 테스트 실측치 · check_env 무네트워크 · verify_docs 검사 대상 8건.
- 실행 결과(2026-09-14, sonnet): 지적 9건 → 반영 7건(기술 스택 표의 python-json-logger, FR-20·22·23 시그니처, 디스크 수치 4곳, 학습가이드 216건), 정당 1건(Architecture 6절 사용 예시 — 선택 인자), 정밀도 조정 1건(4.7GB 표기). 요구사항 기록과의 차이 1건(기획서의 보류 결정 3 트리거 — 프롬프트는 고치지 않음).
- 메인 독립 재검토에서 **검사원이 놓친 것 2건**: 이 문서 2절·3절의 `test_docs.py` 31건(실측 33), 학습가이드의 "인프로세스 테스트 3개"(실측 5). 규칙(`설계서_Agents` 3절)대로 다음 실행부터 **opus** 로 승격. 상세는 `docs/internal/설계서_Agents.md` 5절.

## 6. 보류 결정으로 등재할 것

| 결정 | 트리거 | 기계 판정법 | 이정표 문서 |
|---|---|---|---|
| `check_env` 디스크 경고 기준(임시 10GB)의 확정 | P4 착수 | P4 빌드 산출물 크기 실측 → `DISK_FREE_WARN_GB` | 기존 **보류 결정 8** 에 흡수 — 별도 등재 안 함 |
| 로그 파일 출력·`.env` 탐색 위치(사이드카 CWD) | P4 착수 | 사이드카 stdout 캡처 방식·실행 디렉토리 확인 | 테스트결과서 8절 인계로 기록. P4 프롬프트에서 결정 — 별도 등재 안 함(트리거가 P4 하나뿐) |

→ 새 등재 없음. `CLAUDE.md` 보류 결정 표는 8건 유지, 3번은 취소선·종료 처리(TechSpike 근거).

## 7. 잘 됐다고 판단하는 것

- **역테스트가 실제 결함을 잡았다**(1.2). 검사기를 "통과"로만 확인했다면 이 프로젝트 문서의 표준 표기가 영구히 검사에서 빠졌다.
- **TechSpike 를 프롬프트 전에 한 것**이 7건의 문서-실제 차이를 요구사항·설계·상수(`-orig`)·검사 항목(bgutil)에 반영시켰다. 구현 뒤에 알았으면 P2 에서 되돌아왔을 것이다.
- **완료 기준이 기계 판정**이어서(READY·pytest·verify_docs·npm) SelfReview 가 "느낌"이 아니라 출력으로 채워진다.
- **Red 를 확인한 뒤 Green**: A 등급 5파일이 수집 단계에서 실패하는 것을 보고 구현했다(테스트결과서 6.1절).

## 8. 기술 검증(TechSpike)과의 대조

| TechSpike 5절 "반영할 것" | 반영 위치 | 반영됨 |
|---|---|---|
| flat + 메타 보충 2단계 | scope 2.2절, `VideoStub`/`Video` 분리 (FR-11·12) | ✅ |
| 원어 트랙 `-orig`, 번역 기본 제외, 언어별 요청 | `constants.ORIGINAL_CAPTION_SUFFIX`·`split_caption_key` (FR-7·8), CLAUDE 8절, `ytdlp_default.json` `translated_captions=false` | ✅ |
| Provider 체인 3단 | `TranscriptProvider` Protocol (FR-16), scope 5.1절 | ✅ (구현은 P2) |
| bgutil 스크립트 모드 필수 구성 | `Settings.bgutil_script_path`·`bgutil_http_enabled` (FR-1), `check_env` FAIL 항목 (FR-26), `.env.example` | ✅ |
| ffmpeg 미동봉 | `ytdlp_default.json` `audio_format`, Architecture 7.2절 | ✅ |
| Whisper 기본 small·스레드·VAD·beam | `stt_default.json` (FR-34), `STT_CPU_THREADS` | ✅ |
| `HF_HOME` 지정·심볼릭 링크 경고 | `Settings.models_dir`·`apply_process_env` (FR-2·3), 1.4 조치 | ✅ |
| 환경 제약 명시·디스크 보류 결정 | scope 8.1절, CLAUDE 0절·보류 8, `check_env` disk | ✅ |
| 롱/숏 = 탭 소속 | `VideoKind` 주석, CLAUDE 보류 3 종료 | ✅ |

## 9. 결론

Phase 0 의 완료 기준 13항은 전부 기계 판정으로 충족했고, 점검에서 나온 결함 8건은 모두 수정했다. Direct 리뷰에서 먼저 봐야 할 것 두 가지:
1. **`CLAUDE.md` 8절 YouTube 연동 규칙과 보류 결정 8건** — 이후 모든 Phase 가 이 규칙을 전제한다. 실측 근거(TechSpike)가 충분한지, 트리거가 기계로 판정 가능한지.
2. **`.env` 키 목록(FR-1)과 `backend/config/*.json` 기본값** — "한 번에 확정"한 것이라 이름이 어색하면 지금 바꾸는 것이 가장 싸다.
