(function initializeSearch(){
  const input = document.getElementById("q");
  const filters = document.getElementById("schips");
  const results = document.getElementById("sres");
  const count = document.getElementById("scount");
  const more = document.getElementById("moreResults");
  const clear = document.getElementById("clearSearch");
  const labels = new Map([["all", "全部"], ...GROUPS]);
  const pageSize = 60;
  let group = "all", hits = [], shown = 0, pattern = null, markPattern = null;

  function readAddress(){
    const url = new URL(location.href);
    const params = url.hash.startsWith("#search?") ? new URLSearchParams(url.hash.slice(8)) : url.searchParams;
    input.value = params.get("q") || "";
    group = labels.has(params.get("group")) ? params.get("group") : "all";
  }
  function saveAddress(){
    const url = new URL(location.href);
    // file documents may replace their fragment even when the browser disallows changing their query.
    const file = url.protocol === "file:";
    const params = file ? new URLSearchParams() : url.searchParams;
    const term = input.value.trim();
    if (term) params.set("q", term); else params.delete("q");
    if (group !== "all") params.set("group", group); else params.delete("group");
    if (file) {
      const query = params.toString();
      url.hash = query || url.search ? "search?" + query : "";
    } else if (url.hash.startsWith("#search?")) {
      url.hash = "";
    }
    if (url.href !== location.href) {
      try { history.replaceState(history.state, "", url); }
      catch (error) { if (error.name !== "SecurityError") throw error; }
    }
  }
  function appendText(target, text){
    if (!markPattern) { target.append(text); return; }
    let end = 0;
    for (const hit of text.matchAll(markPattern)){
      target.append(text.slice(end, hit.index));
      const mark = document.createElement("mark");
      mark.textContent = hit[0];
      target.append(mark);
      end = hit.index + hit[0].length;
    }
    target.append(text.slice(end));
  }
  function resultLink(doc){
    const [kind, source, title, url, body] = doc;
    const link = document.createElement("a");
    link.className = "sr";
    link.href = url;
    const heading = document.createElement("div");
    heading.className = "t1";
    const label = document.createElement("span");
    label.className = "gl";
    appendText(label, labels.get(kind) + " · " + source);
    heading.append(label);
    appendText(heading, title);
    const excerpt = document.createElement("div");
    excerpt.className = "t2";
    const first = pattern?.exec(body);
    const start = first ? Math.max(0, first.index - 45) : 0;
    const end = first ? first.index + first[0].length + 70 : 110;
    appendText(excerpt, (start ? "…" : "") + body.slice(start,end) + (body.length > end ? "…" : ""));
    link.append(heading, excerpt);
    return link;
  }
  function appendPage(focusFirst){
    const batch = document.createDocumentFragment();
    const end = Math.min(shown + pageSize, hits.length);
    for (let i = shown; i < end; i++) batch.append(resultLink(hits[i]));
    const first = batch.firstElementChild;
    results.append(batch);
    shown = end;
    more.hidden = shown >= hits.length;
    more.textContent = "继续显示（已显示 " + shown + " / " + hits.length + "）";
    if (focusFirst && first) first.focus();
  }
  function render(){
    const term = input.value.trim();
    clear.hidden = !input.value && group === "all";
    // Longer than every indexed document. Avoid compiling an unbounded pasted phrase.
    const literal = term.length <= longest ? term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") : "";
    pattern = literal ? new RegExp(literal, "iu") : null;
    markPattern = pattern ? new RegExp(literal, "giu") : null;
    const matched = !term ? DOCS : pattern ? DOCS.filter(d =>
      pattern.test(d[2]) || pattern.test(d[4]) || pattern.test(d[1]) || pattern.test(labels.get(d[0]))) : [];
    const totals = new Map([["all", matched.length]]);
    for (const d of matched) totals.set(d[0], (totals.get(d[0]) || 0) + 1);
    for (const button of filters.children){
      const key = button.dataset.g;
      button.textContent = labels.get(key) + " " + (totals.get(key) || 0);
      button.setAttribute("aria-pressed", String(key === group));
      button.classList.toggle("on", key === group);
    }
    hits = group === "all" ? matched : matched.filter(d => d[0] === group);
    count.textContent = term || group !== "all" ? "命中 " + hits.length + " 份文档" : "共 " + DOCS.length + " 份文档，输入关键词开始搜索";
    results.replaceChildren();
    shown = 0;
    if (!hits.length){
      const empty = document.createElement("p");
      empty.className = "sempty";
      empty.textContent = "没有找到相关内容，可更换关键词或来源。";
      results.append(empty);
    }
    appendPage(false);
  }
  const longest = DOCS.reduce((max,d) => Math.max(max,d[1].length,d[2].length,d[4].length,labels.get(d[0]).length),0);
  for (const [key] of labels){
    const button = document.createElement("button");
    button.className = "chip";
    button.type = "button";
    button.dataset.g = key;
    filters.append(button);
  }
  filters.addEventListener("click", event => {
    const button = event.target.closest("button[data-g]");
    if (!button) return;
    group = button.dataset.g;
    saveAddress();
    render();
  });
  function commitInput(event){
    if (event.isComposing) return;
    saveAddress();
    render();
  }
  input.addEventListener("input", commitInput);
  input.addEventListener("compositionend", commitInput);
  input.addEventListener("search", commitInput);
  clear.addEventListener("click", () => {
    input.value = "";
    group = "all";
    saveAddress();
    render();
    input.focus();
  });
  document.querySelector(".skip-link").addEventListener("click", event => {
    event.preventDefault();
    document.getElementById("content0").focus();
  });
  results.addEventListener("click", saveAddress);
  more.addEventListener("click", () => appendPage(true));
  window.addEventListener("popstate", () => {readAddress(); render();});
  document.addEventListener("keydown", event => {
    if (event.key === "/" && !event.ctrlKey && !event.metaKey && !event.altKey && !event.target.closest("input, textarea, [contenteditable]")){
      event.preventDefault(); input.focus();
    }
  });
  readAddress();
  render();
  if (input.value) input.focus({preventScroll:true});
})();
