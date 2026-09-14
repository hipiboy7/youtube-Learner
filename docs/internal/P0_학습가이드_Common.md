# P0 학습가이드 — Common

- 독자: 컴퓨터공학 학부 졸업 수준, 이 프로젝트를 처음 보는 사람 (`docs/internal/용어집.md` 기준)
- 작성일: 2026-09-14 / 작성 LLM: Fable 5.1
- 규칙: `CLAUDE.md` 1절 7단계. 내부 자료(9절 경계). 실습은 **사본 디렉토리**에서만 — 실제 `data/`·DB 를 건드리지 않는다
- 대응 산출물: `docs/P0_요구사항정의서_Common.md`, `docs/P0_설계서_Common.md`, `docs/P0_테스트결과서_Common.md`

> 목적은 담당자가 Phase 0 산출물을 **스스로 재현하고 설명**할 수 있게 하는 것이다. 코드를 다시 설명하는 문서가 아니다 —
> "무엇을 왜 그렇게 만들었나"와 "직접 확인하는 방법"이 중심이다.

## 0. 시작 전 확인 (매번)

```powershell
.\scripts\check_env.ps1        # ==> READY 가 나와야 한다
```

READY 가 아니면 `[FAIL]` 줄이 무엇이 빠졌는지 말해준다. `[WARN]` 두 개(디스크 여유·모델 캐시)는 작업을 막지 않는다.

## 0.5 먼저 알아야 할 것 10가지

| # | 용어 | 한 줄 | 용어집 |
|---|---|---|---|
| ① | Phase / 4단계 | 요구사항정의서 → 설계서 → 코드+테스트 → 테스트결과서. 건너뛰지 않는다 | 6절 |
| ② | TechSpike | 프롬프트 쓰기 **전에** 외부 동작을 실제로 호출해 본 기록. P0 에서 7건이 문서와 달랐다 | 6절 |
| ③ | 등급 A/B/C | 순수 로직(테스트 먼저, ≥90%) / 오케스트레이션(≥70%) / 실측 스크립트 | 6절 |
| ④ | 값의 3분류 | `.env`(환경별) / `constants.py`(설계 고정) / `backend/config/*.json`(실행별) | — |
| ⑤ | Protocol / DIP | 상속 없는 구조적 인터페이스. 구현 교체가 조립 지점 한 곳에서 끝난다 | 6절 |
| ⑥ | 분석 슬롯 | 요약 기능을 나중에 끼울 자리. v1 은 `NullAnalyzer` 만 | 6절 |
| ⑦ | 원어 트랙 `-orig` | 자동자막 중 번역되지 않은 원본. 다른 언어를 요청하면 429 | 2절 |
| ⑧ | 멱등성 / status 파일 | 다시 돌려도 결과가 같다. 실행마다 `status/<stage>_<run_id>.json` | 5절 |
| ⑨ | verify_docs | 문서 속 명령·경로·링크·표를 기계로 검사. pytest 에 포함 | 6절 |
| ⑩ | 보류 결정 | 지금 안 정한 것을 트리거·판정법·이정표와 함께 `CLAUDE.md` 1절 표에 등재 | 6절 |

## 1. 이 Phase 가 한 일 — 한 장 요약

```
기획서(승인) ──▶ TechSpike(실측 7건) ──▶ 작업 프롬프트 v1
                                             │
              ┌──────────────────────────────┴──────────────────────────────┐
              ▼                                                             ▼
   상위 문서 3종 (scope · Architecture · CLAUDE.md)              방법론 도구 (템플릿 6 · 에이전트 · 스킬 · 용어집 · 트러블슈팅)
              │
              ▼
   P0 요구사항정의서 (FR-1~34) ──▶ P0 설계서 ──▶ 코드+테스트 ──▶ P0 테스트결과서
                                                  │
              constants · exceptions · domain(models, interfaces) · config · logging_config
              workflow/run_context · repository/db · analysis(null, registry) · cli/check_env
              scripts/check_env.ps1 · scripts/verify_docs.py · frontend/(scaffold + formatTimestamp)
```

Phase 0 는 **사용자 기능을 만들지 않았다.** 대신 Phase 1~6 이 공통으로 딛는 바닥(설정·모델·인터페이스·기록·예외·로깅·DB 엔진·분석 슬롯)과, 방법론을 기계로 강제하는 도구(`check_env`·`verify_docs`·테스트 등급·커버리지)를 만들었다.

## 2. 직접 실행해 보기

### 2.1 실습 사본 만들기

실습은 `DATA_DIR`·`STATUS_DIR` 을 임시 폴더로 돌려서 한다. 저장소의 `data/`·`status/` 는 건드리지 않는다.

```powershell
$lab = Join-Path $env:TEMP "ytl-lab"; New-Item -ItemType Directory -Force $lab | Out-Null
$env:DATA_DIR = "$lab\data"; $env:STATUS_DIR = "$lab\status"; $env:PYTHONUTF8 = "1"
```

### 2.2 설정이 어디서 오는지 보기

```powershell
backend\.venv\Scripts\python.exe -c "from youtube_learner.config import get_settings; s=get_settings(); print(s.data_dir); print(s.models_dir); print(s.db_path); print(s.resolved_config_dir)"
```

기대: 네 줄이 전부 **절대경로**이고, `models_dir` 이 `DATA_DIR\models` 다(HF_HOME 미설정). `HF_HOME` 환경변수를 주고 다시 실행하면 세 번째 줄만 바뀐다 — 이것이 "환경별 값은 `.env`" 의 뜻이다.

### 2.3 잘못된 값이 어디서 거부되는지 보기

```powershell
$env:API_PORT = "70000"; backend\.venv\Scripts\python.exe -c "from youtube_learner.config import get_settings; get_settings()"
Remove-Item Env:API_PORT
```

기대: pydantic `ValidationError` — `api_port` "less than or equal to 65535". 설정은 **읽는 순간** 거부된다(FR-4). 잘못된 포트로 서버가 뜬 뒤에 실패하는 것과의 차이를 생각해 본다.

### 2.4 실행 기록(run_context) — 성공과 실패

```powershell
backend\.venv\Scripts\python.exe -c "from youtube_learner.config import get_settings; from youtube_learner.workflow.run_context import run_context
s=get_settings()
with run_context('lab_ok', s, extra={'note':'실습'}) as (rid, log): log.info('안에서 한 줄')
try:
    with run_context('lab_fail', s) as (rid2, log): raise RuntimeError('의도한 실패')
except RuntimeError: pass
print('done')"
Get-ChildItem $env:STATUS_DIR | Select-Object Name
Get-Content (Get-ChildItem $env:STATUS_DIR -Filter 'lab_fail_*.json').FullName
```

기대: stdout 에 JSON 한 줄 로그(`run_id`·`stage` 포함), `status\` 에 파일 2개. `lab_fail_*.json` 의 `status` 가 `failed`, `error.type` 이 `RuntimeError`. 예외는 컨텍스트 매니저가 삼키지 않고 **재전파**했다(그래서 `try/except` 가 필요했다).

### 2.5 멱등성 — 같은 run_id 로 두 번

```powershell
backend\.venv\Scripts\python.exe -c "from youtube_learner.config import get_settings; from youtube_learner.workflow.run_context import run_context
s=get_settings()
with run_context('lab_dup', s, run_id='20260914-000000-deadbeef'): pass
with run_context('lab_dup', s, run_id='20260914-000000-deadbeef'): pass"
```

기대: 두 번째에서 `OutputExistsError: 산출물이 이미 있어 덮어쓰지 않는다: …lab_dup_20260914-000000-deadbeef.json`. 이것이 `CLAUDE.md` 6절 "입출력 보존"이 코드로 강제된 모습이다.

### 2.6 분석 슬롯이 "비어 있음"을 어떻게 말하는지

```powershell
backend\.venv\Scripts\python.exe -c "from youtube_learner.config import get_settings; from youtube_learner.analysis.registry import build_registry
r=build_registry(get_settings()); print('available =', r.available())
try: r.get('summary')
except Exception as e: print(type(e).__name__, '| available =', e.available)"
```

기대: `available = []`, 그리고 `AnalyzerNotConfiguredError | available = ()`. API(P1)는 이 예외를 501 로 바꾼다. `.env` 에 `ANALYZERS=ollama` 를 넣고 다시 실행하면 `ConfigError` 가 **기동 시점에** 난다 — 조용히 무시하지 않는다.

### 2.7 문서 검사기를 속여 보기

```powershell
Set-Content -Encoding utf8 "$lab\bad.md" "# 예`n`n``````powershell`npython -m pytest`n``````n"
backend\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'scripts'); import verify_docs, pathlib; [print(f) for f in verify_docs.verify(pathlib.Path(r'$env:TEMP\ytl-lab\bad.md'))]"
```

기대: `[venv]` 위반 — bare `python` 을 쓰는데 활성화 안내가 없다. `python` 을 `backend\.venv\Scripts\python.exe` 로 바꿔 다시 실행하면 출력이 없다.

### 2.8 실습 정리

```powershell
Remove-Item Env:DATA_DIR; Remove-Item Env:STATUS_DIR
Remove-Item -Recurse -Force $lab
```

## 3. 설계 결정 8개 — 리뷰에서 설명할 것

| # | 결정 | 기각한 대안 | 왜 | 어디에 적혀 있나 |
|---|---|---|---|---|
| 1 | 모노레포 `backend/ frontend/ desktop/ mobile/` | Python 단일 패키지(참조 그대로) | 프론트가 있고 3 플랫폼으로 확장. 도구 경계를 디렉토리로 | 기획서 1.2절, `설계서_Architecture` 10절 |
| 2 | 도메인 모델은 pydantic **frozen** | dataclass | 경계에서 거부 + 불변 + P1 API 스키마 재사용 | `P0_설계서_Common` 4.2절 |
| 3 | 인터페이스는 `typing.Protocol` | ABC | 상속 없는 구조적 타이핑, 의존 방향 한쪽, fake 작성 쉬움 | 5.2절 |
| 4 | `HF_HOME` 기본을 `DATA_DIR/models` | HF 기본(C: 사용자 프로필) | C: 여유 최소, Windows 심볼릭 링크 미지원으로 공간 2배 (T-002) | 3.2절 |
| 5 | JSON 로거 직접 구현 | python-json-logger | 필드 5개에 의존성 추가 불필요, 번들 크기 | 6.2절 |
| 6 | `NullAnalyzer` (Null 객체) | `analyzer: Analyzer \| None` | `if None` 분기가 API·화면·작업에 퍼지는 것을 막고, 501 매핑을 한 곳에 | 9.2절 |
| 7 | `check_env` 로직은 Python, `.ps1` 은 래퍼 | PowerShell 에 검사 구현 | pytest 로 검증 가능. `.ps1` 은 "venv python 찾기" 하나만 | 10.2절 |
| 8 | `verify_docs` 는 접두사 있는 경로만 검사 | 슬래시+확장자 전부 | 패키지 상대 표기(`domain/models.py`)는 의도가 여럿 → 오탐. 참조가 11건 오탐으로 확인한 규칙 | 11.2절 |

## 4. 실제가 문서와 다르게 동작한 것들

| # | 문서/예상 | 실제 | 우리가 한 일 |
|---|---|---|---|
| 1 | 자막 언어 우선순위 `ko→en` 로 요청 | 원어 외 언어는 번역 요청 → **429**, 한 언어 실패로 명령 전체 실패 | 원어 트랙(`-orig`)만, 언어별 개별 요청, 429 백오프 규칙(`CLAUDE.md` 8절) |
| 2 | flat 목록에 길이·업로드일 | 숏폼 `duration` 없음, 둘 다 `upload_date` 없음 | `VideoStub`(flat) / `Video`(보충) 분리, P1 메타 보충 단계 |
| 3 | bgutil 은 pip 설치로 동작 | Node 서버 디렉토리 빌드 필요 | `check_env` 검사 항목, `.env` `BGUTIL_SCRIPT_PATH`, T-001 |
| 4 | CPU Whisper 는 실시간보다 느릴 것 | small 3.05x (turbo 0.86x) | 기본 small, 보류 결정 2 |
| 5 | pyproject `readme = "../README.md"` | setuptools 가 프로젝트 밖 파일 거부 | readme 줄 제거 |
| 6 | 검사기가 전체 경로 명령을 인식 | `…\python.exe` 로 시작하는 줄을 명령으로 안 봄 | 역테스트가 잡음 → `.exe` 접미 처리 |
| 7 | HF 캐시는 심볼릭 링크로 절약 | Windows 에서 복사 → 공간 2배, C: 2.4GB 까지 하락 | 캐시 위치 지정·이동, T-002 |

## 5. 자체 점검에서 찾은 내 실수

`docs/internal/P0_검토서_SelfReview.md` 1절. 요약: 설계서 시그니처와 구현이 어긋난 곳 2건(`run_context(run_id=)`, `make_engine` 의 디렉토리 생성)은 **구현이 맞고 문서가 뒤처진** 경우였다 — 코드를 고치며 문서를 같이 고치지 않으면 생기는 전형. 구조적 원인: 설계서를 쓴 뒤 테스트를 쓰다가 필요(결정적 run_id)가 드러났고, 그 자리에서 설계서로 돌아가지 않았다.

## 6. 리뷰에서 나올 수 있는 질문과 답

**Q. 요약 기능이 v1 에 없는데 왜 `analysis/` 패키지가 있나?**
A. 나중에 붙일 자리를 지금 만들어 두지 않으면 P5 에서 API·화면·DB 를 다시 설계해야 한다. `Analyzer` Protocol·레지스트리·(P1)`analyses` 테이블·(P1)501 API·(P3)화면 탭이 슬롯이다. 완료 기준은 "P5 에서 `analysis/` 밖은 설정 한 줄만 바뀐다" — `scope-definition.md` 2.4절.

**Q. 왜 롱/숏을 길이로 판정하지 않나?**
A. 롱폼 탭에 42초 영상이 실재하고 숏폼은 최대 3분이다(TechSpike 3.1절). 탭 소속이 유튜브의 정의다. 보류 결정 3 은 이 실측으로 종료했다.

**Q. `check_env` 가 READY 인데 YouTube 가 막혀 있으면?**
A. `check_env` 는 네트워크를 호출하지 않는다 — READY 가 YouTube 상태에 흔들리면 무관한 작업이 막힌다. 차단 감지는 P2 작업 실패 카운트의 일이다(요구사항 8절 리스크 4).

**Q. 커버리지 A ≥ 90% 인데 `verify_docs.py` 는 왜 85% 였나?**
A. `main()` 이 subprocess 로만 실행되어 측정되지 않았고, 따옴표 주석 처리 분기가 테스트되지 않았다. 인프로세스 테스트 3개를 추가했다 — 실측은 테스트결과서 3절.

**Q. 왜 `python-json-logger` 를 빼고 직접 짰나? 의존성을 줄이는 게 항상 옳은가?**
A. 항상은 아니다. 여기서는 필요한 기능이 30줄이고, 외부 패키지의 API 변경·PyInstaller 번들 크기가 이득보다 컸다. 반대 사례: pydantic-settings 는 직접 짜면 검증이 흩어져서 채택했다(설계서 3.2절).

**Q. 테스트가 216건인데 정상 케이스만 많은 건 아닌가?**
A. 등급 A 모듈은 **거부 케이스가 필수**다(`CLAUDE.md` 3절). `test_domain_models.py` 45건 중 절반 이상이 거부(패턴 위반·빈 제목·시간 역행·idx 불연속·frozen 변경·extra 필드)다. 정상만 테스트하면 아무것도 거부하지 않는 모델도 통과한다.

## 7. 읽을 문서 순서

1. `CLAUDE.md` 0절·1절 — 요약과 보류 결정 8건
2. `docs/scope-definition.md` 2절(기능)·5절(스크립트 전략)·8절(환경)
3. `docs/설계서_Architecture.md` 2절(모듈·DIP)·4절(데이터 흐름)
4. `docs/internal/P0_검토서_TechSpike.md` 3절·4절 — 실측과 "달랐던 것"
5. `docs/P0_요구사항정의서_Common.md` 4절 FR → `docs/P0_설계서_Common.md` 같은 번호 절의 "설계 판단"
6. 코드 — 모듈 docstring 첫 줄이 설계서 절과 FR 을 가리킨다. `domain/models.py` → `config.py` → `workflow/run_context.py` 순
7. `docs/P0_테스트결과서_Common.md` 3절(커버리지)·4절(FR 대조)·6절(재작업)

## 8. 다음 Phase 로 넘어갈 때 기억할 것

- `Settings.apply_process_env()` 는 **faster-whisper import 전에** 호출한다 (P2 계약, `P0_설계서_Common` 15절).
- `resource_root()` 의 frozen 분기는 P4 패키징에서 실제 검증한다.
- P1 은 `Base` 아래 첫 테이블과 Alembic 초기 리비전을 만든다. `VideoStub`/`Video` ↔ ORM 변환은 저장소 계층에.
- 보류 결정 3(탭 판정) 은 P1 전량 목록화에서 겹침 0 을 재확인한다. 보류 결정 8(디스크) 은 P4 전에 닫는다.
- P1 TechSpike 질문: 채널 전량 페이지네이션·숏폼 100+·메타 보충 속도·`curl_cffi` 효과 (TechSpike 6절 미확인 사항).
