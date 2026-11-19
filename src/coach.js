function createCoachWorkspace(api) {
  const {caseIndex, data, workspace, esc, matchTitle, citation, mediaBox, bindMedia, stopMedia, source, ruleLinks} = api;
  const byId = id => document.getElementById(id);
  let model, catalog, active = null, mode = "", review = false, stage = null;
  let conflictMessage = "";
  const pending = new Map();
  const filters = {category:"", year:"", query:"", pick:"2026-1"};
  const entryFooter = document.querySelector("footer[data-compare-entry]");
  const entryPhoto = entryFooter.querySelector(".compare-ref-photo");
  const photoHome = entryPhoto.parentElement;
  const pickerPictures = new Map(["2026-1","2026-28"].map((id,i) =>
    [id, document.querySelectorAll(".preview-side picture")[i]]));
  let planner = null;
  const curated = new Map(data.lessons.flatMap(l => l.cases.map(c => [c.id,c])));
  const keyLast = "cfa.coach.last.v1";
  const defaultQuestion = "你观察到了什么？哪些细节支持你的判断？";
  function initialize() {
    if (model) return;
    catalog = caseIndex();
    model = new CoachModel(catalog, data.lessons, data.rulesByCategory);
  }
  function setMode(next) {
    mode = next;
    if (mode) document.documentElement.dataset.coachView = mode;
    else delete document.documentElement.dataset.coachView;
  }
  function mount(content, classes="") {
    stopMedia();
    workspace.innerHTML = `<div class="coach-shell ${classes}">${content}</div>`;
  }
  function remember(id) {try {sessionStorage.setItem(keyLast,id);} catch (_) {}}
  function savedId() {try {return sessionStorage.getItem(keyLast);} catch (_) {return null;}}
  function plans() {
    const saved = model.list();
    // Another tab can finish a simultaneous save after our write returned.
    // Reconcile by immutable revision so both menu entries still open their own lesson.
    const live = active?.revision && saved.find(p=>p.revision===active.revision);
    if (live && live.id !== active.id) {
      const old = active.id;
      active.id = live.id;
      if (pending.delete(old)) pending.set(live.id,active);
      remember(live.id);
    }
    const entries = new Map(saved.map(p => [p.id,p]));
    for (const [id,p] of pending) entries.set(id,p);
    if (active) entries.set(active.id,active);
    return [...entries.values()];
  }
  function currentPlan(id) {
    if (active && active.id===id) return active;
    return pending.get(id) || model.list().find(p=>p.id===id);
  }
  function choose(p) {
    active = p;
    review = false;
    conflictMessage = "";
    remember(p.id);
  }
  function titleOf(p) {return p.title.trim() || "未命名课单";}
  function say(text) {
    for (const id of ["coach-status","coach-dialog-status"]) {
      const node = byId(id);
      if (node) node.textContent = text;
    }
  }
  function syncStatus(message="") {
    const failed = active && pending.has(active.id);
    const retry = byId("coach-retry");
    if (retry) retry.hidden = !failed;
    say([message,conflictMessage,failed ? "本页保留草稿，可重试保存或导出教练备份。" :
      active?.revision ? "已保存到本机" : ""].filter(Boolean).join("　"));
  }
  function persist() {
    const old = active.id;
    try {
      const result = model.save(active);
      active = result.lesson;
      if (result.conflict) conflictMessage = "其他窗口也编辑了这堂课，本次修改已保留为独立课单。";
      pending.delete(old);
      if (!result.ok) pending.set(active.id,active);
      remember(active.id);
      refreshList();
      syncStatus(result.ok ? "" : result.error || "保存失败");
      return result.ok;
    } catch (err) {
      pending.set(old,active);
      syncStatus(err.message);
      return false;
    }
  }
  function refreshList() {
    const select = byId("coach-choose");
    if (!select) return;
    const items = plans();
    const frag = document.createDocumentFragment();
    for (const p of items) frag.append(new Option(`${titleOf(p)}（${p.items.length} 例）`,p.id));
    select.replaceChildren(frag);
    select.value = active.id;
    byId("coach-current").textContent = titleOf(active) + " · " + active.items.length + " 例";
  }
  function field(name, label, item, placeholder, limit) {
    return `<label class="coach-field">${label}<textarea data-field="${name}" rows="2" maxlength="${limit}" placeholder="${esc(placeholder)}">${esc(item[name] || "")}</textarea></label>`;
  }
  function itemHTML(item,i) {
    const c = catalog[item.caseId];
    return `<li class="coach-item" data-coach-case="${esc(item.caseId)}">
      <div class="coach-item-head"><div><p class="coach-count">第 ${i+1} 案 · ${esc(citation(c))}</p>
      <h3 tabindex="-1">${esc(matchTitle(c))}</h3></div><div class="coach-item-tools">
      <button type="button" data-action="up" aria-label="上移第 ${i+1} 案" ${i===0 ? "disabled" : ""}>上移</button>
      <button type="button" data-action="down" aria-label="下移第 ${i+1} 案" ${i===active.items.length-1 ? "disabled" : ""}>下移</button>
      <button type="button" data-action="remove" aria-label="移除第 ${i+1} 案">移除</button></div></div>
      ${field("question","讨论问题",item,defaultQuestion,CoachModel.limits.question)}
      <details class="coach-item-details"><summary>编辑情境和教练备注</summary>
      ${field("scenario","学员可见的情境",item,curated.get(item.caseId)?.prompt || "写下一段适合讨论的比赛情境",CoachModel.limits.scenario)}
      ${field("note","教练私人备注",item,"仅备课时显示，可记下追问或教学安排",CoachModel.limits.note)}
      <details><summary>核对足协认定</summary><p>${esc(c.conclusion || "本例未单列评议认定。")}</p>${source(c)}</details></details></li>`;
  }
  function filterResults() {
    const select = byId("coach-pick");
    const q = filters.query.replace(/\s+/g,"").toLowerCase();
    const previous = filters.pick;
    const options = document.createDocumentFragment();
    let count = 0, first = "";
    for (const [id,c] of Object.entries(catalog)) {
      if (filters.category && c.category !== filters.category) continue;
      if (filters.year && String(c.season)!==filters.year) continue;
      const label = `${citation(c)} · ${matchTitle(c)}`;
      if (q && !`${id} ${label} ${c.comp} ${data.categories[c.category]}`.replace(/\s+/g,"").toLowerCase().includes(q)) continue;
      options.append(new Option(label,id));
      if (!first) first = id;
      count++;
    }
    select.replaceChildren(options);
    if (!count) select.add(new Option("没有匹配判例",""));
    select.value = previous;
    if (!select.value) select.value = first;
    filters.pick = select.value;
    byId("coach-result-count").textContent = `匹配 ${count} 例`;
    select.disabled = !count;
    updateAdd();
    updatePreview();
  }
  function updatePreview() {
    const c = catalog[filters.pick], picture = pickerPictures.get(filters.pick);
    const preview = byId("coach-case-preview");
    byId("coach-match").textContent = c ? matchTitle(c) : "没有匹配的判例";
    byId("coach-citation").textContent = c ? citation(c) : "可更换赛季、教学分类或搜索词。";
    const visual = byId("coach-match-visual");
    if (picture) {
      if (visual.dataset.case !== filters.pick) {
        // The picker uses a wide single frame, including on phones. The paired
        // lesson view uses portrait crops when two cases share its narrow screen.
        const image = picture.querySelector("img").cloneNode();
        visual.replaceChildren(image);
      }
    } else {
      const text = document.createElement("p");
      text.textContent = c ? c.desc || "本期未单列比赛事件。" : "请调整筛选条件。";
      visual.replaceChildren(text);
    }
    visual.dataset.case = filters.pick;
    if (preview.open) preview.lastElementChild.innerHTML =
      c ? "<p>"+esc(c.desc || "本期未单列事件描述。")+"</p>"+source(c) : "<p>请先选择一个判例。</p>";
  }

  function updateAdd() {
    const added = active.items.some(i=>i.caseId===filters.pick);
    const btn = byId("coach-add");
    btn.disabled = !filters.pick || added;
    btn.textContent = added ? "已在课单中" : "加入课单";
  }
  function setupPicker() {
    const cat = byId("coach-category"), year = byId("coach-year"), query = byId("coach-filter");
    for (const [id,label] of Object.entries(data.categories)) cat.add(new Option(label,id));
    const years = [...new Set(Object.values(catalog).map(c=>String(c.season)))].sort().reverse();
    for (const y of years) year.add(new Option(y,y));
    cat.value=filters.category; year.value=filters.year; query.value=filters.query;
    cat.onchange = () => {filters.category=cat.value;filterResults();};
    year.onchange = () => {filters.year=year.value;filterResults();};
    query.oninput = () => {filters.query=query.value;filterResults();};
    byId("coach-pick").onchange = e => {filters.pick=e.target.value;updateAdd();updatePreview();};
    const preview = byId("coach-case-preview");
    preview.ontoggle = updatePreview;
    preview.onkeydown = event => {
      if (event.key !== "Escape" || !preview.open) return;
      event.preventDefault();
      preview.open = false;
      preview.querySelector("summary").focus();
    };
    filterResults();
  }
  function download(text,mime,name) {
    const url = URL.createObjectURL(new Blob([text],{type:mime}));
    const a = document.createElement("a");
    a.href=url; a.download=name; document.body.append(a); a.click(); a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),30000);
  }
  function safeName(title) {
    return (title.trim().replace(/[<>:"/\\|?*\u0000-\u001f]/g,"_").slice(0,80).replace(/[. ]+$/,"") || "未命名课单");
  }
  function studentURL(hash) {
    const url = api.shareURL();
    url.hash = hash;
    return url.href;
  }
  async function shareLink() {
    const url = studentURL(model.encodeShare(active,{review}));
    try {await navigator.clipboard.writeText(url);syncStatus("已复制学员链接");}
    catch (_) {
      if (!byId("coach-share-label")) return;
      byId("coach-share-label").hidden=false;
      const input = byId("coach-share-text");
      input.value=url; input.focus(); input.select();syncStatus("请复制选中的学员链接");
    }
  }
  function act(fn) {
    return async e => {
      try {await fn(e);}
      catch (err) {syncStatus(err.message);}
    };
  }
  let removed = null;
  function clearShare() {
    const field = byId("coach-share-text");
    if (field) {field.value = ""; byId("coach-share-label").hidden = true;}
  }
  function renderQueue() {
    const list = byId("coach-items");
    const expanded = new Set([...list.querySelectorAll(".coach-item-details[open]")].map(el=>el.closest("li").dataset.coachCase));
    list.innerHTML = active.items.map(itemHTML).join("");
    for (const el of list.children) if (expanded.has(el.dataset.coachCase)) el.querySelector(".coach-item-details").open = true;
    byId("coach-empty").hidden = Boolean(active.items.length);
    byId("coach-undo").hidden = !removed;
    byId("coach-length").textContent = active.items.length ? `已选 ${active.items.length} 例，可编辑问题与授课顺序。` : "课单中还没有判例。";
    for (const id of ["coach-present","coach-preview","coach-download","coach-link","coach-review"]) byId(id).disabled = !active.items.length;
    clearShare();
    updateAdd();
  }
  function editOrder(button) {
    const id = button.closest("li").dataset.coachCase;
    const index = active.items.findIndex(i=>i.caseId===id);
    if (index < 0) return;
    const action = button.dataset.action;
    const to = action === "up" ? index-1 : index+1;
    if (action === "remove") {
      removed = {index, item:active.items.splice(index,1)[0]};
    } else {
      if (to<0 || to>=active.items.length) return;
      [active.items[index],active.items[to]] = [active.items[to],active.items[index]];
    }
    persist(); renderQueue();
    const count = active.items.length;
    if (count) byId("coach-items").children[action === "remove" ? Math.min(index,count-1) : to].querySelector("h3").focus();
    else byId("coach-undo").focus();
    syncStatus(action === "remove" ? "已移除判例，可撤销本次移除。" : `已移到第 ${to+1} 案。`);
  }
  function showEditor() {
    setMode("editor");
    if (!active) {
      const available = model.list();
      choose(available.find(p=>p.id===savedId()) || available[0] || model.create());
    }
    closeEditorLayout();
    const fragment = byId("coach-editor-layout").content.cloneNode(true);
    workspace.parentElement.prepend(workspace);
    workspace.className="hero hero--centred compare-hero coach-picker-page";
    workspace.dataset.enter="rise";
    workspace.setAttribute("aria-labelledby","compare-title");
    workspace.replaceChildren(fragment.querySelector(".wrap"));
    planner = fragment.querySelector("footer");
    planner.querySelector(".compare-catalog").append(entryPhoto);
    planner.append(...fragment.querySelectorAll("dialog"));
    entryFooter.before(planner);

    byId("coach-case-total").textContent=String(data.caseCount);
    byId("coach-title").value=active.title;
    byId("coach-title").maxLength=CoachModel.limits.title;
    byId("coach-review").checked=review;
    byId("coach-arrange").onclick = e => {
      e.preventDefault();
      planner.scrollIntoView({block:"start"});
      byId("coach-plan-heading").focus({preventScroll:true});
    };
    for (const [buttonId,dialogId] of [["coach-edit-items","coach-outline-dialog"],["coach-tools-open","coach-tools-dialog"]]) {
      const button=byId(buttonId), dialog=byId(dialogId);
      button.onclick=()=>dialog.showModal();
      dialog.querySelector("[data-coach-close]").onclick=()=>dialog.close();
    }
    setupPicker(); refreshList(); renderQueue(); syncStatus(model.storageError || "");
    byId("coach-choose").onchange = e => {
      const p = currentPlan(e.target.value);
      if (p) {choose(p); removed=null; showEditor(); byId("coach-choose").focus({preventScroll:true});}
    };
    byId("coach-new").onclick = () => {
      choose(model.create()); removed=null; persist(); showEditor(); byId("coach-title").select(); byId("coach-title").focus();
    };
    byId("coach-title").oninput = e => {active.title=e.target.value; clearShare(); persist();};
    byId("coach-add").onclick = () => {
      const id = filters.pick;
      if (!catalog[id] || active.items.some(i=>i.caseId===id)) return;
      active.items.push({caseId:id,question:"",scenario:"",note:""});
      if (removed?.item.caseId === id) removed = null;
      persist(); renderQueue(); syncStatus(`已加入第 ${active.items.length} 案。`);
    };
    byId("coach-items").onclick = e => {const btn=e.target.closest("button[data-action]"); if (btn) editOrder(btn);};
    byId("coach-items").oninput = e => {
      const control = e.target;
      if (!control.matches("textarea[data-field]")) return;
      const item = active.items.find(i=>i.caseId===control.closest("li").dataset.coachCase);
      item[control.dataset.field] = control.value;
      clearShare(); persist();
    };
    byId("coach-undo").onclick = () => {
      if (!removed) return;
      active.items.splice(Math.min(active.items.length,removed.index),0,removed.item);
      removed=null; persist(); renderQueue(); syncStatus("已恢复判例和备注。");
    };
    byId("coach-retry").onclick = () => persist();
    byId("coach-backup").onclick = act(() => {
      download(model.backup(active),"application/json",safeName(titleOf(active))+"-教练备份.json");
      syncStatus("已生成包含私人备注的教练备份。");
    });
    byId("coach-import").onchange = act(async e => {
      const input=e.target, file=input.files[0]; input.value="";
      if (!file) return;
      const result = model.importBackup(await file.text());
      choose(result.lesson); removed=null;
      if (!result.ok) pending.set(active.id,active);
      showEditor(); syncStatus(result.ok ? "已将备份导入为独立课单。" : result.error);
    });
    byId("coach-review").onchange = e => {review=e.target.checked;clearShare();};
    byId("coach-present").onclick = () => {location.hash="present-"+active.id;};
    byId("coach-preview").onclick = () => {location.hash=`preview-${review ? "review" : "discuss"}-${active.id}`;};
    byId("coach-download").onclick = act(() => {
      download(model.handout(active,{review}),"text/html;charset=utf-8",safeName(titleOf(active))+(review ? "-复盘讲义.html" : "-讨论讲义.html"));
      syncStatus("已生成学员讲义。");
    });
    byId("coach-link").onclick = act(shareLink);
  }
  function beginStage(id) {
    const p = currentPlan(id);
    if (!p || !p.items.length) throw Error("这份投屏课单在当前设备上找不到。请先打开本机课单，或导入教练备份。");
    active = p; remember(p.id);
    stage = {plan:p, handout:model.student(p), at:0, revealed:false};
    setMode("present"); drawStage();
  }
  function move(to) {
    if (!stage || to < 0 || to >= stage.plan.items.length || to === stage.at) return;
    stage.at = to; stage.revealed = false; drawStage(true);
  }
  function revealAnswer() {
    stage.revealed = !stage.revealed;
    drawStage();
    byId("stage-reveal").focus({preventScroll:true});
  }
  function drawStage(focus=false) {
    const {plan,at,revealed,handout} = stage;
    const item = handout.items[at], c = catalog[item.caseId];
    const clip = curated.get(item.caseId)?.clip;
    const hasVideo = c.video_files?.length || c.video_urls?.length;
    const media = clip || !hasVideo ? mediaBox(c,clip) :
      `<details><summary>完整判例视频（可能包含临场判罚）</summary>${mediaBox(c)}</details>`;
    mount(`<header class="coach-head"><p class="coach-count">${esc(titleOf(plan))} · 第 ${at+1} / ${handout.items.length} 案</p>
      <h1 id="compare-title" tabindex="-1">${esc(item.match)}</h1><p>${esc(item.citation)}</p></header>
      <section class="coach-content"><p class="coach-handout-text">${esc(item.prompt)}</p>
      <h2 class="coach-handout-text">${esc(item.question)}</h2>${media}
      ${revealed ? `<section class="coach-answer"><h3>足协评议认定</h3><p>${esc(c.conclusion || "来源未单列评议认定。")}</p>${source(c)}
      <p>现行规则参考 · ${ruleLinks(data.rulesByCategory[c.category])}</p></section>` : ""}</section>
      <div class="coach-actions"><button type="button" id="stage-prev" ${at===0 ? "disabled" : ""}>上一案</button>
      <button type="button" class="coach-primary" id="stage-reveal" aria-pressed="${revealed}">${revealed ? "收起认定" : "揭晓足协认定"}</button>
      <button type="button" id="stage-next" ${at===handout.items.length-1 ? "disabled" : ""}>下一案</button>
      <button type="button" id="stage-fullscreen">${document.fullscreenElement ? "退出全屏" : "全屏投影"}</button>
      <a class="coach-secondary" id="stage-exit" href="#coach">结束投屏</a></div><p class="coach-keys">键盘 ← → 切换判例，R 揭晓或收起认定。</p><p id="coach-status" role="status"></p>`,"coach-stage");
    bindMedia(clip);
    byId("stage-prev").onclick = () => move(at-1);
    byId("stage-next").onclick = () => move(at+1);
    byId("stage-reveal").onclick = revealAnswer;
    byId("stage-fullscreen").onclick = async () => {
      try {
        if (document.fullscreenElement) await document.exitFullscreen();
        else await workspace.requestFullscreen();
      } catch (_) {say("浏览器未启用全屏，可继续用当前投屏视图授课。");}
    };
    if (focus) {
      byId("compare-title").focus({preventScroll:true});
      workspace.scrollTop=0; window.scrollTo(0,0);
    }
  }
  function showStudent(sheet,preview) {
    setMode("student"); stopMedia();
    workspace.innerHTML = `<div class="coach-shell coach-toolbar compare-noprint">
      <a href="${preview ? "#coach" : "#"}">${preview ? "← 返回备课" : "尺度对照课"}</a>
      <button type="button" id="coach-sheet-print">打印讲义</button>
      <button type="button" id="coach-sheet-save">下载离线讲义</button></div>
      <article class="coach-shell coach-handout" id="coach-sheet">${model.sheetBody(sheet)}</article>`;
    const heading = byId("coach-sheet").querySelector("h1");
    heading.id="compare-title"; heading.tabIndex=-1;
    byId("coach-sheet-print").onclick = () => window.print();
    byId("coach-sheet-save").onclick = () => download(model.sheetHTML(sheet),"text/html;charset=utf-8",
      safeName(sheet.title)+(sheet.review ? "-复盘讲义.html" : "-讨论讲义.html"));
  }
  function handles(hash) {
    return hash === "coach" || hash === "coach-plan" || /^(present-|preview-|handout-)/.test(hash);
  }
  function open(hash) {
    try {
      initialize();
      if (hash === "coach" || hash === "coach-plan") {
        showEditor();
        if (hash === "coach-plan") requestAnimationFrame(() => byId("coach-arrange")?.click());
      }
      else if (hash.startsWith("present-")) beginStage(hash.slice(8));
      else if (hash.startsWith("handout-")) showStudent(model.decodeShare("#"+hash),false);
      else {
        const m = /^preview-(review|discuss)-(.+)$/.exec(hash), p = m && currentPlan(m[2]);
        if (!p) throw Error("这份本机讲义预览已失效。学员可使用教练分享的讲义链接或 HTML 文件。");
        showStudent(model.student(p,{review:m[1]==="review"}),true);
      }
    } catch (error) {
      setMode("student");
      mount(`<h1 id="compare-title" tabindex="-1">无法打开这份课单</h1><p role="alert">${esc(error.message)}</p>
        <div class="coach-actions"><a href="#coach">返回备课</a><a href="#">课程目录</a></div>`);
    }
  }
  function closeEditorLayout() {
    if (!planner) return;
    for (const dialog of planner.querySelectorAll("dialog[open]")) dialog.close();
    photoHome.append(entryPhoto);
    planner.remove(); planner=null;
    workspace.className="";
    delete workspace.dataset.enter;
    workspace.removeAttribute("aria-labelledby");
    workspace.parentElement.append(workspace);
  }
  function leave() {
    closeEditorLayout();
    if (mode === "present" && document.fullscreenElement === workspace) document.exitFullscreen().catch(()=>{});
    setMode(""); stage=null;
  }
  function fromPair(ids,title) {
    initialize(); choose(model.create(title)); removed=null;
    active.items=ids.map(caseId=>({caseId,question:"",scenario:"",note:""}));
    persist(); location.hash="coach";
  }
  document.addEventListener("fullscreenchange",() => {
    const button=byId("stage-fullscreen");
    if (button) button.textContent = document.fullscreenElement ? "退出全屏" : "全屏投影";
  });
  document.addEventListener("keydown",e => {
    if (mode !== "present" || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey || e.defaultPrevented ||
        e.target.closest?.("input,textarea,select,video,[contenteditable=true]")) return;
    if (e.key==="ArrowRight") move(stage.at+1);
    else if (e.key==="ArrowLeft") move(stage.at-1);
    else if (e.key==="Home") move(0);
    else if (e.key==="End") move(stage.handout.items.length-1);
    else if (e.key.toLowerCase()==="r") revealAnswer();
    else if (e.key==="Escape" && !document.fullscreenElement) location.hash="coach";
    else return;
    e.preventDefault();
  });
  window.addEventListener("beforeprint",() => {
    if (!(mode==="editor" || mode==="present") || !active?.items.length) return;
    byId("coach-print")?.remove();
    const paper=document.createElement("article");
    paper.id="coach-print"; paper.className="coach-handout";
    paper.innerHTML=model.sheetBody(model.student(active,{review:mode==="editor" && review}));
    workspace.append(paper);
  });
  window.addEventListener("afterprint",()=>byId("coach-print")?.remove());
  return {handles,open,leave,fromPair,hasPending:()=>Boolean(pending.size),
    storageChanged:()=>{if(mode==="editor") refreshList();},
    updateMedia:()=>{if(mode==="present") drawStage();}};
}
