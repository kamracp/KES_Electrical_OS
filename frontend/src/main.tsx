import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

const rootElement = document.getElementById("root");

if (rootElement === null) {
  throw new Error("KES Electrical OS root element was not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <main>
      <h1>KES Electrical OS</h1>
      <p>Engineering workspace initializing.</p>
    </main>
  </StrictMode>,
);
