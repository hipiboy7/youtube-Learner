import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("index.html 에 #root 가 없다");
}
createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
