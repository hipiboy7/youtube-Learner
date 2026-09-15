// formatTimestamp 검증 — 등급 A (테스트 먼저). 대응: docs/P0_설계서_Common.md 12절 (FR-31).
import { describe, expect, it } from "vitest";
import { formatTimestamp } from "./time";

describe("formatTimestamp", () => {
  it("0ms → 0:00", () => {
    expect(formatTimestamp(0)).toBe("0:00");
  });

  it("65000ms → 1:05 (한 시간 미만은 m:ss)", () => {
    expect(formatTimestamp(65_000)).toBe("1:05");
  });

  it("3_600_000ms → 1:00:00 (한 시간 이상은 h:mm:ss)", () => {
    expect(formatTimestamp(3_600_000)).toBe("1:00:00");
  });

  it("3_661_000ms → 1:01:01", () => {
    expect(formatTimestamp(3_661_000)).toBe("1:01:01");
  });

  it("밀리초는 반올림하지 않고 내림한다 (59999 → 0:59)", () => {
    expect(formatTimestamp(59_999)).toBe("0:59");
  });

  it("세그먼트 실측값: 986441ms → 16:26", () => {
    expect(formatTimestamp(986_441)).toBe("16:26");
  });

  it.each([-1, Number.NaN, Number.POSITIVE_INFINITY])("거부: %p", (bad) => {
    expect(() => formatTimestamp(bad)).toThrow(RangeError);
  });
});
