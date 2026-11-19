(() => {
  "use strict";
  const data = JSON.parse(document.getElementById("compare-data").textContent);
  let decodedCases;
  // Decode only after a lesson or the comparison picker is opened. Each code is
  // one big-endian LZW dictionary index; TextDecoder reconstructs the Chinese text.
  function caseIndex() {
    if (decodedCases) return decodedCases;
    const input = atob(data.caseIndex.codes);
    const output = new Uint8Array(data.caseIndex.bytes);
    const dictionary = Array.from({length:256}, (_,i) => String.fromCharCode(i));
    let previous = "", cursor = 0;
    for (let i=0; i<input.length; i+=2) {
      const code = (input.charCodeAt(i) << 8) | input.charCodeAt(i+1);
      const phrase = code === dictionary.length ? previous + previous[0] : dictionary[code];
      for (let j=0; j<phrase.length; j++) output[cursor++] = phrase.charCodeAt(j);
      if (previous && dictionary.length < 65536) dictionary.push(previous + phrase[0]);
      previous = phrase;
    }
    if (cursor !== output.length) throw Error("判例目录不完整，请重新打开完整学习包。");
    decodedCases = JSON.parse(new TextDecoder().decode(output));
    return decodedCases;
  }
  const workspace = document.getElementById("workspace");
  const attempts = new CompareAttempts();
  const byId = id => document.getElementById(id);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
  })[ch]);
  const mobile = matchMedia("(max-width: 760px)");
  const letters = ["A","B"];
  const insufficient = "unsure";
  let route = "", lesson = null, activeSide = 0;
  let player = null, selectedPair = [], panelOffsets = [0, 0];
  let lastFocus = null;
  function matchTitle(c) {
    return c.home && c.away ? `${c.home} 对 ${c.away}` : `${c.comp || "赛季评议"} · 判例 ${c.no}`;
  }
  function citation(c) {
    return `${c.season} 赛季 · 第 ${c.issue} 期 · 判例 ${c.no}`;
  }
  function header(title, kicker, back="#", label="课程目录") {
    return `<div class="compare-toolbar compare-noprint"><a href="${back}">← ${label}</a>
      <button type="button" class="compare-secondary" id="copy-pair">复制分享链接</button>
      <label id="share-label" hidden>复制此链接<input id="share-fallback" type="text" readonly></label>
      <span id="share-status" role="status"></span></div>
      <p class="compare-kicker">${esc(kicker)}</p><h1 tabindex="-1" id="compare-title">${esc(title)}</h1>`;
  }
  function shell(html) {
    stopMedia();
    workspace.innerHTML = `<div class="compare-shell">${html}</div>`;
    const shareButton = byId("copy-pair");
    if (shareButton) shareButton.onclick = share;
  }
  function shareAddress() {
    const canonical = document.querySelector('link[rel="canonical"]');
    const local = location.protocol === "file:" || location.hostname === "localhost" ||
      location.hostname.endsWith(".localhost") || location.hostname === "[::1]" || /^127\./.test(location.hostname);
    const url = new URL(local && canonical ? canonical.href : location.href);
    url.search = "";
    return url;
  }
  async function share() {
    const url = shareAddress();
    url.hash = location.hash;
    const field = byId("share-label");
    try {
      await navigator.clipboard.writeText(url.href);
      byId("share-status").textContent = "已复制链接";
    } catch (_) {
      field.hidden = false;
      const input = field.querySelector("input");
      input.value = url.href;
      input.focus();
      input.select();
      byId("share-status").textContent = "请复制已选中的链接";
    }
  }
  function stopMedia() {
    if (!player) return;
    const previous = player;
    player = null;
    previous.pause();
    previous.removeAttribute("src");
    previous.load();
    const box = previous.closest(".compare-media");
    box?.querySelector("[data-play]")?.removeAttribute("hidden");
    box?.querySelector("[data-clip-control]")?.remove();
    previous.remove();
  }
  function videoFragment(clip) {
    return clip ? `#t=${clip.start},${clip.end}` : "";
  }
  function mediaBox(c, clip=null) {
    const index = clip ? clip.video_index : 0;
    const files = c.video_files || [], urls = c.video_urls || [];
    if (!(files[index] || urls[index])) return '<p class="compare-status">本例没有视频，可阅读比赛情形。</p>';
    const frag = videoFragment(clip);
    const lite = document.documentElement.hasAttribute("data-lite");
    const opts = !clip && Math.max(files.length,urls.length) > 1 ?
      `<label>视频角度<select data-angle>${Array.from({length:Math.max(files.length,urls.length)},(_,i)=>`<option value="${i}">角度 ${i+1}</option>`).join("")}</select></label>` : "";
    const link = urls[index] ? `<a data-official-video href="${esc(urls[index]+frag)}" target="_blank" rel="noopener noreferrer">官方视频 ↗</a>` : "";
    return `<div class="compare-media compare-noprint" data-media-case="${esc(c.season+"-"+c.seq)}">
      ${opts}${lite ? "" : `<button class="compare-secondary" data-play type="button">${clip ? "播放观察片段" : "播放判例视频"}</button>`}
      <span data-media-status role="status">${lite ? "轻量版 · 文字学习" : ""}</span>
      ${lite || !clip ? link : ""}</div>`;
  }
  function bindMedia(clip=null) {
    workspace.querySelectorAll("[data-media-case]").forEach(box => {
      const c = caseIndex()[box.dataset.mediaCase];
      const button = box.querySelector("[data-play]");
      const select = box.querySelector("[data-angle]");
      const link = box.querySelector("[data-official-video]");
      const note = box.querySelector("[data-media-status]");
      const getIndex = () => clip ? clip.video_index : Number(select?.value || 0);
      if (select) select.onchange = () => {
        stopMedia();
        if (link) link.href = c.video_urls[getIndex()] || c.source;
        note.textContent = "";
      };
      if (!button) return;
      button.onclick = () => {
        stopMedia();
        const index = getIndex();
        const file = c.video_files[index], url = c.video_urls[index];
        const video = document.createElement("video");
        player = video;
        video.playsInline = true;
        video.controls = !clip;
        video.muted = Boolean(clip);
        video.setAttribute("aria-label", `${matchTitle(c)}${clip ? "观察片段" : "判例视频"}`);
        if (clip) video.style.visibility = "hidden";
        const status = text => {if (player === video) note.textContent = text;};
        if (clip) {
          // Decode at the verified in-point before showing any picture or audio.
          video.addEventListener("loadedmetadata", () => {
            if (player !== video) return;
            video.currentTime = clip.start;
          });
          const reveal = () => {
            if (player !== video || video.seeking || video.currentTime < clip.start || video.currentTime >= clip.end) return;
            video.style.visibility = "visible";
          };
          if (!video.requestVideoFrameCallback) {
            video.addEventListener("timeupdate", reveal);
          }
          let frameHandle = null;
          const withinClip = (_, frame) => {
            if (player !== video) return;
            if (frame.mediaTime >= clip.end) {stopMedia(); note.textContent = "片段已结束，可再次播放。"; return;}
            if (frame.mediaTime >= clip.start && !video.seeking) video.style.visibility = "visible";
            frameHandle = video.requestVideoFrameCallback(withinClip);
          };
          if (video.requestVideoFrameCallback) frameHandle = video.requestVideoFrameCallback(withinClip);
          video.addEventListener("emptied", () => {
            if (player !== video && frameHandle !== null) video.cancelVideoFrameCallback(frameHandle);
          });
          video.addEventListener("ended", () => {
            if (player === video) {stopMedia(); note.textContent = "片段已结束，可再次播放。";}
          });
          video.addEventListener("timeupdate", () => {
            if (player === video && video.currentTime >= clip.end) {stopMedia(); note.textContent = "片段已结束，可再次播放。";}
          });
        }
        let remote = !file;
        video.addEventListener("error", () => {
          if (player !== video) return;
          if (!remote && url && navigator.onLine) {
            remote = true;
            status("本机缺片，正在尝试官方视频…");
            video.src = url + videoFragment(clip);
            video.play().catch(()=>{});
          } else {
            stopMedia();
            note.textContent = clip ? "视频当前无法打开。可以阅读比赛情形，或选择现有画面不足以判断。" : "视频当前无法打开。可以阅读比赛事件、足协认定或打开官方来源。";
          }
        });
        const controls = document.createElement("button");
        if (clip) {
          controls.type = "button";
          controls.dataset.clipControl = "";
          controls.className = "compare-secondary";
          controls.textContent = "暂停片段";
          controls.onclick = () => {
            if (video.paused) video.play().catch(()=>status("请重试播放")); else video.pause();
          };
          video.addEventListener("pause", () => {
            controls.textContent = "继续播放";
            if (player !== video) controls.remove();
          });
          video.addEventListener("play", () => {controls.textContent = "暂停片段";});
          video.addEventListener("emptied", () => {if (player !== video) controls.remove();});
          box.append(controls);
        }
        button.hidden = true;
        box.append(video);
        video.src = (file ? `videos/${file}` : url) + videoFragment(clip);
        status("");
        video.play().catch(() => {
          if (player === video && !video.error) status("点击播放控件继续。");
        });
      };
    });
  }
  function optionName(code) {
    if (code === insufficient) return "现有画面不足以判断";
    return lesson.options.find(o => o.id === code)?.label || code;
  }
  function statusBar() {
    return `<div class="compare-status compare-noprint"><span id="save-status" role="status"></span>
      <button class="compare-secondary" type="button" id="retry-save" hidden>重试保存</button></div>`;
  }
  function reportSave() {
    const failed = attempts.store.pending.size > 0;
    byId("save-status").textContent = failed ? "保存失败，本页仍保留草稿。请重试保存或打印当前记录。" :
      attempts.current.updated ? "已保存到本机" : "初判和复盘仅保存在本机";
    byId("retry-save").hidden = !failed;
    byId("retry-save").onclick = () => {attempts.store.retry(); reportSave();};
  }
  function save() {
    attempts.save();
    reportSave();
  }
  function historyMenu() {
    const items = attempts.list(lesson.id);
    if (!items.length) return "";
    const selected = attempts.current.id;
    const choices = items.map((a,i) => {
      const when = new Date(a.updated).toLocaleString("zh-CN");
      const state = a.picks.length === 2 ? "已复盘" : `已提交 ${a.picks.length}/2 案`;
      return `<option value="${esc(a.id)}" ${a.id===selected ? "selected" : ""}>${i+1} · ${esc(when)} · ${state}</option>`;
    });
    if (!items.some(a=>a.id===selected)) choices.unshift('<option selected value="">本次练习</option>');
    return `<label class="compare-field compare-noprint">本机练习记录<select id="history-attempt">${choices.join("")}</select></label>`;
  }
  function bindHistory() {
    if (byId("history-attempt")) byId("history-attempt").onchange = e => {
      if (!e.target.value) return;
      attempts.start(lesson.id, e.target.value);
      showLesson();
      focusTitle();
    };
  }
  function showLesson() {
    const a = attempts.current;
    if (a.picks.length >= 2) {showReview(); return;}
    const index = a.picks.length;
    const member = lesson.cases[index], c = caseIndex()[member.id], draft = a.drafts[index];
    const answers = [...lesson.options, {id:insufficient, label:optionName(insufficient)}];
    const radios = answers.map(o => `<label><input type="radio" name="verdict" value="${esc(o.id)}"
      ${o.id===draft.verdict ? "checked" : ""} required><span>${esc(o.label)}</span></label>`).join("");
    shell(header(lesson.title, `精编盲判 · 第 ${index+1} / 2 案`) +
      `<div class="compare-grid"><article class="compare-panel"><p class="compare-kicker">案例 ${letters[index]} · ${esc(citation(c))}</p>
      <h2>${esc(matchTitle(c))}</h2><p>${esc(member.prompt)}</p>${mediaBox(c,member.clip)}</article>
      <form id="lesson-form" class="compare-panel"><fieldset class="compare-choices"><legend>${esc(lesson.question)}</legend>
      ${radios}</fieldset><label class="compare-field">我观察到什么（选填）<textarea id="observation" rows="3">${esc(draft.observation || "")}</textarea></label>
      <button id="save-pick" class="compare-primary" type="submit">${index ? "提交并核对两案" : "提交初判，进入案例 B"}</button></form></div>
      ${statusBar()}${historyMenu()}<button id="print-draft" class="compare-secondary compare-noprint" type="button">打印当前记录</button>
      <div class="compare-print-note" id="print-draft-text"></div>`);
    bindMedia(member.clip);
    bindHistory();
    reportSave();
    byId("print-draft").onclick = () => window.print();
    byId("observation").oninput = e => {draft.observation = e.target.value; save();};
    byId("lesson-form").onchange = e => {
      if (e.target.name === "verdict") {draft.verdict = e.target.value; save();}
    };
    byId("lesson-form").onsubmit = e => {
      e.preventDefault();
      const choice = new FormData(e.target).get("verdict");
      if (!answers.some(o=>o.id===choice)) return;
      a.picks.push({verdict:choice, observation:byId("observation").value});
      save();
      showLesson();
      focusTitle();
    };
  }
  function citedConclusion(text, quote) {
    const start = text.indexOf(quote);
    if (start < 0) return esc(text);
    return esc(text.slice(0,start)) + '<mark class="compare-quote">' + esc(quote) +
      '</mark>' + esc(text.slice(start + quote.length));
  }
  function source(c) {
    const date = String(c.source_date || "").replace(/^(\d{4})(\d{2})(\d{2})$/, "$1-$2-$3");
    const link = `season-${c.season}.html#case-${c.seq}`;
    return `<p class="compare-citation">中国足协 · ${esc(date)} · <a href="${esc(link)}">完整判例</a>
      <a href="${esc(c.source)}" target="_blank" rel="noopener noreferrer">足协原文 ↗</a>
      ${c.supplement ? ` · <a href="${esc(c.supplement.url)}" target="_blank" rel="noopener noreferrer">第 ${esc(c.supplement.issue)} 期补充认定 ↗</a>` : ""}</p>`;
  }
  function ruleLinks(rules) {
    return (rules || []).map(rule => `<a href="${esc(rule.href)}">${esc(rule.title)}（${esc(rule.version)}）</a>`).join(" · ");
  }
  function showReview() {
    const a = attempts.current;
    const panels = lesson.cases.map((member,i) => {
      const c = caseIndex()[member.id], pick = a.picks[i];
      const verdict = pick.verdict === insufficient ? "初判标记为画面不足" :
        pick.verdict === member.answer ? "与评议认定一致" : "与评议认定不同";
      return `<article id="panel-${letters[i].toLowerCase()}" class="compare-panel" data-print-panel>
        <p class="compare-kicker">案例 ${letters[i]} · ${esc(citation(c))}</p><h2>${esc(matchTitle(c))}</h2>
        <h3>我的初判</h3><p><strong>${esc(optionName(pick.verdict))}</strong> · ${verdict}</p>
        ${pick.observation ? `<p>${esc(pick.observation)}</p>` : ""}
        <h3>足协评议认定</h3><p>${citedConclusion(c.conclusion, member.quote)}</p>
        ${source(c)}</article>`;
    });
    shell(header(lesson.title,"双案复盘 · 两次初判已提交") +
      tabButtons() + `<div class="compare-grid">${panels.join("")}</div>
      <section class="compare-summary"><h2>两案的关键差异</h2><p class="compare-kicker">课程编写者的观察提示</p>
      <p>${esc(lesson.difference)}</p><p>现行规则参考 · ${ruleLinks(lesson.rules)}</p>
      <label class="compare-field">下次我会先看什么<textarea id="reflection" rows="4">${esc(a.reflection)}</textarea></label>
      <p class="compare-print-note" id="printed-reflection"></p></section>${statusBar()}
      <div class="compare-actions compare-noprint"><button type="button" id="print-review" class="compare-primary">打印复盘单</button>
      <button type="button" class="compare-secondary" id="coach-from-pair">用这两案新建课单</button>
      <button type="button" id="redo" class="compare-secondary">重新练习</button></div>${historyMenu()}`);
    setupTabs();
    reportSave();
    bindHistory();
    byId("reflection").oninput = e => {a.reflection = e.target.value; save();};
    byId("print-review").onclick = () => window.print();
    byId("coach-from-pair").onclick = () => coach.fromPair(lesson.cases.map(c=>c.id),lesson.title);
    byId("redo").onclick = () => {
      attempts.fresh(lesson.id);
      attempts.save();
      activeSide = 0;
      panelOffsets = [0,0];
      showLesson(); focusTitle();
    };
  }
  function tabButtons() {
    return '<div class="compare-tabs compare-noprint" role="tablist" aria-label="选择对读案例" hidden>' +
      letters.map((s,i)=>`<button id="side-${s.toLowerCase()}" type="button" role="tab" aria-selected="${i===activeSide}">案例 ${s}</button>`).join("") + "</div>";
  }
  function tabsForSize(printing=false) {
    const tabs = workspace.querySelector(".compare-tabs");
    if (!tabs) return;
    const single = mobile.matches && !printing;
    tabs.hidden = !single;
    letters.forEach((letter,i) => {
      const suffix = letter.toLowerCase(), tab = byId("side-"+suffix), panel = byId("panel-"+suffix);
      const selected = activeSide===i;
      tab.setAttribute("aria-selected",String(selected));
      tab.tabIndex = selected ? 0 : -1;
      panel.hidden = single && !selected;
      if (single) {
        panel.setAttribute("role","tabpanel");
        panel.setAttribute("aria-labelledby",tab.id);
      } else {
        panel.removeAttribute("role");
        panel.removeAttribute("aria-labelledby");
      }
    });
  }
  function setupTabs() {
    const tabs = workspace.querySelector(".compare-tabs");
    if (!tabs) return;
    function switchTo(i) {
      if (activeSide === i) return;
      const topOf = side => byId("panel-"+letters[side].toLowerCase()).getBoundingClientRect().top + window.scrollY;
      const inset = (document.querySelector(".topbar")?.offsetHeight || 0) + tabs.offsetHeight;
      const insidePanel = window.scrollY + inset >= topOf(activeSide) - 2;
      panelOffsets[activeSide] = Math.max(0, window.scrollY + inset - topOf(activeSide));
      stopMedia();
      activeSide = i;
      tabsForSize();
      if (insidePanel || panelOffsets[i]) window.scrollTo(0, topOf(i) - inset + panelOffsets[i]);
    }
    letters.forEach((s,i) => {
      const tab = byId("side-"+s.toLowerCase());
      tab.onclick = () => switchTo(i);
      tab.onkeydown = e => {
        const next = {ArrowLeft:1-i,ArrowRight:1-i,Home:0,End:1}[e.key];
        if (next == null) return;
        e.preventDefault();
        byId("side-"+letters[next].toLowerCase()).focus();
        switchTo(next);
      };
    });
    tabsForSize();
  }
  const picker = {category:"handball", season:["",""], filter:["",""], selected:["",""]};
  function showPicker(reason="") {
    if (reason) {
      history.replaceState(null, "", "#free");
      route = "free";
    }
    shell(header("自由配对","三赛季判例 · 自选两案") +
      `<p>在同一教学分类中选两场比赛，对读事件经过和足协原文。</p>
      ${reason ? `<p class="compare-status" role="alert">${esc(reason)}</p>` : ""}
      <label class="compare-field">教学分类<select id="pick-category"></select></label>
      <div class="compare-grid">${letters.map(s=>`<section class="compare-panel"><h2>选择案例 ${s}</h2>
      <label class="compare-field">赛季<select id="season-${s.toLowerCase()}"><option value="">全部赛季</option></select></label>
      <label class="compare-field">搜索球队或期次<input id="filter-${s.toLowerCase()}" type="search" placeholder="球队名或第 3 期"></label>
      <label class="compare-field">判例<select id="pick-${s.toLowerCase()}"></select></label></section>`).join("")}</div>
      <div class="compare-actions"><button id="open-pair" type="button" class="compare-primary">开始对读</button>
      <span id="pick-status" role="status"></span></div>`);
    const category = byId("pick-category");
    for (const [id,label] of Object.entries(data.categories)) category.add(new Option(label,id));
    category.value = picker.category;
    const seasons = [...new Set(Object.values(caseIndex()).map(c=>String(c.season)))].sort().reverse();
    function validate() {
      const [a,b] = picker.selected;
      byId("open-pair").disabled = !a || !b || a===b;
      byId("pick-status").textContent = a && b && a===b ? "请选择两个不同的判例。" : "";
    }
    function fill(i) {
      const key = letters[i].toLowerCase(), select = byId("pick-"+key);
      select.replaceChildren(new Option("请选择判例",""));
      for (const [id,c] of Object.entries(caseIndex())) {
        if (c.category !== picker.category || (picker.season[i] && String(c.season)!==picker.season[i])) continue;
        const label = `${citation(c)} · ${matchTitle(c)}`;
        const term = picker.filter[i].replace(/\s+/g,"").toLowerCase();
        const haystack = `${label} ${c.comp} ${id}`.replace(/\s+/g,"").toLowerCase();
        if (term && !haystack.includes(term)) continue;
        select.add(new Option(label,id));
      }
      select.value = picker.selected[i];
      picker.selected[i] = select.value;
      if (select.options.length===1) select.options[0].text = "没有匹配判例";
      validate();
    }
    category.onchange = () => {
      picker.category = category.value;
      picker.selected = ["",""];
      fill(0); fill(1);
    };
    letters.forEach((s,i) => {
      const key = s.toLowerCase(), year = byId("season-"+key), filter = byId("filter-"+key);
      seasons.forEach(v=>year.add(new Option(v,v)));
      year.value = picker.season[i];
      filter.value = picker.filter[i];
      year.onchange = () => {picker.season[i]=year.value; fill(i);};
      filter.oninput = () => {picker.filter[i]=filter.value; fill(i);};
      byId("pick-"+key).onchange = e => {picker.selected[i]=e.target.value; validate();};
      fill(i);
    });
    byId("open-pair").onclick = () => {location.hash = "pair-"+picker.selected.join("~");};
  }
  function showPair(ids) {
    const cs = ids.map(id=>caseIndex()[id]);
    if (cs.some(c=>!c)) {showPicker("链接中的判例不存在，请重新选择。"); return;}
    if (ids[0] === ids[1]) {showPicker("链接中的两个判例相同，请另选一例。"); return;}
    if (cs[0].category !== cs[1].category) {showPicker("两案属于不同教学分类，请从同一分类重新选择。"); return;}
    selectedPair = ids;
    picker.category = cs[0].category;
    picker.selected = ids.slice();
    picker.filter = ["",""];
    picker.season = ["",""];
    const panels = cs.map((c,i) => `<article id="panel-${letters[i].toLowerCase()}" data-print-panel class="compare-panel">
      <p class="compare-kicker">案例 ${letters[i]} · ${esc(citation(c))}</p><h2>${esc(matchTitle(c))}</h2>
      <h3>比赛事件</h3><p>${esc(c.desc || "来源未提供事件描述。")}</p>${mediaBox(c)}
      <h3>足协评议认定</h3><p>${esc(c.conclusion || "未单列评议结论，可查当期足协原文。")}</p>${source(c)}</article>`);
    shell(header(data.categories[cs[0].category]+" · 双案对读","自由配对","#free","重新选案") +
      `<div class="compare-actions compare-noprint"><button class="compare-secondary" id="swap-pair" type="button">交换两案</button>
      <button type="button" class="compare-secondary" id="coach-from-pair">用这两案新建课单</button>
      <button id="print-review" type="button" class="compare-secondary">打印对照单</button></div>`+
      tabButtons()+`<div class="compare-grid">${panels.join("")}</div>
      <section class="compare-summary"><h2>现行规则参考</h2><p>${ruleLinks(data.rulesByCategory[cs[0].category])}</p></section>`);
    bindMedia();
    setupTabs();
    byId("coach-from-pair").onclick = () => coach.fromPair(ids,data.categories[cs[0].category]+"对照课");
    byId("swap-pair").onclick = () => {location.hash = "pair-"+[...ids].reverse().join("~");};
    byId("print-review").onclick = () => window.print();
  }
  function focusTitle() {
    const h = byId("compare-title");
    if (h) {
      h.focus({preventScroll:true});
      window.scrollTo(0,0);
    }
  }
  function renderRoute() {
    const hash = location.hash.slice(1);
    if (hash === "main") return;
    coach.leave();
    stopMedia();
    const previous = route;
    route = hash;
    activeSide = 0;
    panelOffsets = [0,0];
    const entry = !hash;
    document.querySelectorAll("[data-compare-entry]").forEach(el => {el.hidden = !entry;});
    workspace.hidden = entry;
    document.documentElement.toggleAttribute("data-compare-work",!entry);
    // Unmounted work cannot contribute printable private notes or focusable controls.
    if (entry) {
      lesson = null; workspace.replaceChildren();
      if (previous && lastFocus?.isConnected) lastFocus.focus();
      return;
    }
    if (hash === "free") {lesson=null; showPicker();}
    else if (coach.handles(hash)) {lesson=null; coach.open(hash);}
    else if (hash.startsWith("lesson-")) {
      lesson = data.lessons.find(l=>l.id === hash.slice(7));
      if (lesson) { attempts.start(lesson.id); showLesson(); }
      else showPicker("课程链接已失效，请重新选案。");
    } else {
      lesson = null;
      const m = /^pair-(\d{4}-\d+)~(\d{4}-\d+)$/.exec(hash);
      if (m) showPair(m.slice(1));
      else showPicker("无法识别这个配对链接，请重新选择。");
    }
    focusTitle();
  }
  document.addEventListener("click", e => {
    const a = e.target.closest("a[href]");
    if (!a) return;
    if (a.getAttribute("href")==="#main") {
      // Keep the lesson's permalink while using the skip link.
      e.preventDefault();
      (workspace.hidden ? byId("main") : byId("compare-title"))?.focus();
    } else if (a.closest("[data-compare-entry]")) lastFocus = a;
  });
  window.addEventListener("hashchange",renderRoute);
  window.addEventListener("pagehide",stopMedia);
  window.addEventListener("beforeunload", e => {
    if (attempts.store.pending.size || coach.hasPending()) {e.preventDefault(); e.returnValue = "";}
  });
  window.addEventListener("storage", e => {
    if (!e.key || e.key.startsWith("cfa.coach.")) coach.storageChanged();
    if (!e.key?.startsWith("cfa.compare.") || !lesson) return;
    // Keep the form being edited. New records can be selected without a reload.
    const menu = byId("history-attempt");
    if (menu && document.activeElement !== menu) {
      const currentId = attempts.current?.id;
      menu.parentElement.outerHTML = historyMenu();
      bindHistory();
      const next = byId("history-attempt");
      if (next && [...next.options].some(o=>o.value===currentId)) next.value = currentId;
    }
  });
  mobile.addEventListener("change", () => {stopMedia(); tabsForSize();});
  window.addEventListener("beforeprint", () => {
    tabsForSize(true);
    if (byId("printed-reflection")) byId("printed-reflection").textContent = "我的复盘：" + (attempts.current.reflection || "未填写");
    if (byId("print-draft-text") && lesson) {
      const a = attempts.current;
      byId("print-draft-text").textContent = lesson.cases.map((item,i) => {
        const p = a.picks[i] || a.drafts[i];
        return `案例 ${letters[i]} · ${matchTitle(caseIndex()[item.id])}：${optionName(p.verdict || "尚未选择")}。${p.observation || ""}`;
      }).join("\n");
    }
  });
  window.addEventListener("afterprint",()=>tabsForSize());
  document.addEventListener("cfa:lite",()=>{
    coach.updateMedia();
    if (lesson) showLesson(); else if (route.startsWith("pair-") && selectedPair.length) showPair(selectedPair);
  });
  const coach = createCoachWorkspace({caseIndex,data,workspace,esc,matchTitle,citation,mediaBox,bindMedia,stopMedia,source,ruleLinks,shareURL:shareAddress});
  renderRoute();
})();
