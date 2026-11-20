(() => {
  const byId = id => document.getElementById(id);
  // Match an editorial headline to its available column as the viewport, font
  // or text changes. Long titles retain their full text and a readable minimum.
  const title = byId("portalTitle");
  function fitTitle() {
    title.style.removeProperty("--heading-fit");
    const maximum = parseFloat(getComputedStyle(title).fontSize);
    const lines = window.innerWidth >= 1024 ? 3 : 2;
    function fits() {
      return title.getBoundingClientRect().height <= lines * parseFloat(getComputedStyle(title).lineHeight) + 1;
    }
    if (fits()) return;
    let low = 20, high = maximum;
    for (let step = 0; step < 8; step++) {
      const middle = (low + high) / 2;
      title.style.setProperty("--heading-fit", middle + "px");
      if (fits()) low = middle;
      else high = middle;
    }
    title.style.setProperty("--heading-fit", low + "px");
  }
  let titleWidth = 0;
  new ResizeObserver(entries => {
    const width = entries[0].contentRect.width;
    if (width !== titleWidth) { titleWidth = width; fitTitle(); }
  }).observe(title.parentElement);
  new MutationObserver(fitTitle).observe(title, {childList:true, characterData:true, subtree:true});
  // The first ResizeObserver delivery fits the laid-out title before paint.
  // Reading its geometry while parsing would force layout before the study controls are wired.
  document.fonts.addEventListener("loadingdone", fitTitle);
  const rows = __STUDY_INDEX__;
  const seasons = ["2026", "2025", "2024"];
  function read(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
    catch { return fallback; }
  }
  function caseUrl(row) { return "season-" + row[0] + ".html#case-" + row[1]; }
  const date = new Date();
  const day = Math.floor(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) / 86400000);
  const available = rows.filter(row => row[3]);
  const daily = available[day % available.length];
  let recent;
  for (const season of seasons) {
    const last = read("cfa" + season + ".last", null);
    if (!last || !Number.isFinite(last.ts) || (recent && recent.ts >= last.ts)) continue;
    const row = rows.find(row => row[0] === season && row[1] === last.seq);
    if (row) recent = {row, ts: last.ts};
  }
  const chosen = recent ? recent.row : daily;
  if (chosen) {
    byId("todayCase").href = byId("studyFromSettings").href = caseUrl(chosen);
    byId("caseIssue").textContent = chosen[0] + " · 第" + chosen[6] + "期 · 判例" + chosen[7];
    byId("caseTopic").textContent = [chosen[2], chosen[8]].filter(Boolean).join(" · ");
    byId("homeTeam").textContent = chosen[4] || "主队";
    byId("awayTeam").textContent = chosen[5] || "客队";
  }
  if (recent) {
    byId("msFoot").href = caseUrl(recent.row);
    byId("caseLabel").textContent = "上次学习";
    byId("caseAction").textContent = byId("studyFromSettings").querySelector("span").textContent = "继续学习";
    if (daily && daily !== recent.row) {
      byId("dailyLink").href = caseUrl(daily);
      byId("dailyLink").hidden = false;
    }
  }
  const sampleText = byId("sampleText");
  const prompt = sampleText.textContent;
  const sampleReview = byId("sampleReview");
  sampleReview.addEventListener("click", () => {
    const reveal = sampleReview.getAttribute("aria-pressed") !== "true";
    sampleReview.setAttribute("aria-pressed", String(reveal));
    sampleReview.textContent = reveal ? "重看问题" : "查看评议认定";
    sampleText.textContent = reveal ? __SAMPLE_REVIEW__ : prompt;
  });
  const search = byId("portalSearch").form;
  search.addEventListener("submit", () => {
    search.querySelector('[role="status"]').textContent = "正在打开搜索结果…";
  });
  const picker = byId("shelfPicker");
  function showShelf() {
    for (const shelf of document.querySelectorAll(".shelf-list")) {
      shelf.hidden = shelf.id !== picker.value;
    }
  }
  picker.addEventListener("change", showShelf);
  showShelf();

  const full = byId("modeFull"), light = byId("modeLite");
  function displayMode(lite) {
    full.setAttribute("aria-pressed", String(!lite));
    light.setAttribute("aria-pressed", String(lite));
    byId("modeDesc").textContent = lite ? "阅读文字，视频跳转官方来源。" : "优先播放本地视频，缺失时提供官方来源。";
    if (lite) document.documentElement.dataset.lite = "1";
    else document.documentElement.removeAttribute("data-lite");
  }
  function setMode(lite) {
    try { localStorage.setItem("cfa.lite", lite ? "1" : "0"); } catch {}
    displayMode(lite);
  }
  full.addEventListener("click", () => setMode(false));
  light.addEventListener("click", () => setMode(true));
  displayMode(read("cfa.lite", 0) === 1);
  function refreshStats() {
    const seen = seasons.reduce((total, year) => total + Object.keys(read("cfa" + year + ".seen", {})).length, 0);
    const fav = seasons.reduce((total, year) => total + Object.keys(new LearningRecords("cfa" + year + ".fav").read()).length, 0);
    const due = Object.values(QuizRecords.readWrong()).filter(row => !row.done && (row.due || 0) <= Date.now()).length;
    byId("msFoot").querySelector("b").textContent = seen;
    byId("msDue").querySelector("b").textContent = due;
    byId("msStreak").textContent = currentStudyStreak(read("cfa.streak", {}));
    byId("msFav").textContent = fav;
  }
  window.addEventListener("storage", event => {
    if (event.key === "cfa.lite" || event.key === null) displayMode(read("cfa.lite", 0) === 1);
    if (QuizRecords.related(event.key) || event.key === "cfa.streak" ||
        /^cfa\d{4}\.(seen|fav)(\.|$)/.test(event.key)) refreshStats();
  });
  refreshStats();
})();
