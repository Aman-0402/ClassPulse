// Escape user-supplied text before it goes into an HTML string (SweetAlert's
// `html` option). Task titles and CSV-upload error messages both carry text
// someone typed, so without this a value like `<img onerror=...>` would run
// as script in the viewer's browser.
export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
