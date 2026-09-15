"""proto — Phase 1 착수 전 사용자 확인용 end-to-end 프로토타입. 등급 C (테스트 미강제, 산출물 검증).

채널 URL → 롱폼·숏폼 목록 → 스크립트(원어 자막 → 폴백 → Whisper) → 화면(원클릭 복사·'요약 및 정리' 저장) 한 줄을
가장 얇게 이어 본다. Phase 1~3 의 모듈 경계(youtube/·transcripts/·stt/·api/)를 선점하지 않도록 이 패키지 안에 격리한다.
대응: docs/internal/검토서_Prototype.md. 브랜치 prototype/e2e-slice 밖(main)으로 병합하지 않는다.
"""
