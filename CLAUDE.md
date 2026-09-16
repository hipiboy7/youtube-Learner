# CLAUDE.md — 작업 규칙

`youtubeLearner` 프로젝트(유튜브 채널 롱폼·숏폼 목록 + 스크립트 추출, 자막 → 로컬 Whisper)에서
코드·문서를 만들 때 항상 지켜야 할 규칙이다.

- **무엇을/왜**: [`docs/scope-definition.md`](docs/scope-definition.md)
- **어떻게**: [`docs/설계서_Architecture.md`](docs/설계서_Architecture.md)
- **어떤 규칙으로**: 이 문서 (충돌 시 이 문서 우선)
- **초기 요구·결정 원문**: [`docs/internal/qa/P0_질의응답_초기요구.md`](docs/internal/qa/P0_질의응답_초기요구.md)

> **v2 개정 사유 (2026-09-16)**: 사용자 요청으로 산출물 효율을 검토했다. Phase 0 실적은 문서 4,036줄 대 코드 1,127줄이었고,
> 같은 사실이 최대 11개 파일에 적혀 있었다(예: "Whisper 기본 모델 = small"). 정합성 검사에서 나온 어긋남 31건의 대부분이
> **우리 문서끼리의 불일치**였다 — 중복이 만든 비용이다. 그래서 (1) Phase 당 문서를 3개로 줄이고, (2) **단일 출처 규칙**(5절)을 세우고,
> (3) 중복 감시용 `doc-consistency` 에이전트를 없애고(대신 5.1절 grep 규칙), (4) E2E 스모크 테스트와 사용자용 문제 해결 문서를 요구에 넣었다.
> 결정 기록: [`docs/internal/qa/질의응답_방법론개정.md`](docs/internal/qa/질의응답_방법론개정.md)

## 0. 프로젝트 요약 (작업 전 필수 확인)

> **이 절은 5절 단일 출처 규칙의 유일한 예외다.** 매 세션 자동 로드되므로 "5분 안에 실수하지 않을 만큼"의 사실을 여기 둔다.
> 값이 출처와 어긋나면 **출처가 맞다.** 값을 고칠 때는 출처와 이 절 두 곳만 고치면 된다.

- **목적**: 사용자가 고른 유튜브 채널의 **롱폼·숏폼 영상 목록**과 각 영상의 **전체 스크립트**(세그먼트+타임스탬프)를 확보해 학습에 쓴다.
- **스크립트 소스 우선순위**: 수동 자막(`manual`) → 원어 자동 자막(`auto`, 트랙 키 `<lang>-orig`) → 로컬 faster-whisper(`whisper`). 번역 자막은 기본 꺼짐 — 다른 언어를 요청하면 HTTP 429. → 출처 `constants.py`, 상세 `docs/scope-definition.md` 5절
- **자동 요약·핵심 도출은 v1에 없다.** 인터페이스·레지스트리·API 501·화면 자리만 만든다(구현은 Phase 5). **수동 흐름은 v1이다**: 스크립트 **원클릭 복사** → 사용자가 외부 AI 챗에서 요약 → **'요약 및 정리'에 붙여 넣어 저장**(`analyses`, `analyzer_name="manual"`) — Phase 3.
- **롱/숏 판정은 탭 소속**(`/videos` vs `/shorts`)이다. 길이로 판정하지 않는다.
- **스택**: Python 3.12 (`backend\.venv`), FastAPI, SQLite(WAL)+SQLAlchemy, Huey(SQLite), yt-dlp[default]+bgutil PO 토큰 **상주 서버**(Node, `127.0.0.1:4416`), faster-whisper int8, React+Vite+TS → Tauri(P4) → Capacitor(P6).
- **개발 환경**: Windows Server 2022, 물리 코어 1/논리 2, RAM 16GB, GPU 없음, Node 24, ffmpeg·Rust·gh 없음. 디스크·속도 실측은 `docs/internal/P0_실측기록_Common.md` 1절.
- **자연키**: `yt_channel_id`(UC…), `yt_video_id`. 스크립트 유일성은 (video, source, language, model_name, pipeline_version).
- **외부 서비스 3종**: YouTube(yt-dlp 경유) / bgutil PO 토큰 상주 서버(`tools/bgutil-ytdlp-pot-provider/server/build/main.js`) / Hugging Face Hub(모델 1회 다운로드). YouTube Data API·클라우드 STT/LLM은 쓰지 않는다.

## 1. Phase 진행 절차 (반복 사이클)

총 7단계(Phase 0~6)를 아래 절차로 반복한다. 각 Phase는 **완료 기준을 충족할 때까지** 이 사이클을 돈다.

| Phase | 명칭 | 산출물 |
|---|---|---|
| 0 | 범위 정의 + 공통 모듈 | ✅ 완료 (`main` 병합 `6480b0b`) |
| 1 | 채널·영상 목록 | 채널 해석, `/videos`·`/shorts` 탭 리스팅, 증분 동기화, 메타 보충, DB 스키마(`channels`·`videos`·`analyses`), API·CLI |
| 2 | 스크립트 파이프라인 | Provider 체인, json3 파싱·정규화, 오디오→Whisper, Huey 큐·재시도·재개, 모델 벤치마크 |
| 3 | 웹 UI | React 화면 일체 — 목록·뷰어(**원클릭 복사**)·**'요약 및 정리' 수동 입력·저장**·작업·설정, 자동 분석 자리 |
| 4 | 빌드·배포 | PyInstaller onedir 사이드카 + Tauri + NSIS, 모델 최초 다운로드. **깨끗한 Windows VM 검증** |
| 5 | 분석 플러그인 | **자동** 분석기 구현(`analysis/` 안에서만), 화면에 출처(`manual`/분석기) 표시 |
| 6 | 모바일 | Capacitor Android, 서버 URL 설정 |

**Phase 1~3은 프로토타입을 정식 구조로 이관한다** (사용자 결정 2026-09-16). `prototype/e2e-slice` 브랜치가 전 경로를 실측해 두었으므로
같은 기술 검증을 다시 하지 않는다. 근거는 [`docs/internal/검토서_Prototype.md`](docs/internal/검토서_Prototype.md) 를 인용한다.

### 각 Phase의 진행 순서

0. **⚠️ 환경 확인 (필수 선행)** — 가장 먼저 실행한다.

   ```powershell
   .\scripts\check_env.ps1
   ```

   마지막 줄이 `==> READY`가 아니면 그 Phase의 개발·테스트·검증을 시작하지 않는다. 몇 번을 실행해도 안전하다.

0-1. **⚠️ 보류된 결정 확인 (필수 선행)** — 이전 Phase에서 "나중에 판단한다"로 넘긴 사항이 이번 Phase의 트리거인지 확인한다.

   | # | 열린 결정 | 트리거 | 확인 방법 | 이정표 문서 |
   |---|---|---|---|---|
   | 1 | **분석 엔진 선택** — 추출식 / 로컬 LLM(Ollama) / Claude API. v1은 `NullAnalyzer`만 | Phase 5 착수 | `GET /analyzers`가 빈 목록을 반환하는가 | `docs/scope-definition.md` 2.4절 |
   | 2 | **Whisper 기본 모델 확정** — 현재 값은 설정 파일이 갖고 있고 medium·WER 은 미측정이다 | Phase 2 벤치마크 | `backend/config/stt_default.json`의 `model` + P2 실측기록의 모델별 벤치표 | `docs/internal/P0_실측기록_Common.md` 4절 |
   | 3 | ~~숏폼 판정 기준(탭 vs 길이 보조)~~ → **탭 소속으로 결정 (2026-09-14)** | 종료 (P1 전량 실측 시 재확인) | P1 동기화 결과에서 두 kind에 모두 있는 `yt_video_id` 건수 = 0 | `docs/internal/P0_실측기록_Common.md` 4절 |
   | 4 | **Python 3.14 전환** — 3.12 고정 | Phase 4 패키징 완료 후 | CI 매트릭스 3.14 잡 통과 여부 | `docs/설계서_Architecture.md` 7절 |
   | 5 | **P5(분석) vs P6(모바일) 순서** | Phase 4 종료 | 사용자 결정 기록 (`docs/internal/qa/`) | `docs/scope-definition.md` 7절 |
   | 6 | **서버 배포(Docker) 여부** — 데스크톱 우선 | Phase 6 착수 | 모바일이 LAN 밖 접속을 요구하는가 | `docs/설계서_Architecture.md` 8.3절 |
   | 7 | **YouTube Data API 키 병행** | yt-dlp 목록 경로 차단 발생 시 | `VideoListSource` 구현체가 2개인가 | `docs/scope-definition.md` 3.6절 |
   | 8 | **디스크 확보** — 사용자가 D: 를 증설했다(2026-09-15). P4 의 Rust 툴체인·빌드 산출물이 들어갈 자리를 다시 확인한다 | Phase 4 착수 | `check_env`의 디스크 여유 항목이 경고 없이 통과 | `docs/scope-definition.md` 8.1절 |
   | 9 | **PO 토큰 상주 서버의 배포 형태** — 개발은 `dev_proto.ps1` 이 띄운다. 배포(P4)에서 사이드카가 Node 서버를 함께 띄울지, 다른 수단을 쓸지 | Phase 4 착수 | 설치파일에 PO 토큰 수단이 포함돼 깨끗한 VM 에서 자막이 받아지는가 | `docs/internal/검토서_Prototype.md` |

   **결정을 문서 각주로만 남기지 않는다.** 보류하는 순간 (a) 트리거, (b) 기계로 판정하는 방법, (c) 돌아갈 이정표 문서를 이 표에 함께 등재한다.

1. **설계서 작성** — `docs/P{N}_설계서_<Topic>.md` 한 문서에 **목적·범위·요구사항(FR)·설계 판단·완료 기준**을 담는다(4절).
   프로토타입이 이미 실측한 Phase(1~3)는 기술 검증을 건너뛰고 `검토서_Prototype` 을 근거로 인용한다.
   새로운 외부 동작에 의존하는 Phase(4·5·6)는 **설계서를 쓰기 전에** 실제로 호출해 보고 결과를 `docs/internal/P{N}_실측기록_<Topic>.md` 에 먼저 적는다.
2. **사용자에게 설계서를 설명하고 확인받는다.** 별도 작업 프롬프트 파일은 만들지 않는다(10절). 사용자 요청 원문과 결정은 `docs/internal/qa/` 에 남긴다.
3. **브랜치 생성** — `main`에서 `impl-phase{N}` 분기. 첫 커밋과 함께 `origin`에 push.
4. **코드 + 테스트** — 3절 등급 기준. 등급 A는 테스트 먼저.
5. **실측기록 작성** — `docs/internal/P{N}_실측기록_<Topic>.md`: 실호출 출력·완료 기준 대조·재작업 내역·남은 위험·다음 Phase 인계.
   테스트 수와 커버리지는 **옮겨 적지 않는다** — 재현 명령만 적는다(5절).
6. **학습 가이드** — `docs/internal/P{N}_학습가이드_<Topic>.md`. 사용자가 직접 실행해 확인하는 실습과 예상 질문.
7. **Direct 리뷰** — 사용자가 직접 리뷰한다(PR 리뷰가 아님). 지적을 반영할 때는 5.1절 grep 절차를 따른다.
8. **Phase 종료 루틴** — 병합 **전에** 한다.

   ```
   ① pytest (test_docs 포함) / scripts\verify_docs.py / 프론트 npm test·build / check_env / E2E 스모크 — 전부 통과
   ② history/<날짜>_<작업자>_<주제>.md — 종료 시점 상태·다음 단계
   ③ 산출물 커밋 → push (브랜치에)
   ④ merge --no-ff → push (브랜치는 삭제하지 않는다 — 11절)
   ```

### 원칙: 근거는 우리 것으로

작업 중 선행 사례나 외부 자료를 참고할 수 있다. 그러나 **산출물에는 우리 판단의 근거만 남긴다.** "다른 곳이 이렇게 했으므로"는 근거가 아니다.
어떤 결정이든 그 자체로 정당한 이유를 서술한다. 이유를 쓸 수 없다면 그 결정을 다시 검토한다. 판단이 바뀌면 지우지 말고 정정 이력으로 남긴다(10절).

## 2. SOLID 준수

- **SRP**: 모듈/클래스/함수는 하나의 책임만. "유튜브에서 가져오기", "json3 파싱", "저장", "일 시키기"는 별도 모듈.
- **OCP**: 변경 가능성 있는 값(자막 언어 우선순위, Whisper 모델·스레드, 요청 간격·재시도)은 코드 수정 없이 설정으로.
- **LSP**: 공통 인터페이스 구현을 대체 구현으로 바꿔도 호출부가 안 깨진다.
- **ISP**: 거대한 클래스보다 필요한 기능만 노출하는 작은 인터페이스.
- **DIP**: 상위 로직은 구체 클래스가 아니라 **Protocol**에 의존한다 — `VideoListSource`·`TranscriptProvider`·`SttEngine`·`Analyzer`(`domain/interfaces.py`).
  **영상 목록 소스·스크립트 소스·STT 엔진·분석기는 변경 가능성이 가장 높은 네 축**이다. 구체 구현 선택은 조립 지점 한 곳에서만.

## 3. 테스트 — 선별 적용

코드 성격에 따라 3등급 + E2E. 판단이 애매하면 **"입출력이 결정적인가"**(같은 입력 → 항상 같은 출력)를 기준으로.

| 등급 | 대상 | 규칙 | 커버리지 |
|---|---|---|---|
| **A. 핵심 순수 로직** | 파싱·정규화·판정·상태 전이·순수 유틸 (`constants` 검증, `domain/models`, `run_context`, `json3_parser`, `channel_resolver`, `jobs/state`, 프론트 `formatTimestamp`·`copyText`) | Red→Green→Refactor로 **테스트 먼저**. 테스트 없는 변경은 미완료 | **≥ 90%** |
| **B. 오케스트레이션/통합** | 설정·IO·외부 의존 (`config`, `repository/*`, `cli/*`, `youtube/*`, `transcripts/*`, `stt/*`, `jobs/tasks`, `api/*`, React 컴포넌트) | 구현 후 통합 테스트. 외부는 Protocol fake 또는 기록된 응답 | **≥ 70%** |
| **C. 탐색/실측** | `scripts/spike/*`, 벤치마크 | 자동 테스트 미강제. **실측기록 문서**로 대체 | 측정 제외 |

- A+B 가중 평균 **≥ 80%**. 테스트 파일은 대상 코드와 1:1. `domain/interfaces.py`는 측정 제외.
- 배치: A → `backend/tests/unit/`, B → `backend/tests/integration/`, 프론트는 대상 파일 옆 `*.test.ts(x)`.
- **거부 케이스 필수**: 부적합 입력을 거부하는 모듈은 정상 케이스만 테스트하면 아무것도 안 하는 구현도 통과한다.

### E2E 스모크 테스트 (Phase 1부터 필수)

**사용자 흐름이 실제로 되는지를 자동으로 증명하는 테스트가 있어야 한다.** Phase 0 종료 시점에 이것이 0개였고, 그래서 "동작한다"를
매번 사람이 손으로 확인했다 — 프로토타입에서 두 번(T-006·T-007) 그 확인이 늦어 사용자가 먼저 실패를 봤다.

- 위치 `backend/tests/e2e/`, 마커 `-m e2e`, 기본 pytest에서 **제외**(외부 서비스가 막히면 관계없는 변경도 빨간불이 되고, 그러면 실패를 무시하기 시작한다).
- Phase 종료 루틴에서 **수동으로 한 번 돌리고** 출력을 실측기록에 남긴다.
- 한 Phase는 그 Phase가 완성한 흐름을 한 줄로 검증하는 E2E를 최소 1개 남긴다. 예: P1 = 채널 URL → 목록 N건, P2 = 영상 → 스크립트 저장, P3 = 복사 텍스트 조립 → 요약 저장.

## 4. Phase 내부 작업 순서

건너뛰거나 역순으로 진행하지 않는다. **Phase 당 문서는 3개다.**

| 순서 | 산출물 | 담는 것 |
|---|---|---|
| 1 | `docs/P{N}_설계서_<Topic>.md` | 목적·배경·범위(In/Out) · **요구사항 FR** · 모듈별 인터페이스와 **설계 판단**(왜 + 기각 대안) · 비기능 · 구현 순서 · **완료 기준 체크박스** · 다음 Phase 인계 |
| 2 | 코드 + 테스트 | 3절 등급 기준. 모듈 docstring 첫 줄: `<역할> — 대응: docs/P{N}_설계서_*.md N절 (FR-x~y). 등급 A\|B` |
| 3 | `docs/internal/P{N}_실측기록_<Topic>.md` | 실행 환경 · (해당 시)착수 전 실측 · **실호출 출력** · 완료 기준 대조 · 재작업·발견 · 남은 위험 · 인계 · **재현 명령** |

보조로 `docs/internal/P{N}_학습가이드_<Topic>.md`(사용자 이해용, 1절 6단계)를 쓴다.
템플릿은 `docs/internal/templates/`. 요구사항–설계–코드–실측이 서로 추적 가능해야 한다(문서에서 코드 경로를, 코드 docstring에서 문서 절을).
FR 번호대: P0 = FR-1~99, P1 = FR-101~199, P2 = FR-201~299 …

### 리뷰·수정 반영은 5.1절 절차로 한다

리뷰 지적, 개선 사항, 판단 변경을 반영할 때 **찾아 바꾸기로 끝내지 않는다.** 단일 출처 규칙(5절)을 지키면 고칠 곳은 보통 1~2곳이고,
그 1~2곳을 확실히 찾는 방법이 5.1절이다. `scripts/verify_docs.py`는 "이 문장대로 하면 실제로 되는가"(명령·경로·링크·표)를 보고,
"두 문장이 서로 반대말을 하는가"는 보지 못한다 — 그래서 값을 두 곳에 두지 않는 것이 유일한 해법이다.

## 5. 단일 출처 규칙 (하드코딩 금지의 확장)

**같은 사실을 두 곳에 적지 않는다. 한 곳에 적고 나머지는 링크한다.**

| 사실 종류 | 단일 출처 | 다른 문서·코드는 |
|---|---|---|
| 실행마다 조절하는 값 (모델·스레드·VAD·포맷·간격·재시도·페이지 규칙) | `backend/config/*.json` (파일마다 `"_comment"`로 근거) | 파일명만 언급, 값 복사 금지 |
| 환경에 따라 달라지는 값 (경로·포트·CORS·토큰 위치) | `.env.example` → `config.Settings` | 키 이름만 언급 |
| 설계상 고정된 값 (열거형·`-orig` 접미사·버전·DB 파일명) | `constants.py` | 상수 이름으로 참조 |
| 실측값 (속도·건수·용량·소요 시간·실제 출력) | `docs/internal/P{N}_실측기록_*.md` | 절 번호로 링크 |
| 작업 규칙 | 이 문서 | 절 번호로 링크 |
| 기능 범위·완료 판정 기준 | `docs/scope-definition.md` | 절 번호로 링크 |
| 모듈 구조·경계·배포 구성 | `docs/설계서_Architecture.md` | 절 번호로 링크 |
| 용어 정의 | `docs/internal/용어집.md` | 용어만 언급 |
| 장애 이력·증상 | `docs/internal/검토서_트러블슈팅.md` | `T-0NN` 번호로 링크 |

- **예외는 이 문서 0절 하나다.** 매 세션 로드되는 요약이라 값을 함께 둔다. 어긋나면 출처가 맞다.
- 값을 두 곳에 적어야 한다고 판단되면 **왜 그래야 하는지를 그 자리에 쓴다.** 쓸 수 없으면 링크로 바꾼다.
- **재현성 관련 값은 반드시 고정한다.** 정규화 규칙·모델·파이프라인 버전은 스크립트 레코드에 **동반 저장**한다. 동일 원본 + 동일 버전 → 동일 결과.

### 5.1 사실을 바꿀 때의 절차

```bash
grep -rn "<옛 값>" CLAUDE.md README.md docs backend/config backend/src frontend/src
```

걸린 줄을 전부 열어 **이력인지 현재 서술인지** 가른다. 이력(정정 이력·개정 사유·`T-0NN` 기록·일자 붙은 실측)은 고치지 않는다.
현재 서술이 2곳 이상이면 그중 하나를 링크로 바꾼다 — 그것이 단일 출처 규칙을 지키는 방법이다.

> **왜 에이전트를 쓰지 않나.** v1에서는 `doc-consistency` 서브에이전트가 이 일을 했다. 두 번 돌려 31건을 찾았는데
> 대부분이 "우리 문서끼리 불일치"였고, 그 불일치는 중복이 만든 것이었다. 회당 20만 토큰을 쓰고 1회차에 2건을 놓쳤다.
> 중복을 없애면 검사할 것이 거의 없다. 남는 일은 위 `grep` 한 줄로 충분하다.

## 6. Workflow 친화 구성

향후 워크플로 도구(Airflow류) 이식을 대비해 각 단계를 독립적으로 구성한다(`설계서_Architecture` 6절).

- **독립성**: 단계마다 별도 CLI 진입점(`cli/run_*.py`). 단계 간 연동은 **DB·파일로만**.
- **명시적 trigger/input/output**: docstring에 `Trigger / Input / Output / ⚠️ 사전 조건`. 입력은 명시적 인자로만.
- **모니터링·재시작**: `status/<stage>_<run_id>.json`(started/succeeded/failed). 실패 시 그 단계·그 영상만 재실행.
- **멱등성 (Phase 1~ 필수)**: 같은 입력으로 다시 실행해도 산출물과 외부 상태가 같아야 한다. 자연키 upsert, 스크립트는 (video, source, language, model, pipeline_version) 존재 시 건너뜀.
  → 왜 필수인가: 파이프라인은 중간에 끊기고 다시 돌아가는 것이 정상 운영이다(429·차단·CPU 시간).
- **실패는 상태로 남긴다** — 500 으로 던지지 않는다. 화면이 사유를 보여야 한다(T-006 의 교훈).
- **입출력 보존**: `captions/*.json3`·`whisper/*.json` 원본은 덮어쓰지 않는다(코드가 거부). 방향은 `원본 → DB 세그먼트 → 전체 텍스트 → [분석]` 한쪽. `audio/*.m4a`만 삭제 가능 캐시.

## 7. 배포·자원

- **1차 배포 경로는 Windows 설치파일**(P4): PyInstaller **onedir** 백엔드를 Tauri v2 사이드카로 동봉, NSIS. 개발 실행 경로는 `backend\.venv` 직접 실행.
- Docker는 서버 배포용 **선택지**(보류 결정 6). `.env`로 설정 주입, 호스트 경로 하드코딩 금지, `DATA_DIR` 볼륨.
- 의존성은 `backend/pyproject.toml`에 하한·상한 고정. yt-dlp는 YouTube 변경이 잦아 예외적으로 설정에서 갱신 가능하게 둔다.
- **자원 제약**: 개발 VM은 물리 코어 1개. 메모리·디스크·**프로세스 기동 비용**이 큰 값은 설정으로 빼고 기본값을 작게 잡는다.
  → 요청마다 외부 프로세스를 띄우는 설계는 1코어에서 타임아웃한다(T-007). 상주 서버를 쓴다.
- **로컬 디스크는 D: 우선** (사용자 규칙 2026-09-14). 저장소·venv·`node_modules`·`DATA_DIR`·도구(`tools/`)·pip/npm 캐시(`D:\claude\.cache\`)를 D: 에 둔다. C: 는 OS 전용.
  새 도구를 도입할 때는 **저장 위치를 먼저 D: 로 지정한 뒤 실행**한다. `~`(홈 디렉토리) 기준 기본 경로를 코드·문서에 쓰지 않는다(T-002·T-004).
- **이식성**: 개발 Windows Server / 사용자 Windows 10·11 / (P6) 서버는 Linux 가능. OS 패키지 직접 의존을 피한다.

## 8. YouTube 연동 규칙

### 작업 전 확인 (필수)

`.\scripts\check_env.ps1` → `==> READY`. PO 토큰 수단이 없으면 자막이 조용히 빠질 수 있어 "코드 문제"로 오진한다.

### 실제 호출로 검증한다

라이브러리 README만으로 API 동작을 단정하지 않는다. **실제로 호출해 응답을 확인**하고, 확인한 사실과 **확인 일자·yt-dlp 버전**을 실측기록에 남긴다.
모킹 테스트만으로는 완료가 아니다. **사용자가 쓰는 포트·프로세스에서 확인한다** — 다른 인스턴스에서만 검증해 실패를 놓친 적이 있다(T-006).

### 실측으로 확정된 규칙

| 규칙 | 근거 |
|---|---|
| 목록은 **탭 URL**(`/videos`, `/shorts`)로 flat 추출. 플레이리스트 URL은 쓰지 않는다 | 숏츠 플레이리스트 100개 상한; 탭 실측 |
| flat 결과를 믿지 않는 필드: `duration`(숏폼 없음), `upload_date`(둘 다 없음), `playlist_count`(없음), **`title`(잘림)** → 영상별 메타 보충이 정본 | `P0_실측기록` 4절, `검토서_Prototype` |
| 자막은 **원어 트랙만**: `subtitles[<lang>]` → `automatic_captions[<lang>-orig]`. 다른 언어는 번역 요청이 되어 **429** | `P0_실측기록` 4절 |
| 언어는 **한 번에 하나씩** 요청한다. yt-dlp는 한 언어 실패로 명령 전체를 실패시킨다 | 같은 절 |
| 오디오는 `bestaudio[ext=m4a]/bestaudio`, 후처리 없음. ffmpeg를 요구하는 옵션을 넣지 않는다 | 같은 절 |
| PO 토큰은 **상주 HTTP 서버**(`127.0.0.1:4416`)로 받는다. script 모드(요청마다 Node 기동)는 1코어에서 15초 제한을 넘는다 | T-007 |
| 네트워크 작업 **워커 1개**, 요청 간 1~3초 지터, 429는 지수 백오프 후 재시도, 상한 후 `failed` | `docs/scope-definition.md` 5.4절 |
| yt-dlp 인스턴스는 **워커 수명과 함께 재사용**한다. 매번 새로 만들면 플러그인 가용성 검사를 매번 치른다 | T-006·T-007 |
| yt-dlp API 호출은 `youtube/`·`transcripts/providers.py`·`stt/audio_fetcher.py` **세 곳으로 한정** | 옵션 변경 파급 차단 |
| 차단(`Sign in to confirm you're not a bot`)이 나오면 코드를 고치기 전에 **회선·간격·제공자 상태**를 먼저 확인하고 트러블슈팅에 기록 | 원인 오진 방지 |

## 9. 문서 파일명 규칙

```
[P<phase>_]<DocType>_<Topic>.md
```

- **`P<phase>`**: 특정 Phase(0~6)에 종속된 문서에만 붙인다. 전체를 다루는 문서는 생략.
- **`<DocType>`**: 아래 4개 중 하나로 고정.

  | DocType | 의미 | 위치 | 4절 순서 |
  |---|---|---|---|
  | `설계서` | 목적·범위·요구사항(FR)·설계 판단·완료 기준 | `docs/` | 1 |
  | `실측기록` | 실행 환경·실호출 출력·완료 기준 대조·재작업·인계·재현 명령 | `docs/internal/` | 3 |
  | `학습가이드` | 사용자 숙지·체화용 (실습·예상 질문) | `docs/internal/` | 보조 |
  | `검토서` | 정규 순서 밖의 조사 — 트러블슈팅, 프로토타입, 사고 분석 | `docs/internal/` | 보조 |

- **`<Topic>`**: 다루는 대상. 코드 모듈·패키지명과 맞춘다(`Common`, `ChannelListing`, `Transcripts`).
- 문서 개정은 **제자리 개정 + 머리에 개정 사유**. 전면 재작성이라 이전 판을 나란히 둘 가치가 있을 때만 새 파일.
- **예외**: `docs/scope-definition.md`·`docs/설계서_Architecture.md`(전체 문서), 각 디렉토리의 `README.md`, `docs/internal/용어집.md`(공용 참조), `docs/internal/qa/[P{N}_]질의응답_<주제>.md`(사용자 문답 기록).
- **`docs/` = 제출물, `docs/internal/` = 내부 자료.** 설계서·scope-definition·설계서_Architecture는 제출물. 실측기록·학습가이드·검토서·용어집·템플릿은 내부.
- 모든 문서는 `#` 제목 아래 **머리말 불릿 메타 블록**(상위 문서·절번호, 규칙, 작성일/작성 LLM, 상태·결과·결론)을 둔다.

## 10. 요구사항–산출물 페어링

채팅으로 작업이 진행되므로 대화 중 생성되는 요구사항을 반드시 파일로 남긴다.

- **사용자 요청 원문과 결정은 `docs/internal/qa/[P{N}_]질의응답_<주제>.md` 에 보존한다.** 질문·답·결정을 그대로 옮긴다.
- **작업 프롬프트 파일은 만들지 않는다** (v2 개정, 사용자 확인: "내가 요청한 내용만 적혀있으면 되지 않을까?").
  LLM에게 주는 지시는 곧 설계서가 되므로 두 번 쓸 이유가 없다. 구 docs/prompts/ 디렉토리는 삭제했고, 요청 원문은 위 `qa/` 로 옮겼다(원본은 git 이력).
- 요구사항이 갱신되면 대응 산출물도 같이 갱신해 **"요구사항 최신본 ↔ 산출물 최신본"이 한 쌍**을 이루게 한다.
- 판단이 바뀐 경우 이전 기록을 지우지 않고 **정정 이력으로 남긴다**(왜 바뀌었는지가 중요).
- 트러블을 해결한 직후에는 `.claude/skills/troubleshoot/SKILL.md`에 따라 `docs/internal/검토서_트러블슈팅.md`에 기록한다.
  **사용자가 볼 증상**이면 `docs/internal/학습가이드_문제해결.md` 에도 한 줄 추가한다.

## 11. Git / 협업 규칙

- **`main`에 직접 작업하지 않는다.** Phase당 브랜치 하나(**`impl-phase{N}`**)를 `main`에서 분기. 방법론·도구 변경은 `chore/<주제>` 브랜치.
- **커밋하면 즉시 push한다**(사용자 규칙 2026-09-14). 로컬에만 있는 커밋을 두지 않는다.
- **Phase 브랜치는 병합 후에도 삭제하지 않는다.** 병합 커밋은 결과만, 브랜치는 과정을 보여준다.
- **PR은 올리지 않는다**(혼자 진행). 품질 확인은 1절 7단계(Direct 리뷰)로 한다. 병합은 `git merge --no-ff <브랜치>` → push.
- 커밋 메시지: `<type>(<scope>): <요약>` (type = feat|fix|docs|test|chore|refactor). 본문에 무엇이 왜 바뀌었는지.
- 세션 단위 작업 히스토리를 `history/<날짜>_<작업자>_<주제>.md`로 남긴다(작업자 표기 `park.sei`). 히스토리는 **사후에 고치지 않는다**.
- **작업 시작 전 `git status` 를 확인한다** — 다른 세션이 남긴 미커밋 변경을 발견한 적이 있다(2026-09-15).
- **커밋 금지**: `.env`, 토큰·API 키, `data/`(DB·자막 원본·오디오·모델), `status/`, `node_modules/`, `tools/`, 빌드 산출물. 자막·오디오는 저작물이라 저장소에 올리지 않는다 — 테스트 fixture는 자작 최소 샘플만.
- 원격: `https://github.com/hipiboy7/youtube-Learner.git` (`origin`).

## 12. 데이터 규칙

| 항목 | 기준 |
|---|---|
| 기록 원본 | **SQLite 한 파일**(`DATA_DIR/youtube_learner.db`), WAL, `busy_timeout`, 외래키 ON. 화면·API는 DB만 읽는다 |
| 파일 산출물 | `data/channels/<yt_channel_id>/{captions,audio,whisper}/`. 원본(json3·Whisper 원출력)은 읽기만, 덮어쓰기 거부 |
| 자연키 | `yt_channel_id`, `yt_video_id`. 스크립트 유일성 (video, source, language, model_name, pipeline_version) |
| 버전 동반 | 스크립트 레코드에 `source`·`engine`·`model_name`·`pipeline_version` 필수. 규칙 변경 시 재생성 대상을 이 값으로 고른다 |
| 언어 | 트랙 키 `ko-orig`는 저장 시 `ko` + `source=auto`. 번역 트랙은 옵션, `source=translated` |
| 파싱 검증 | json3 파싱 직후 세그먼트 수·시간 단조 증가·빈 텍스트 0건 확인 후 저장 |
| 인코딩·개행 | UTF-8(BOM 없음), LF. Windows에서도 `newline="\n"` 명시. **단 `.ps1` 은 UTF-8 BOM**(T-005) |
| **필드명(키)** | **영문 ASCII만.** 값은 원문(한국어) 그대로 |
| 재현성 | 동일 원본 + 동일 `pipeline_version` → DB 세그먼트·전체 텍스트 바이트 단위 동일 |
| 원문 보존 | 정규화는 DB에만. 원본 파일은 변형하지 않는다 |
| 삭제 가능 | `audio/*.m4a`만. 삭제 후에도 DB·원출력만으로 화면이 완전해야 한다 |
