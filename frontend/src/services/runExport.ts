// Export of a persisted calculation run (Master Prompt v2.1 sections 19 and 20).
// A study page may only export a run the backend has stored: the file holds the
// stored run summary and the result it produced. Shared by every module.
export function downloadRunJson(payload: unknown, filename: string): void {
  if (typeof URL.createObjectURL !== "function") {
    return;
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
