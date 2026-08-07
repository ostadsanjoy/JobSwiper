export function stripHtml(html) {
  if (!html) return "";
  let clean = html;
  if (clean.includes("&lt;") || clean.includes("&gt;")) {
    const doc = new DOMParser().parseFromString(clean, "text/html");
    clean = doc.body.textContent || clean;
  }
  const doc = new DOMParser().parseFromString(clean, "text/html");
  return (doc.body.textContent || "").replace(/\s+/g, " ").trim();
}

export function sanitizeHtml(html) {
  if (!html) return "";
  let clean = html;

  // Unescape HTML entities if text contains escaped tags
  if (clean.includes("&lt;") || clean.includes("&gt;")) {
    const doc = new DOMParser().parseFromString(clean, "text/html");
    clean = doc.body.textContent || clean;
  }
  if (clean.includes("&lt;") || clean.includes("&gt;")) {
    const doc = new DOMParser().parseFromString(clean, "text/html");
    clean = doc.body.textContent || clean;
  }

  // Strip script and inline event handlers
  clean = clean
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/ on\w+="[^"]*"/gi, "")
    .replace(/ on\w+='[^']*'/gi, "");

  // Strip inline styles so standard clean typography renders naturally
  clean = clean.replace(/ style="[^"]*"/gi, "").replace(/ style='[^']*'/gi, "");

  return clean;
}