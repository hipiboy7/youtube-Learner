// App 프로토타입 화면 렌더 — 등급 B (파이프라인 확인). 대응: docs/internal/검토서_Prototype.md.
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

describe("App (프로토타입)", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } })));
  });

  it("제목·API 서버·채널 입력을 보여준다", async () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "youtubeLearner" })).toBeInTheDocument();
    expect(screen.getByText(/API 서버/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/채널 URL/)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /채널 추가/ })).toBeInTheDocument();
  });
});
