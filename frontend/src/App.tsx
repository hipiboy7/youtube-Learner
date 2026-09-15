// 자리 화면 — 화면 설계·구현은 Phase 3 (scope-definition 2.5절). 대응: docs/P0_설계서_Common.md 12절.
import { API_BASE_URL } from "./lib/api";

export default function App() {
  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem", lineHeight: 1.6 }}>
      <h1>youtubeLearner</h1>
      <p>화면은 Phase 3에서 구현합니다. 이 페이지는 빌드·테스트 파이프라인 확인용 자리입니다.</p>
      <p>
        API 서버: <code>{API_BASE_URL}</code>
      </p>
    </main>
  );
}
