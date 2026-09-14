// API base URL — 대응: docs/P0_설계서_Common.md 12절 (FR-31). 등급 B.
// 데스크톱(P4)은 localhost 사이드카, 모바일(P6)은 PC 서버 주소를 쓴다. 값은 빌드 시 VITE_API_BASE_URL, 이후 설정 화면(P3)에서 덮어쓴다.

export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8765";

/** 빈 값·공백은 기본값, 끝 슬래시는 제거한다. */
export function resolveApiBaseUrl(raw: string | undefined): string {
  const trimmed = (raw ?? "").trim();
  const base = trimmed === "" ? DEFAULT_API_BASE_URL : trimmed;
  return base.replace(/\/+$/, "");
}

export const API_BASE_URL: string = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL as string | undefined);
