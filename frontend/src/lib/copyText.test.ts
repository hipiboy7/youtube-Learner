// copyText 검증 — 등급 A. 대응: docs/internal/검토서_Prototype.md 7절.
import { describe, expect, it } from "vitest";
import { buildCopyText, buildHeader, buildTranscript, formatUploadDate } from "./copyText";

const meta = {
  title: "내신 대비는 5단계만 지키세요", channel_title: "대치동캐슬", url: "https://www.youtube.com/watch?v=YfoO5jZchPQ",
  duration_s: 826, upload_date: "20260914", transcript_source: "auto", transcript_language: "ko", transcript_model: null,
};
const segs = [{ start_ms: 0, text: "첫 문장" }, { start_ms: 65_000, text: "둘째 문장" }];
const now = new Date("2026-09-15T10:00:00Z");

describe("formatUploadDate", () => {
  it("yt-dlp 형식 YYYYMMDD → YYYY-MM-DD, 없으면 미제공", () => {
    expect(formatUploadDate("20260914")).toBe("2026-09-14");
    expect(formatUploadDate(null)).toBe("미제공");
    expect(formatUploadDate("2026-09-14")).toBe("2026-09-14");
  });
});

describe("buildHeader", () => {
  it("제목·채널·URL·길이·게시일·출처·세그먼트 수를 담는다", () => {
    const h = buildHeader(meta, 2, now);
    expect(h).toContain("# 내신 대비는 5단계만 지키세요");
    expect(h).toContain("- 채널: 대치동캐슬");
    expect(h).toContain("- 길이: 13:46 / 게시일: 2026-09-14");
    expect(h).toContain("스크립트 출처: auto / ko · 세그먼트 2개 · 복사 2026-09-15");
  });
  it("없는 값은 지어내지 않고 미제공", () => {
    const h = buildHeader({ title: "t", url: "u" }, 0, now);
    expect(h).toContain("- 채널: 미제공");
    expect(h).toContain("- 길이: 미제공 / 게시일: 미제공");
    expect(h).toContain("스크립트 출처: 미제공");
  });
});

describe("buildTranscript", () => {
  it("타임스탬프 포함이면 줄마다 [m:ss]", () => {
    expect(buildTranscript(segs, true)).toBe("[0:00] 첫 문장\n[1:05] 둘째 문장");
  });
  it("미포함이면 공백으로 이어 붙인 한 덩어리", () => {
    expect(buildTranscript(segs, false)).toBe("첫 문장 둘째 문장");
  });
});

describe("buildCopyText", () => {
  it("프롬프트 → 머리말 → 스크립트 순서, 빈 줄로 구분", () => {
    const t = buildCopyText(meta, segs, { withTimestamps: true, withHeader: true, withPrompt: true, prompt: "# Role\n요약해라\n", now });
    const [p, h, s] = t.split("\n\n");
    expect(p).toBe("# Role\n요약해라");
    expect(h.startsWith("# 내신 대비는")).toBe(true);
    expect(s).toBe("[0:00] 첫 문장\n[1:05] 둘째 문장");
  });
  it("옵션을 다 끄면 스크립트만", () => {
    expect(buildCopyText(meta, segs, { withTimestamps: false, withHeader: false, withPrompt: false, prompt: "x", now })).toBe("첫 문장 둘째 문장");
  });
  it("프롬프트 포함이어도 빈 프롬프트는 붙이지 않는다", () => {
    const t = buildCopyText(meta, segs, { withTimestamps: false, withHeader: false, withPrompt: true, prompt: "   ", now });
    expect(t).toBe("첫 문장 둘째 문장");
  });
});
