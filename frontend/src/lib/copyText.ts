// 복사 텍스트 조립 — 프롬프트 + 메타데이터 머리말 + (타임스탬프) 스크립트. 등급 A (순수 함수).
// 대응: docs/internal/검토서_Prototype.md 7절. 근거: Gemini 비교(2026-09-15) — URL 판이 앞선 것은 제목·길이·타임스탬프였다.
import { formatTimestamp } from "./time";

export type CopySegment = { start_ms: number; text: string };
export type CopyMeta = {
  title: string; channel_title?: string | null; url: string; duration_s?: number | null; upload_date?: string | null;
  transcript_source?: string | null; transcript_language?: string | null; transcript_model?: string | null;
};
export type CopyOptions = { withTimestamps: boolean; withHeader: boolean; withPrompt: boolean; prompt: string; now?: Date };

/** `20260914` → `2026-09-14`. 다른 형식은 그대로. */
export function formatUploadDate(raw: string | null | undefined): string {
  if (!raw) return "미제공";
  const m = /^(\d{4})(\d{2})(\d{2})$/.exec(raw);
  return m ? `${m[1]}-${m[2]}-${m[3]}` : raw;
}

export function buildHeader(meta: CopyMeta, segmentCount: number, now: Date = new Date()): string {
  const source = meta.transcript_source
    ? `${meta.transcript_source}${meta.transcript_language ? ` / ${meta.transcript_language}` : ""}${meta.transcript_model ? ` / ${meta.transcript_model}` : ""}`
    : "미제공";
  return [
    `# ${meta.title}`,
    `- 채널: ${meta.channel_title ?? "미제공"}`,
    `- URL: ${meta.url}`,
    `- 길이: ${meta.duration_s != null ? formatTimestamp(meta.duration_s * 1000) : "미제공"} / 게시일: ${formatUploadDate(meta.upload_date)}`,
    `- 스크립트 출처: ${source} · 세그먼트 ${segmentCount}개 · 복사 ${now.toISOString().slice(0, 10)}`,
  ].join("\n");
}

export function buildTranscript(segments: CopySegment[], withTimestamps: boolean): string {
  if (withTimestamps) return segments.map((s) => `[${formatTimestamp(s.start_ms)}] ${s.text}`).join("\n");
  return segments.map((s) => s.text).join(" ");
}

/** 최종 복사 텍스트. 프롬프트 → (구분선) → 머리말 → 스크립트. */
export function buildCopyText(meta: CopyMeta, segments: CopySegment[], opts: CopyOptions): string {
  const parts: string[] = [];
  if (opts.withPrompt && opts.prompt.trim()) parts.push(opts.prompt.trimEnd());
  if (opts.withHeader) parts.push(buildHeader(meta, segments.length, opts.now));
  parts.push(buildTranscript(segments, opts.withTimestamps));
  return parts.join("\n\n");
}
