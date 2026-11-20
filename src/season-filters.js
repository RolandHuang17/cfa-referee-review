// Only these filters describe the public case catalogue. Personal notes, tags and
// bookmarks stay in local storage, and the selected case is omitted from shares.
const publicSeasonFilterKeys = ["path", "cat", "v", "comp", "team", "issue", "q"];

function seasonSharePage(href, canonical, season) {
  const url = new URL(href);
  const host = url.hostname.toLowerCase();
  const local = host === "localhost" || host.endsWith(".localhost") || /^127(?:\.\d{1,3}){3}$/.test(host) ||
    host === "[::1]" || host === "[::]" || host === "0.0.0.0";
  if (!local && (url.protocol === "http:" || url.protocol === "https:")) return url.origin + url.pathname;
  return canonical || "season-" + season + ".html";
}

function seasonFilterHash(filters, selected) {
  const params = new URLSearchParams();
  for (const key of publicSeasonFilterKeys) {
    const value = filters[key];
    if (value && value.trim()) params.set(key, value.trim());
  }
  if (!params.toString()) return selected ? "#case-" + selected : "";
  if (!selected && [...params.keys()].length === 1 && params.has("cat")) return "#cat-" + params.get("cat");
  if (selected) params.set("case", selected);
  return "#filters?" + params.toString();
}

function readSeasonFilterHash(hash, allowed) {
  const filters = {};
  const single = hash.match(/^#case-(\d+)$/);
  const category = hash.match(/^#cat-([\w-]+)$/);
  if (single) return {filters, selected:Number(single[1])};
  if (category && allowed.cat.has(category[1])) return {filters:{cat:category[1]}, selected:null};
  if (!hash.startsWith("#filters?")) return {filters, selected:null};
  const params = new URLSearchParams(hash.slice("#filters?".length));
  for (const key of publicSeasonFilterKeys) {
    const value = (params.get(key) || "").trim();
    if (value && (key === "q" || allowed[key].has(value))) filters[key] = value;
  }
  // Selecting a team in the sidebar intentionally includes all its competitions.
  if (filters.team) delete filters.comp;
  const selected = params.get("case");
  return {filters, selected:selected && /^\d+$/.test(selected) ? Number(selected) : null};
}
