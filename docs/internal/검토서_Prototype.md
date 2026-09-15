# 검토서 — End-to-End 프로토타입 (Phase 1 착수 전 사용자 확인용)

- 작성일: 2026-09-15 / 작성 LLM: Fable 5.1 / 브랜치: `prototype/e2e-slice` (`main` 6480b0b 에서 분기)
- 규칙: `CLAUDE.md` 9절 DocType `검토서`(정규 4단계 밖의 조사). 등급 C — 자동 테스트 미강제, 산출물(실행 결과)로 검증. 내부 자료
- 사용자 요청(원문, 2026-09-15): "phase 1 시작하기 전에 prototype을 먼저 보고 싶어. 별도 prototype 브랜치를 만들고, prototype을 네가 처음부터 끝까지 완성해서 나에게 결과물을 보여줄 수 있어?"
- 결론: **채널 입력 → 롱폼·숏폼 목록 → 스크립트(원어 자막 → 폴백 → Whisper) → 화면(원클릭 복사) → '요약 및 정리' 저장** 한 줄이 이 VM 에서 실제로 동작한다(3절 실측). 이 브랜치는 `main` 에 병합하지 않고 참고용으로 남긴다. Phase 1~3 에 넘길 교훈은 5절.

## 1. 무엇을 만들었나

scope-definition v2 의 v1 기능을 **가장 얇게** 이었다. 정식 모듈 경계(`youtube/`·`transcripts/`·`stt/`·`api/`)를 선점하지 않도록 `backend/src/youtube_learner/proto/` 한 패키지에 격리했고, Phase 0 공통 모듈(설정·상수·도메인 모델·DB 엔진·로깅)은 그대로 썼다.

| 구성 | 파일 | 하는 일 |
|---|---|---|
| yt-dlp 접근 | `proto/yt.py` | 탭 flat 목록, 영상 메타(원어·자막 트랙), 원어 자막 json3 다운로드·파싱, bestaudio m4a, youtube-transcript-api 폴백. **인스턴스 재사용 + 네트워크 락** |
| Whisper | `proto/stt.py` | `stt_default.json` 대로 faster-whisper(small, int8, VAD) 전사, 진행률 콜백 |
| 저장 | `proto/store.py` | SQLite `proto_channels`·`proto_videos`(세그먼트 JSON)·`proto_summaries`(수동 요약) |
| API | `proto/app.py` | FastAPI: 채널 동기화, 목록, 스크립트(자막 즉시 / Whisper 백그라운드 1스레드), 요약 GET/PUT, `GET /analyzers` → `[]` |
| 화면 | `frontend/src/App.tsx` | 채널 입력·동기화, 롱폼/숏폼 탭, 영상 목록(썸네일·상태), 세그먼트 뷰어(타임스탬프 → 유튜브 위치), **📋 스크립트 복사**(타임스탬프 포함 옵션), **요약 및 정리** 편집기 + 💾 저장, Whisper 진행률 |
| 실행 | `scripts/dev_proto.ps1` | 백엔드(:8765)·프론트(:5173) 두 창 |

## 2. 실행 방법

```powershell
.\scripts\check_env.ps1              # ==> READY
.\scripts\dev_proto.ps1              # 백엔드 + 프론트 각각 새 창
```

브라우저에서 `http://localhost:5173`. 채널 입력란에 기본으로 `https://www.youtube.com/@sebasi15` 가 들어 있다 — "채널 추가·동기화" → 왼쪽 목록에서 영상 클릭 → "스크립트 가져오기" → "📋 스크립트 복사" → 외부 AI 챗에 붙여 요약을 받고 → "요약 및 정리"에 붙여 넣고 "💾 저장".
API 만 보려면 `http://127.0.0.1:8765/docs` (FastAPI 자동 문서). 데이터는 `data/youtube_learner.db` 와 `data/proto/{captions,audio}/` 에 남는다(git 미추적).

## 3. 실측 (2026-09-15, 이 VM — 물리 코어 1, CPU 부하 90%+ 상태에서)

### 3.1 채널 동기화 — `POST /proto/channels {"url":"https://www.youtube.com/@sebasi15","limit":12}`

```
{"id":1,"yt_channel_id":"UCgheNMc3gGHLsT-RISdCzDQ","title":"세바시 강연 Sebasi Talk","counts":{"long":12,"short":12},"added":24}
real 0m2.857s
롱폼 12 건: GYM6ikcn8jQ 1004s / L81RWsnY-vY 996s / pih8wYwLVLE 2564s …
숏폼 12 건: VG8lEPtvlGc None / O6Ntqa0jC74 None / NWvf7L-Rfu4 None …   ← 숏폼 flat 에는 duration 이 없다 (TechSpike 3.1절과 일치)
```

### 3.2 스크립트 — 자막 경로 `POST /proto/videos/L81RWsnY-vY/transcript`

```
elapsed 22s
{'transcript_status': 'done', 'transcript_source': 'auto', 'transcript_language': 'ko', 'language': 'ko', 'duration_s': 995, 'upload_date': '20260911'}
segments: 373 chars: 6814
first: [(359, '지난 명절에 한우 드렸나요? 혹시'), (3399, '그게 맛있었다라고 하면 그건 운이')]
파일: data/proto/captions/L81RWsnY-vY.ko-orig.json3 (214,913 bytes)
```

원어 트랙 `ko-orig` 만 요청했고(언어 한 번에 하나), 번역 트랙은 건드리지 않았다 — 429 없음. 22초 중 대부분은 메타 조회 + bgutil PO 토큰 생성(Node 기동)이다.

### 3.3 요약 및 정리 — `PUT` → `GET /proto/videos/L81RWsnY-vY/summary`

```
PUT: 2026-09-15T09:50:56.089961+00:00 ChatGPT
GET text: ## 핵심 요약 (프로토타입 검증용) / - 미사일을 만들던 서울대 공학자가 한우 사업으로 전환한 이유 / - 명절 ...
analyzer_name: manual
```

한글이 그대로 저장·조회된다(UTF-8). 목록에 `summary` 표시가 붙는다(3.5절).

### 3.4 스크립트 — Whisper 경로 `POST /proto/videos/O6Ntqa0jC74/transcript {"force_whisper":true}`

```
status: pending progress: 0.0 lang: ko dur: 79
  t=32s  pending 0.05      ← 오디오 1,272,877 bytes 다운로드 완료
  t=95s  pending 0.352     ← 모델 로드(≈50s, CPU 부하 상태) 후 전사 시작
  t=124s done 1.0
{'transcript_status': 'done', 'transcript_source': 'whisper', 'transcript_model': 'small', 'transcript_language': 'ko', 'duration_s': 79}
segments: 20
  0     와 이 일이 맞나? 나는 맞지 않는데 계속해서 이 일을 하고 있는 거 아닌가?
  6000  배우로서 가장 힘들었던 것 중에 하나가 도전을 해야 되고 항상 예측할 수 없는 것들이 계속 벌어지고 있다는 거죠.
  16800 매일 새로운 환경과 마주하게 되고 그 변화에 맞춰서 끊임없이 계속해서 적응을 해야 한다는 것입니다.
```

79초 오디오 → 전체 124초(다운로드 ≈25s, 모델 로드 ≈50s, 전사 ≈30s → 전사만 약 2.6x 실시간). 화면은 3초마다 진행률을 폴링해 막대로 보인다.

### 3.5 목록 상태 반영

```
  long  L81RWsnY-vY done auto     summary
  short O6Ntqa0jC74 done whisper
```

## 4. 만들면서 겪은 것 (Phase 1~3 에 넘길 사실)

| # | 발견 | 원인 | 프로토타입 조치 | Phase 반영 |
|---|---|---|---|---|
| 1 | 첫 실행에서 스크립트 요청이 500 으로 죽고 상태가 `pending` 에 걸림 | bgutil 플러그인이 **yt-dlp 인스턴스마다** `node generate_once.js --version` 을 15초 제한으로 실행하는데, CPU 97% 부하(Claude Code·Chrome·Notion 동시 실행)에서 Node 기동이 15초를 넘겼다(평시 3.3초). 예외가 `YoutubeLearnerError` 가 아니어서 잡히지 않았다 | 용도별 yt-dlp 인스턴스 재사용(`_ydl`) + 네트워크 락 → Node 검사는 프로세스당 1회. 어떤 예외든 `failed` 로 기록. 처리 중 집합(`_active`)으로 stale `pending` 재시도 허용 | **P2 설계**: yt-dlp 인스턴스 수명 = 워커 수명, 실패는 상태로(500 금지), 재시도 정책. **P0 인계**: bgutil 검사 타임아웃은 1코어에서 부족 — P4 배포 시 Node 기동 시간 실측 |
| 2 | 숏폼 flat 에 길이 없음 → 목록에 "길이 미확인" | TechSpike 3.1절 그대로 | 스크립트 요청 시 메타 보충으로 채움 | P1 메타 보충 단계가 목록 뒤에 필요하다는 것을 화면에서도 확인 |
| 3 | 자막 경로 22초 중 대부분이 메타 조회·PO 토큰 | 영상당 yt-dlp 요청 2회(메타 + 자막) | — | P2: 메타 보충(P1)이 트랙 목록을 저장해 두면 자막 요청 1회로 줄어든다 |
| 4 | curl 로 한글 JSON 을 보내면 `?` 로 깨짐 | 테스트 셸(Git Bash)의 인코딩 — 앱 문제 아님 | 파일(`--data-binary @…`)로 보내 확인 | 테스트결과서에 실호출 출력 넣을 때 인코딩 주의 |

## 5. 프로토타입이 정식이 아닌 이유 — Phase 1~3 에서 달라져야 할 것

- **저장**: 세그먼트를 JSON 문자열로 한 컬럼에 넣었다. 정식은 `transcripts`·`transcript_segments` 정규화 + 버전 동반(`pipeline_version`·`model_name`) + 원본 파일 보존 규칙(scope 4절).
- **작업**: Python 스레드 1개. 정식은 Huey 큐(재시도·재개·상태 파일 `run_context`).
- **멱등성**: 채널 동기화는 `yt_video_id` upsert 로 멱등이지만, 증분 중단 규칙·전체 재스캔·메타 보충 배치는 없다.
- **테스트**: 등급 C — 자동 테스트 없음(프론트 렌더 1건만). 정식은 A/B 등급·커버리지.
- **경계**: `youtube/`·`transcripts/`·`stt/`·`api/` 패키지와 `VideoListSource`·`TranscriptProvider`·`SttEngine` Protocol 구현으로 재배치.
- **화면**: 설정·작업 모니터·복사 형식 옵션(qa Q3)·자동 분석 자리 미구현. 정식 화면 설계는 P3 요구사항정의서에서.

## 6. 브랜치 처리

`prototype/e2e-slice` 는 **참고용으로 보존**하고 `main` 에 병합하지 않는다(코드가 정식 경계를 어기므로). Phase 1~3 프롬프트는 이 문서 4·5절을 "실측 근거"로 인용한다. 이 검토서와 `history/2026-09-15_park.sei_prototype-e2e.md` 만 필요하면 `impl-phase1` 로 cherry-pick 한다.
