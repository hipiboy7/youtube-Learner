// 프로토타입 화면 — 채널 → 롱폼/숏폼 목록 → 스크립트(복사) → '요약 및 정리' 저장. 등급 C.
// 대응: docs/internal/검토서_Prototype.md 3절. 정식 화면 설계는 Phase 3 에서 다시 한다.
import { useCallback, useEffect, useState } from "react";
import { API_BASE_URL } from "./lib/api";
import { buildCopyText } from "./lib/copyText";
import { formatTimestamp } from "./lib/time";

type Kind = "long" | "short";
type Channel = { id: number; yt_channel_id: string; title: string; url: string; synced_at: string | null; counts: Record<Kind, number> };
type Segment = { idx: number; start_ms: number; end_ms: number; text: string };
type Video = {
  yt_video_id: string; kind: Kind; title: string; url: string; duration_s: number | null; view_count: number | null;
  thumbnail_url: string | null; upload_date: string | null; language: string | null;
  transcript_status: "none" | "pending" | "done" | "failed"; transcript_source: string | null; transcript_language: string | null;
  transcript_model: string | null; transcript_error: string | null; progress: number; has_summary?: boolean;
  segments?: Segment[]; full_text?: string; channel_title?: string | null;
};
type Summary = { text: string; service: string; updated_at: string | null };
type Prompt = { text: string; is_default: boolean; updated_at: string | null };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

const statusLabel: Record<Video["transcript_status"], string> = { none: "없음", pending: "진행 중", done: "완료", failed: "실패" };

export default function App() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [channelId, setChannelId] = useState<number | null>(null);
  const [kind, setKind] = useState<Kind>("long");
  const [videos, setVideos] = useState<Video[]>([]);
  const [selected, setSelected] = useState<Video | null>(null);
  const [summary, setSummary] = useState<Summary>({ text: "", service: "", updated_at: null });
  const [url, setUrl] = useState("https://www.youtube.com/@sebasi15");
  const [limit, setLimit] = useState(12);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // 복사 옵션 — 기본값: 타임스탬프·머리말·프롬프트 전부 켬 (Gemini 비교 결과: 제목·길이·타임스탬프가 빠지면 요약이 지어낸다)
  const [withTimestamps, setWithTimestamps] = useState(true);
  const [withHeader, setWithHeader] = useState(true);
  const [withPrompt, setWithPrompt] = useState(true);
  const [prompt, setPrompt] = useState<Prompt>({ text: "", is_default: true, updated_at: null });
  const [promptDraft, setPromptDraft] = useState<string | null>(null); // null = 편집기 닫힘
  const [backendWarning, setBackendWarning] = useState<string | null>(null);
  const [manualCopyText, setManualCopyText] = useState<string | null>(null); // 클립보드 실패 시 직접 선택·복사용

  const EXPECTED_BACKEND = "proto-2";

  const say = (msg: string) => { setNotice(msg); window.setTimeout(() => setNotice(null), 4000); };

  const loadChannels = useCallback(async () => {
    const list = await api<Channel[]>("/proto/channels");
    setChannels(list);
    if (channelId === null && list.length) setChannelId(list[0].id);
  }, [channelId]);

  const loadVideos = useCallback(async () => {
    if (channelId === null) return;
    setVideos(await api<Video[]>(`/proto/channels/${channelId}/videos?kind=${kind}`));
  }, [channelId, kind]);

  const loadDetail = useCallback(async (id: string) => {
    const [v, s] = await Promise.all([api<Video>(`/proto/videos/${id}`), api<Summary>(`/proto/videos/${id}/summary`)]);
    setSelected(v);
    setSummary(s);
  }, []);

  useEffect(() => { loadChannels().catch((e) => say(`백엔드 연결 실패: ${e.message}`)); }, [loadChannels]);
  useEffect(() => {
    api<{ version?: string }>("/health")
      .then((h) => {
        if (h.version !== EXPECTED_BACKEND) {
          setBackendWarning(`백엔드가 옛 버전입니다 (${h.version ?? "버전 없음"} ≠ ${EXPECTED_BACKEND}). 프롬프트 저장 등이 동작하지 않습니다 — 두 창을 닫고 .\\scripts\\dev_proto.ps1 을 다시 실행하세요 (옛 서버를 자동 정리합니다).`);
        }
      })
      .catch((e) => setBackendWarning(`백엔드(${API_BASE_URL})에 연결할 수 없습니다: ${e.message}`));
    api<Prompt>("/proto/settings/summary_prompt").then(setPrompt).catch((e) => say(`프롬프트를 불러오지 못했다: ${e.message}`));
  }, []);
  useEffect(() => { loadVideos().catch((e) => say(e.message)); }, [loadVideos]);
  useEffect(() => {
    if (!selected || selected.transcript_status !== "pending") return;
    const t = window.setInterval(() => { loadDetail(selected.yt_video_id).catch(() => undefined); loadVideos().catch(() => undefined); }, 3000);
    return () => window.clearInterval(t);
  }, [selected, loadDetail, loadVideos]);

  async function addChannel() {
    setBusy("채널 동기화 중 (롱폼·숏폼 탭 각 " + limit + "건)…");
    try {
      const r = await api<{ id: number; title: string; counts: Record<Kind, number>; added: number }>("/proto/channels", {
        method: "POST", body: JSON.stringify({ url, limit }),
      });
      await loadChannels();
      setChannelId(r.id);
      say(`${r.title}: 롱폼 ${r.counts.long} · 숏폼 ${r.counts.short} (신규 ${r.added})`);
    } catch (e) { say(`동기화 실패: ${(e as Error).message}`); } finally { setBusy(null); }
  }

  async function fetchTranscript(force = false) {
    if (!selected) return;
    setBusy("스크립트 확보 중 — 자막 확인 → 없으면 Whisper…");
    try {
      const v = await api<Video>(`/proto/videos/${selected.yt_video_id}/transcript`, { method: "POST", body: JSON.stringify({ force_whisper: force }) });
      setSelected(v);
      await loadVideos();
      say(v.transcript_status === "done" ? `스크립트 완료 (${v.transcript_source}, ${v.segments?.length ?? 0} 세그먼트)` : "자막이 없어 Whisper 로 전사 중 — 진행률을 표시한다");
    } catch (e) { say(`실패: ${(e as Error).message}`); } finally { setBusy(null); }
  }

  async function writeClipboard(text: string): Promise<string> {
    // 1) 표준 API (localhost·https 에서만 허용) → 2) 숨은 textarea + execCommand (구형/비보안 컨텍스트) → 3) 실패 시 수동 복사 상자
    if (navigator.clipboard?.writeText) {
      try { await navigator.clipboard.writeText(text); return "clipboard"; } catch { /* 아래 폴백 */ }
    }
    const ta = document.createElement("textarea");
    ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.left = "-9999px";
    document.body.appendChild(ta); ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    if (!ok) throw new Error("브라우저가 클립보드 접근을 막았다");
    return "execCommand";
  }

  async function copyTranscript() {
    if (!selected?.segments?.length) { say("복사할 스크립트가 없다 — 먼저 '스크립트 가져오기'"); return; }
    const text = buildCopyText(selected, selected.segments, { withTimestamps, withHeader, withPrompt, prompt: prompt.text });
    const parts = [withPrompt && prompt.text.trim() && "프롬프트", withHeader && "머리말", withTimestamps ? "타임스탬프 스크립트" : "스크립트"].filter(Boolean).join(" + ");
    try {
      const how = await writeClipboard(text);
      setManualCopyText(null);
      say(`${parts} ${text.length.toLocaleString()}자를 클립보드에 복사했다 (${how}) — AI 챗 서비스에 붙여 넣으세요`);
    } catch (e) {
      setManualCopyText(text);
      say(`클립보드 복사 실패: ${(e as Error).message} — 아래 상자에서 직접 전체 선택(Ctrl+A) 후 복사(Ctrl+C)하세요`);
    }
  }

  async function savePrompt() {
    if (promptDraft === null) return;
    try {
      setPrompt(await api<Prompt>("/proto/settings/summary_prompt", { method: "PUT", body: JSON.stringify({ text: promptDraft }) }));
      setPromptDraft(null);
      say("프롬프트를 저장했다 — 이후 복사에 적용된다");
    } catch (e) { say(`프롬프트 저장 실패: ${(e as Error).message}`); }
  }

  async function resetPrompt() {
    try {
      const p = await api<Prompt>("/proto/settings/summary_prompt", { method: "DELETE" });
      setPrompt(p);
      setPromptDraft(promptDraft === null ? null : p.text);
      say("프롬프트를 기본값으로 되돌렸다");
    } catch (e) { say(`복원 실패: ${(e as Error).message}`); }
  }

  async function saveSummary() {
    if (!selected) return;
    try {
      const s = await api<Summary>(`/proto/videos/${selected.yt_video_id}/summary`, { method: "PUT", body: JSON.stringify(summary) });
      setSummary(s);
      await loadVideos();
      say("요약 및 정리를 저장했다");
    } catch (e) { say(`저장 실패: ${(e as Error).message}`); }
  }

  const channel = channels.find((c) => c.id === channelId) ?? null;

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "1rem 1.5rem", lineHeight: 1.5, color: "#1f2328" }}>
      <header style={{ display: "flex", alignItems: "baseline", gap: "1rem", flexWrap: "wrap" }}>
        <h1 style={{ margin: 0, fontSize: "1.4rem" }}>youtubeLearner</h1>
        <span style={{ color: "#57606a" }}>프로토타입 — API 서버 <code>{API_BASE_URL}</code></span>
        {notice && <span style={{ marginLeft: "auto", background: "#fff8c5", padding: "0.2rem 0.6rem", borderRadius: 6 }}>{notice}</span>}
      </header>
      {backendWarning && (
        <div style={{ background: "#ffebe9", border: "1px solid #ff8182", color: "#82071e", padding: "0.5rem 0.8rem", borderRadius: 6, marginTop: "0.6rem" }}>
          ⚠️ {backendWarning}
        </div>
      )}

      <section style={{ display: "flex", gap: "0.5rem", margin: "1rem 0", alignItems: "center", flexWrap: "wrap" }}>
        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="채널 URL 또는 @핸들" style={{ flex: "1 1 320px", padding: "0.45rem 0.6rem" }} />
        <label>탭당 <input type="number" min={1} max={200} value={limit} onChange={(e) => setLimit(Number(e.target.value))} style={{ width: 64 }} /> 건</label>
        <button onClick={addChannel} disabled={!!busy}>채널 추가·동기화</button>
        {channels.length > 1 && (
          <select value={channelId ?? ""} onChange={(e) => { setChannelId(Number(e.target.value)); setSelected(null); }}>
            {channels.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
        )}
        {busy && <span style={{ color: "#0969da" }}>{busy}</span>}
      </section>

      {channel && (
        <div style={{ display: "grid", gridTemplateColumns: "minmax(320px, 2fr) 3fr", gap: "1.25rem" }}>
          <section>
            <h2 style={{ fontSize: "1.05rem", margin: "0 0 0.5rem" }}>{channel.title} <small style={{ color: "#57606a" }}>{channel.yt_channel_id}</small></h2>
            <div style={{ display: "flex", gap: "0.25rem", marginBottom: "0.5rem" }}>
              {(["long", "short"] as Kind[]).map((k) => (
                <button key={k} onClick={() => { setKind(k); setSelected(null); }}
                  style={{ fontWeight: kind === k ? 700 : 400, borderBottom: kind === k ? "2px solid #0969da" : "2px solid transparent" }}>
                  {k === "long" ? "롱폼" : "숏폼"} ({channel.counts[k]})
                </button>
              ))}
            </div>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, maxHeight: "70vh", overflow: "auto" }}>
              {videos.map((v) => (
                <li key={v.yt_video_id} onClick={() => loadDetail(v.yt_video_id).catch((e) => say(e.message))}
                  style={{ display: "flex", gap: "0.6rem", padding: "0.4rem", cursor: "pointer", borderRadius: 6,
                    background: selected?.yt_video_id === v.yt_video_id ? "#ddf4ff" : "transparent" }}>
                  {v.thumbnail_url && <img src={v.thumbnail_url} alt="" style={{ width: 96, height: 54, objectFit: "cover", borderRadius: 4 }} />}
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{v.title}</div>
                    <div style={{ fontSize: "0.85rem", color: "#57606a" }}>
                      {v.duration_s != null ? formatTimestamp(v.duration_s * 1000) : "길이 미확인"} · 스크립트 {statusLabel[v.transcript_status]}
                      {v.transcript_source ? ` (${v.transcript_source})` : ""}{v.has_summary ? " · 요약 있음" : ""}
                    </div>
                  </div>
                </li>
              ))}
              {!videos.length && <li style={{ color: "#57606a" }}>영상 없음 — 동기화하세요</li>}
            </ul>
          </section>

          <section>
            {!selected ? <p style={{ color: "#57606a" }}>왼쪽에서 영상을 선택하세요.</p> : (
              <>
                <h2 style={{ fontSize: "1.05rem", margin: "0 0 0.25rem" }}><a href={selected.url} target="_blank" rel="noreferrer">{selected.title}</a></h2>
                <div style={{ fontSize: "0.85rem", color: "#57606a", marginBottom: "0.5rem" }}>
                  {selected.kind === "long" ? "롱폼" : "숏폼"} · {selected.duration_s != null ? formatTimestamp(selected.duration_s * 1000) : "길이 미확인"}
                  {selected.upload_date ? ` · ${selected.upload_date}` : ""}{selected.language ? ` · 원어 ${selected.language}` : ""}
                </div>

                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap", marginBottom: "0.5rem" }}>
                  <button onClick={() => fetchTranscript(false)} disabled={!!busy || selected.transcript_status === "pending"}>스크립트 가져오기</button>
                  <button onClick={() => fetchTranscript(true)} disabled={!!busy || selected.transcript_status === "pending"} title="자막이 있어도 Whisper 로 전사">Whisper 로 전사</button>
                  <button onClick={copyTranscript} disabled={selected.transcript_status !== "done"} style={{ fontWeight: 700 }}>📋 스크립트 복사</button>
                  <span style={{ fontSize: "0.85rem", color: "#57606a" }}>
                    상태 {statusLabel[selected.transcript_status]}
                    {selected.transcript_status === "pending" && ` ${Math.round(selected.progress * 100)}%`}
                    {selected.transcript_source && ` · 출처 ${selected.transcript_source}${selected.transcript_model ? ` (${selected.transcript_model})` : ""}`}
                  </span>
                </div>
                {selected.transcript_status === "pending" && (
                  <div style={{ height: 6, background: "#eee", borderRadius: 3, marginBottom: "0.5rem" }}>
                    <div style={{ width: `${Math.round(selected.progress * 100)}%`, height: "100%", background: "#0969da", borderRadius: 3 }} />
                  </div>
                )}
                {selected.transcript_error && <p style={{ color: "#cf222e" }}>{selected.transcript_error}</p>}

                <fieldset style={{ border: "1px solid #d0d7de", borderRadius: 6, padding: "0.4rem 0.6rem", marginBottom: "0.6rem", fontSize: "0.85rem" }}>
                  <legend style={{ color: "#57606a" }}>복사 형식</legend>
                  <label style={{ marginRight: "0.8rem" }}><input type="checkbox" checked={withPrompt} onChange={(e) => setWithPrompt(e.target.checked)} /> 요약 프롬프트 포함</label>
                  <label style={{ marginRight: "0.8rem" }}><input type="checkbox" checked={withHeader} onChange={(e) => setWithHeader(e.target.checked)} /> 메타데이터 머리말(제목·채널·URL·길이·게시일·출처)</label>
                  <label style={{ marginRight: "0.8rem" }}><input type="checkbox" checked={withTimestamps} onChange={(e) => setWithTimestamps(e.target.checked)} /> 타임스탬프 [m:ss]</label>
                  <button onClick={() => setPromptDraft(promptDraft === null ? prompt.text : null)} style={{ marginLeft: "0.4rem" }}>
                    {promptDraft === null ? "✏️ 프롬프트 편집" : "편집 닫기"}
                  </button>
                  <span style={{ marginLeft: "0.6rem", color: "#57606a" }}>
                    {prompt.is_default ? "기본 프롬프트" : `사용자 편집본${prompt.updated_at ? ` (저장 ${new Date(prompt.updated_at).toLocaleString()})` : ""}`}
                  </span>
                  {promptDraft !== null && (
                    <div style={{ marginTop: "0.5rem" }}>
                      <textarea value={promptDraft} onChange={(e) => setPromptDraft(e.target.value)} spellCheck={false}
                        style={{ width: "100%", minHeight: 220, padding: "0.5rem", boxSizing: "border-box", fontFamily: "ui-monospace, monospace", fontSize: "0.8rem" }} />
                      <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.3rem" }}>
                        <button onClick={savePrompt} style={{ fontWeight: 700 }} disabled={!promptDraft.trim()}>💾 프롬프트 저장</button>
                        <button onClick={resetPrompt}>기본값 복원</button>
                        <span style={{ color: "#57606a" }}>{promptDraft.length.toLocaleString()}자 · 복사 텍스트 맨 앞에 붙는다</span>
                      </div>
                    </div>
                  )}
                </fieldset>

                <div style={{ maxHeight: "34vh", overflow: "auto", border: "1px solid #d0d7de", borderRadius: 6, padding: "0.5rem", marginBottom: "1rem", fontSize: "0.92rem" }}>
                  {selected.segments?.length ? selected.segments.map((s) => (
                    <div key={s.idx} style={{ display: "flex", gap: "0.5rem" }}>
                      <a href={`${selected.url}${selected.url.includes("?") ? "&" : "?"}t=${Math.floor(s.start_ms / 1000)}s`} target="_blank" rel="noreferrer"
                        style={{ color: "#57606a", fontVariantNumeric: "tabular-nums", flex: "0 0 auto" }}>{formatTimestamp(s.start_ms)}</a>
                      <span>{s.text}</span>
                    </div>
                  )) : <span style={{ color: "#57606a" }}>스크립트가 없다 — "스크립트 가져오기"</span>}
                </div>

                {manualCopyText !== null && (
                  <div style={{ marginBottom: "1rem" }}>
                    <div style={{ fontSize: "0.85rem", color: "#82071e", marginBottom: "0.25rem" }}>
                      클립보드 복사가 막혀 있어 아래 상자에 복사 텍스트를 넣었습니다 — 상자를 클릭해 Ctrl+A, Ctrl+C 로 복사하세요.
                      <button onClick={() => setManualCopyText(null)} style={{ marginLeft: "0.5rem" }}>닫기</button>
                    </div>
                    <textarea readOnly value={manualCopyText} onFocus={(e) => e.currentTarget.select()}
                      style={{ width: "100%", minHeight: 160, padding: "0.5rem", boxSizing: "border-box", fontFamily: "ui-monospace, monospace", fontSize: "0.8rem" }} />
                  </div>
                )}

                <h3 style={{ fontSize: "1rem", margin: "0 0 0.25rem" }}>요약 및 정리 <small style={{ color: "#57606a" }}>외부 AI 챗 서비스에서 받은 글을 붙여 넣고 저장</small></h3>
                <textarea value={summary.text} onChange={(e) => setSummary({ ...summary, text: e.target.value })}
                  placeholder="복사한 스크립트를 ChatGPT·Claude 등에 붙여 요약을 받은 뒤, 그 결과를 여기에 붙여 넣으세요"
                  style={{ width: "100%", minHeight: 160, padding: "0.5rem", boxSizing: "border-box" }} />
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginTop: "0.4rem" }}>
                  <input value={summary.service} onChange={(e) => setSummary({ ...summary, service: e.target.value })} placeholder="어느 서비스에서 받았나 (선택)" style={{ flex: "1 1 200px", padding: "0.4rem" }} />
                  <button onClick={saveSummary} style={{ fontWeight: 700 }}>💾 저장</button>
                  <span style={{ fontSize: "0.85rem", color: "#57606a" }}>{summary.updated_at ? `저장 ${new Date(summary.updated_at).toLocaleString()}` : "저장된 요약 없음"}</span>
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
