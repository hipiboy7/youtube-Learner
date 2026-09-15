// 시간 표기 유틸 — 대응: docs/P0_설계서_Common.md 12절 (FR-31). 등급 A.
// 스크립트 뷰어의 모든 세그먼트 타임스탬프에 쓰인다. 순수 함수.

/**
 * 밀리초를 `m:ss`(한 시간 미만) 또는 `h:mm:ss` 로 표기한다. 밀리초는 내림.
 * @throws RangeError 음수·NaN·무한
 */
export function formatTimestamp(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) {
    throw new RangeError(`formatTimestamp: 0 이상의 유한한 밀리초가 필요하다 (받은 값: ${ms})`);
  }
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const ss = String(seconds).padStart(2, "0");
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${ss}`;
  }
  return `${minutes}:${ss}`;
}
