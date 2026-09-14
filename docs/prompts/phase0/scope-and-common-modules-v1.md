# Phase 0 작업 프롬프트 v1 — 범위 정의 + 공통 모듈

- 일자: 2026-09-14
- 요청 LLM 모델: Fable 5.1
- 성격: Phase 0 종속 작업 지시 (`docs/prompts/phase0/`)
- 대응 산출물: `docs/scope-definition.md`, `docs/설계서_Architecture.md`, `CLAUDE.md`, `docs/P0_요구사항정의서_Common.md`, `docs/P0_설계서_Common.md`, `docs/P0_테스트결과서_Common.md`, `backend/` 공통 모듈, `frontend/` 스캐폴드, `scripts/`
- 선행 검증: `docs/internal/P0_검토서_TechSpike.md` (2026-09-14 실측)
- 상태: **제시 — 사용자 확인 대기.** 확인 전에도 작업은 이 판대로 진행하며, 수정 요청이 오면 v2로 개정하고 산출물을 맞춘다

## 사용자 요청 (원문, 2026-09-14)

> 원하는 유튜브 채널을 통해서 학습을 하기 위한 프로그램을 만들고 싶어. […] 특정 유튜브 채널을 선택하면, 해당 유튜브 채널의 롱폼 영상목록, 숏폼 영상목록을 추출하고, 각 영상에 대한 전체 스크립트도 추출하고, 해당 스크립트를 기반으로 내용 요약 및 중요 내용 도출. 스크립트는 영상에서 자체적으로 제공을 안해도 직접 음성으로부터 추출이 가능해야 함.
>
> [요약 기능은] 우선은 해당 기능은 나중에 추가할 수 있게 아키텍처를 잡아보자. 스크립트 뽑는 기능 구현 후 빌드 배포하고, 해당 기능은 버튼 또는 포맷만 만들어놓고 나중에 기능 추가해서 연결할 수 있는 방식으로 진행.
>
> 로컬 웹앱, 데스크톱 앱, 나중에는 스마트폰 앱으로까지 개발 가능해야 함. […] 한국어 채널, 채널당 수백 개 이하로 시작하는데, [다국어·수천 개]로 확장할 수 있는 구조로 설계.
>
> 추가로 내가 진행하고 있는 프로젝트 디렉토리 구조와 방법, 단계, 절차가 있는데, 그 방식을 따를 수 있는지 확인해줘. 참조 URL: https://github.com/SDS-MW-Team/embedding-based-llm-classifier.git […] 우리 프로젝트에 더 적합한게 있다면, 그걸 제안해봐.
>
> https://github.com/hipiboy7/youtube-Learner.git 만들었어, 연결해줘. 그리고 커밋하면 항상 push도 같이해줘.

확정 답변: Python(FastAPI) 백엔드 · 로컬 faster-whisper · React 웹→Tauri→Capacitor · 요약은 슬롯만 · 문서 수준은 참조와 동일(심사 전용 제외) · 혼자 진행(PR 없음) · 개인 GitHub.

## 배경

기획서(승인 2026-09-14)가 참조 방법론을 "따를 수 있다, 다섯 곳만 조정"으로 판정했다: 모노레포, 제품 기능 기반 Phase, "완성본 참조"→"기술 검증(TechSpike)", Windows/PowerShell, 심사 전용 산출물 제외. Phase 0는 그 조정된 방법론을 **문서와 코드로 고정**하고, 이후 Phase가 의존할 공통 모듈을 만든다.

TechSpike(2026-09-14)에서 확인된 사실이 이 프롬프트의 제약이 된다:

| # | 사실 | 이 Phase에 미치는 것 |
|---|---|---|
| F1 | 탭 flat 목록 60건/2.4초. 숏폼 flat에 `duration` 없음, 두 탭 모두 `upload_date` 없음 | 데이터 모델에 "flat 필드"와 "보충 필드"를 구분해 정의 |
| F2 | 원어 자막은 `subtitles[<lang>]` 또는 `automatic_captions[<lang>-orig]`. 다른 언어는 번역 → HTTP 429 | 상수 `ORIGINAL_CAPTION_SUFFIX`, `TranscriptSource` 열거형(manual/auto/whisper; translated는 옵션) |
| F3 | PO 토큰 제공자(bgutil)는 Node ≥ 20 + 빌드된 `generate_once.js` 필요 | `Settings`에 `BGUTIL_SCRIPT_PATH`, `check_env`에 검사 항목 |
| F4 | `bestaudio[ext=m4a]` 후처리 없음 → ffmpeg 불필요, PyAV가 디코딩 | 아키텍처 7절 "도입하지 않은 것: ffmpeg 바이너리" |
| F5 | Whisper small int8 2스레드: 실시간 3.05배 | STT 기본값(`stt_default.json`)과 보류 결정 2의 판정 재료 |
| F6 | youtube-transcript-api 사내 IP에서 1.6초 동작 | Provider 체인 2순위 확정 |
| F7 | 물리 코어 1 / 논리 2, RAM 16GB, GPU 없음, C·D 각 5GB 미만 여유, Rust 없음 | scope 8절 실행 환경, `HF_HOME` 설정, P4 전 디스크 확보 보류 결정 |
| F8 | 롱폼 탭에 42초 영상 존재 | 롱/숏 판정은 탭 소속(보류 결정 3 종료) |

## 작업 지시

Phase 0 사이클(`CLAUDE.md` 1절)을 그대로 밟는다. 순서를 바꾸거나 건너뛰지 않는다.

### A. 상위 문서 3종

1. **`docs/scope-definition.md` v1** — 무엇을/왜. 절 구성: 1 개요 / 2 기능 정의(채널 선택 → 롱폼·숏폼 목록 → 스크립트 → 분석 슬롯) / 3 외부 서비스(YouTube·yt-dlp·bgutil·youtube-transcript-api — **TechSpike 실측 사실과 확인 일자**) / 4 데이터 모델·보존 원칙(SQLite 원본, 파일 산출물, 버전 동반 저장) / 5 스크립트 확보 전략(원어 자막 우선 → 폴백 → Whisper; 언어 정책) / 6 성공 기준(Phase별 기계 판정) / 7 Phase 로드맵(P0~P6, 기획서 3절) / 8 실행 환경(F7 실측) / 9 In·Out of Scope / 10 작업 원칙.
2. **`docs/설계서_Architecture.md` v1** — 어떻게. 0 범위 문서와의 경계 규약 / 1 개요(모노레포, 백엔드=API 서버, 클라이언트 3종) / 2 모듈 구조와 DIP 경계(`VideoListSource`·`TranscriptProvider`·`SttEngine`·`Analyzer` 4 Protocol + 저장소 경계) / 3 외부 연동(yt-dlp 옵션 계약, bgutil 구성, 레이트리밋 원칙) / 4 데이터 흐름(목록 flat → 메타 보충 → 자막 → 오디오 → STT → 정규화 → [분석]; 파일 명명; 하류 덮어쓰기 금지) / 5 STT·분석 슬롯 설계(설정값, NullAnalyzer, 501 계약) / 6 Workflow 규약(CLI 계약, `status/`, 멱등성, 자연키) / 7 기술 스택·값의 3분류·도입하지 않은 것(ffmpeg 바이너리, Redis, Docker-first) / 8 배포 구성(P4 Tauri 사이드카, P6 Capacitor) / 9 테스트 전략(A/B/C, 프론트 Vitest, E2E `-m e2e`) / 10 디렉토리(목표 형태, Phase 귀속 주석) / 11 문서 간 추적성 / 12 개정 이력.
3. **`CLAUDE.md` v1** — 참조 절 구조(0~12) 유지. 0절 프로젝트 요약(목적·환경 실측·핵심 상수·**"요약은 슬롯만"**) / 1절 Phase 절차 + 선행 확인(`scripts/check_env.ps1` → `==> READY`) + **보류된 결정 표**(기획서 5절 7건 + TechSpike 추가: 디스크 확보) / 2 SOLID / 3 TDD 3등급(대상 모듈을 우리 것으로) / 4 Phase 내부 4단계 + 전체 재독 규칙 + 문서 명령 실검사 / 5 하드코딩 금지 3분류 / 6 Workflow·멱등성 / 7 배포(Windows 설치파일 1차, Docker 선택) / 8 **YouTube 연동 규칙**(원어 트랙만, 언어별 요청, 429 백오프, 요청 간격, 네트워크 워커 1개, 실호출 검증·일자 기록) / 9 문서 파일명 규칙(+`검토서_TechSpike` 추가) / 10 요구사항–산출물 페어링 / 11 Git(혼자, PR 없음, `merge --no-ff`, 브랜치 보존, **커밋 즉시 push**, 커밋 금지 대상) / 12 데이터 규칙(SQLite WAL 원본, 원본 자막·Whisper 원출력 보존, UTF-8·LF, 키 영문).

### B. 방법론 도구

4. `docs/internal/templates/` 6종 — **완료(2026-09-14)**. 사용법 README 포함.
5. `.claude/agents/doc-consistency.md`, `.claude/skills/troubleshoot/SKILL.md` 이식 — 독서 순서·경로·프로젝트명을 우리 것으로. `docs/internal/설계서_Agents.md`에 이식 근거와 "만들지 않은 에이전트(report-writer·prompt-finest)와 이유".
6. `docs/internal/용어집.md` 초판 — 롱폼/숏폼, 탭, flat 추출, json3, 원어 트랙(`-orig`), PO 토큰, JS 런타임/EJS, VAD, int8/ctranslate2, 멱등성, 자연키, Protocol/DIP, 등급 A/B/C.
7. `docs/internal/검토서_트러블슈팅.md` 생성 + **T-001**(bgutil pip 설치만으로는 제공자 "unavailable" — 서버 디렉토리 빌드로 해결).

### C. 4단계 산출 (요구사항정의서 → 설계서 → 코드+테스트 → 테스트결과서)

8. **`docs/P0_요구사항정의서_Common.md`** — FR-1~ 번호대. 대상 모듈: `config.py`(Settings: `DATA_DIR`·`STATUS_DIR`·`HF_HOME`·`LOG_LEVEL`·`LOG_FORMAT`·`API_HOST`·`API_PORT`·`CORS_ORIGINS`·`YTDLP_JS_RUNTIME`·`BGUTIL_SCRIPT_PATH`·`BGUTIL_HTTP_BASE_URL`·`STT_CPU_THREADS` 등 **이후 Phase 키까지 한 번에 확정**), `constants.py`(VideoKind·TranscriptSource·AnalysisKind 값, `LANG_PRIORITY_DEFAULT=["ko"]`, `ORIGINAL_CAPTION_SUFFIX="-orig"`, `PIPELINE_VERSION`, DB 파일명, `status/` 패턴), `domain/models.py`(ChannelRef·ChannelInfo·VideoStub·Video·TranscriptSegment·TranscriptResult·AnalysisResult — pydantic v2, 경계에서 거부), `domain/interfaces.py`(4 Protocol), `exceptions.py`(단일 베이스 + YouTube/Transcript/Stt/Analyzer/Storage/Config 하위), `logging_config.py`(JSON 한 줄, UTC, 루트 핸들러 교체), `workflow/run_context.py`(`status/<stage>_<run_id>.json` started/succeeded/failed, 재전파), `repository/db.py`(SQLite 엔진 팩토리: WAL·busy_timeout·외래키, 세션), `analysis/registry.py`+`null_analyzer.py`(이름 기반 레지스트리, v1은 Null만, 미설정 시 `AnalyzerNotConfiguredError`), `cli/check_env.py`(환경 검사 → `==> READY`/`NOT READY`, 종료 코드) + `scripts/check_env.ps1`(얇은 래퍼), `scripts/verify_docs.py`(Windows 규칙: venv 힌트는 `backend\.venv\Scripts\python.exe` 또는 `Activate.ps1`; `powershell`·`bash` 펜스; 접두사 `backend/ frontend/ scripts/ docs/ .claude/ history/ desktop/ mobile/`; 백슬래시 경로 정규화; `.ps1` 실재) + `backend/tests/integration/test_docs.py`(검사기 역테스트 포함), `frontend/` 스캐폴드(Vite+React+TS, Vitest+Testing Library, A등급 유틸 1개 예: `formatTimestamp`, API base URL 설정 자리, "분석" 탭 자리는 P3), `backend/pyproject.toml`(extras: `youtube` `stt` `api` `jobs` `dev`, pytest `-m 'not e2e'`, coverage omit `domain/interfaces.py`), `.env.example`(전 키 + 근거 절), `backend/config/stt_default.json`·`ytdlp_default.json`·`sync_default.json`(각 `_comment`).
9. **`docs/P0_설계서_Common.md`** — 모듈별 인터페이스·설계 판단(왜 Protocol, 왜 pydantic, 왜 SQLite WAL, 왜 Huey는 P2에서, 왜 `HF_HOME`을 우리가 정하나)·검증 방법·구현 순서.
10. **코드 + 테스트** — 등급 A(`constants` 검증 로직·`domain/models`·`run_context` 파일명/상태 전이·`verify_docs` 검사 함수·프론트 유틸)는 **테스트 먼저**. 등급 B(`config`·`logging_config`·`db`·`check_env`·`analysis/registry`·`test_docs`)는 구현 후 통합 테스트. 모듈 docstring 첫 줄 규약 준수.
11. **`docs/P0_테스트결과서_Common.md`** — 실측 커버리지(A ≥ 90%, B ≥ 70%), FR 전건 검증표, `check_env` 실행 출력, `verify_docs` 출력, 프론트 `npm test`·`npm run build` 출력.

### D. 종료 루틴

12. `docs/internal/P0_검토서_SelfReview.md`, `docs/internal/P0_학습가이드_Common.md`.
13. `history/2026-09-14_park.sei_workspace-setup.md`(이 세션의 결정·상태·다음 단계).
14. `doc-consistency` 실행(첫 회, 메인 재검토) → 어긋남 반영 → `pytest`·`verify_docs` 최종 → 커밋·push → 사용자 Direct 리뷰 → `merge --no-ff main` → push(브랜치 보존).

## 완료 기준 (기계 판정)

- [ ] `.\scripts\check_env.ps1` → 마지막 줄 `==> READY`, 종료 코드 0 (이 VM)
- [ ] `backend\.venv\Scripts\python.exe -m pytest` 전건 통과, `tests/integration/test_docs.py` 포함
- [ ] 커버리지 실측: 등급 A ≥ 90%, 등급 B ≥ 70%, A+B ≥ 80% → 테스트결과서 3절
- [ ] `scripts\verify_docs.py` 종료 코드 0 (`README.md`·`CLAUDE.md`·`docs/*.md`·`docs/internal/*.md`·`docs/internal/templates/*.md`)
- [ ] `frontend`: `npm test` 통과, `npm run build` 성공
- [ ] `CLAUDE.md` 1절 보류 결정 표에 8건 이상(기획서 7건 + 디스크 확보) — 각 행에 트리거·판정법·이정표 3요소
- [ ] 4 Protocol이 `backend/src/youtube_learner/domain/interfaces.py`에 있고, `analysis/registry.py`가 `NullAnalyzer`만 등록
- [ ] `.claude/agents/doc-consistency.md`·`.claude/skills/troubleshoot/SKILL.md` 존재, 독서 순서에 우리 경로
- [ ] `docs/internal/P0_검토서_TechSpike.md` 3절이 실제 출력 복사(turbo 측정 포함)
- [ ] 모든 P0 문서가 9절 파일명 규칙을 따르고, 머리말 메타 블록(상위 문서·절번호·작성일·LLM)을 가진다
- [ ] `git log --graph main`에 `impl-phase0` `merge --no-ff` 커밋, `origin/impl-phase0` 보존

## 하지 않는 것 (다른 Phase 책임)

채널 해석·탭 리스팅 구현(P1), 자막·오디오·Whisper 파이프라인(P2), FastAPI 라우터 실체(P1~P3; P0는 `api/` 골격 없음), React 화면(P3), PyInstaller/Tauri(P4), 분석기 구현(P5), Capacitor(P6). `api/`·`youtube/`·`transcripts/`·`stt/`·`jobs/` 패키지는 P0에서 **만들지 않는다** — 빈 패키지는 "있는데 비어 있는" 어긋남을 만든다.
