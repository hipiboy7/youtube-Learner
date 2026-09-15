// App 자리 화면 렌더 — 등급 B (Testing Library 파이프라인 확인). 대응: docs/P0_설계서_Common.md 12절.
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App (Phase 0 자리 화면)", () => {
  it("제목과 API 서버 주소를 보여준다", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "youtubeLearner" })).toBeInTheDocument();
    expect(screen.getByText(/API 서버/)).toBeInTheDocument();
  });
});
