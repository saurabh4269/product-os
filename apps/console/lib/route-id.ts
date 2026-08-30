/** Static export pages share one `_` HTML file; read the live URL, not generateStaticParams. */

export function segmentId(path: string, root: string): string {
  const parts = path.split("/").filter(Boolean);
  if (parts[0] !== root) return "";
  const last = parts[parts.length - 1] ?? "";
  if (!last || last === root || last === "_") return "";
  return last;
}

export function queryId(search: string): string {
  const raw = search.startsWith("?") ? search.slice(1) : search;
  return new URLSearchParams(raw).get("id") ?? "";
}
