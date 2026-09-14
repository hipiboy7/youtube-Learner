// API base URL 검증 — 등급 B. 대응: docs/P0_설계서_Common.md 12절 (FR-31).
import { describe, expect, it } from "vitest";
import { API_BASE_URL, DEFAULT_API_BASE_URL, resolveApiBaseUrl } from "./api";

describe("resolveApiBaseUrl", () => {
  it("미설정이면 기본값 (백엔드 기본 포트 8765)", () => {
    expect(resolveApiBaseUrl(undefined)).toBe("http://127.0.0.1:8765");
    expect(resolveApiBaseUrl("")).toBe(DEFAULT_API_BASE_URL);
    expect(resolveApiBaseUrl("   ")).toBe(DEFAULT_API_BASE_URL);
  });

  it("끝 슬래시를 제거한다", () => {
    expect(resolveApiBaseUrl("http://192.168.0.10:8765/")).toBe("http://192.168.0.10:8765");
    expect(resolveApiBaseUrl("http://pc.local:8765///")).toBe("http://pc.local:8765");
  });

  it("모듈 상수는 해석된 값이다", () => {
    expect(API_BASE_URL.endsWith("/")).toBe(false);
  });
});
