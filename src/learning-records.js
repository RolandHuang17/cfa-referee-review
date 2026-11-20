// Each edit writes one independent key before replacing its observed predecessor.
// Two tabs editing the same base create two surviving versions, even without Web Locks.
class LearningRecords {
  constructor(key, notes = false, listKey = null) {
    this.key = key;
    this.prefix = key + ".entry.";
    this.notes = notes;
    this.listKey = listKey;
    this.pending = new Map();
    this.records = Object.create(null);
    this.versions = new Map();
    this.obsolete = new Map();
    this.unreadable = new Map();
    this.readFailed = false;
  }
  validValue(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    return !this.notes || (typeof value.text === "string" &&
      (value.conflicts === undefined || (Array.isArray(value.conflicts) &&
        value.conflicts.every(copy => copy && typeof copy.text === "string"))));
  }
  scan() {
    const unreadable = new Map();
    const records = Object.create(null);
    const aggregate = localStorage.getItem(this.key);
    if (aggregate !== null) {
      try {
        const raw = JSON.parse(aggregate);
        if (!raw || typeof raw !== "object" || Array.isArray(raw) !== !!this.listKey)
          throw Error("旧存储格式异常");
        for (const [id, value] of Object.entries(raw)) {
          if (!this.validValue(value)) { unreadable.set(this.key, aggregate); continue; }
          records[this.listKey ? this.listKey(value) : id] = value;
        }
      } catch (_) { unreadable.set(this.key, aggregate); }
    }
    const versions = new Map();
    for (const name of Object.keys(localStorage)) {
      if (!name.startsWith(this.prefix)) continue;
      const raw = localStorage.getItem(name);
      if (raw === null) continue; // Another tab compacted this version during the scan.
      let entry;
      try {
        entry = JSON.parse(raw);
        if (!entry || typeof entry.id !== "string" || !Number.isFinite(entry.at) ||
            !(entry.value === null || this.validValue(entry.value))) throw Error("版本内容异常");
        const idPrefix = this.prefix + encodeURIComponent(entry.id) + ".";
        if (!name.startsWith(idPrefix) || !Array.isArray(entry.parents) ||
            !entry.parents.every(parent => typeof parent === "string" && parent.startsWith(idPrefix) && parent !== name))
          throw Error("版本关系异常");
      } catch (_) { unreadable.set(name, raw); continue; }
      const items = versions.get(entry.id) || [];
      items.push({...entry, name});
      versions.set(entry.id, items);
    }
    const obsolete = new Map();
    for (const [id, candidates] of versions) {
      // A second tab can observe the new version before its parent keys are removed.
      const superseded = new Set(candidates.flatMap(entry => entry.parents || []));
      obsolete.set(id, candidates.filter(entry => superseded.has(entry.name)).map(entry => entry.name));
      const items = candidates.filter(entry => !superseded.has(entry.name));
      versions.set(id, items);
      items.sort((a, b) => b.at - a.at || b.name.localeCompare(a.name));
      const values = items.map(item => item.value);
      const primary = this.notes ? values.find(value => value && (value.text || value.conflicts?.length)) : values[0];
      if (!primary) { delete records[id]; continue; }
      if (!this.notes) { records[id] = primary; continue; }
      const alternatives = new Map();
      for (const v of values.filter(Boolean)) {
        for (const copy of [v, ...(v.conflicts || [])]) {
          if (copy.text && copy.text !== primary.text) alternatives.set(copy.text, {text: copy.text, ts: copy.ts});
        }
      }
      records[id] = {...primary};
      if (alternatives.size) records[id].conflicts = [...alternatives.values()];
      else delete records[id].conflicts;
    }
    this.unreadable = unreadable;
    this.readFailed = false;
    this.obsolete = obsolete;
    this.versions = versions;
    this.records = records;
  }
  read() {
    try { this.scan(); } catch (_) { this.readFailed = true; }
    const out = Object.assign(Object.create(null), this.records);
    for (const [id, op] of this.pending) {
      if (op.value) out[id] = op.value;
      else delete out[id];
    }
    return out;
  }
  base(id, all = false) {
    const versions = this.versions.get(String(id)) || [];
    if (!this.notes || all) return versions.map(v => v.name);
    const primary = versions.find(v => v.value && v.value.text) || versions[0];
    return primary ? [primary.name] : [];
  }
  put(id, value, parents) {
    id = String(id);
    const prior = this.pending.get(id);
    const nonce = Array.from(crypto.getRandomValues(new Uint32Array(3)), n => n.toString(36)).join("-");
    const name = this.prefix + encodeURIComponent(id) + "." + nonce;
    this.lastWriteName = name;
    const replaced = prior?.stored ? [...parents, prior.name] : prior ? prior.parents : parents;
    this.pending.set(id, {name, value, parents: replaced, at: Date.now()});
    return this.commit(id);
  }
  commit(id) {
    const op = this.pending.get(id);
    if (!op) return true;
    try {
      this.scan();
      if (!op.stored) {
        // Carry forward physically surviving parents if a previous tab stopped during cleanup.
        op.parents = [...new Set([...op.parents, ...(this.obsolete.get(id) || [])])];
        localStorage.setItem(op.name, JSON.stringify({id, at: op.at, value: op.value, parents: op.parents}));
        op.stored = true;
      }
      for (const old of op.parents) if (!this.unreadable.has(old)) localStorage.removeItem(old);
      this.scan();
      // Preserve the original aggregate key for older pages and backup readers.
      // If the old snapshot is damaged it is also the owner's raw recovery copy.
      if (!this.unreadable.has(this.key))
        localStorage.setItem(this.key, JSON.stringify(this.listKey ? Object.values(this.records) : this.records));
      this.pending.delete(id);
      return true;
    } catch (_) { return false; }
  }
  retry() {
    for (const id of [...this.pending.keys()]) this.commit(id);
    return !this.pending.size;
  }
}

function noteFromBackup(value) {
  if (!value || typeof value.text !== "string") return null;
  const note = {text: value.text, ts: Number(value.ts) || 0};
  if (Array.isArray(value.conflicts)) {
    note.conflicts = value.conflicts.filter(v => v && typeof v.text === "string").map(v => ({text: v.text, ts: Number(v.ts) || 0}));
  }
  return note;
}
// Backups from two devices have no shared revision IDs. Keep distinct text as
// recoverable copies, and replace only the local parents observed before the import.
function importLearningNotes(store, entries, known) {
  const local = store.read(), updates = [];
  for (const [id, raw] of Object.entries(entries || {})) {
    if (!known(id)) continue;
    const incoming = noteFromBackup(raw), old = local[id];
    if (!incoming || (!incoming.text.trim() && !incoming.conflicts?.length)) continue;
    const recent = old && (old.ts || 0) >= incoming.ts ? old : incoming;
    const other = recent === old ? incoming : old;
    const copies = new Map();
    for (const copy of [...(recent.conflicts || []), other, ...(other?.conflicts || [])]) {
      if (!copy?.text || copy.text === recent.text) continue;
      const previous = copies.get(copy.text);
      if (!previous || (copy.ts || 0) > previous.ts)
        copies.set(copy.text, {text:copy.text, ts:copy.ts || 0});
    }
    const merged = {...recent};
    if (copies.size) merged.conflicts = [...copies.values()];
    else delete merged.conflicts;
    if (old && old.text === merged.text && old.ts === merged.ts &&
        JSON.stringify(old.conflicts || []) === JSON.stringify(merged.conflicts || [])) continue;
    updates.push({id, value:merged, parents:store.base(id, true)});
  }
  for (const {id, value, parents} of updates) store.put(id, value, parents);
  return updates.length;
}
function showNoteCopies(box, note, restore, resolve) {
  box.replaceChildren();
  if (!note || !note.conflicts || !note.conflicts.length) return;
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "同一笔记的其他版本（" + note.conflicts.length + "）";
  details.append(summary);
  for (const copy of note.conflicts) {
    const p = document.createElement("p");
    p.textContent = copy.text;
    const button = document.createElement("button");
    button.className = "btn";
    button.textContent = "恢复此文本";
    button.onclick = () => restore(copy.text);
    details.append(p, button);
  }
  const keep = document.createElement("button");
  keep.className = "btn";
  keep.textContent = "保留编辑框文本并移除上述副本";
  keep.onclick = () => {
    if (confirm("保留编辑框中的笔记并移除这里列出的其他版本？")) resolve();
  };
  details.append(keep);
  box.append(details);
}

// Keep the editor's base until a switch or save. Remote edits cannot replace text
// the user is composing. Failed changes stay in the page and in JSON exports.
class LearningNoteEditor {
  constructor(store, ids, afterChange) {
    this.store = store;
    this.input = document.getElementById(ids.input);
    this.status = document.getElementById(ids.status);
    this.copies = document.getElementById(ids.copies);
    this.afterChange = afterChange;
    this.id = "";
    this.parents = [];
    this.timer = null;
    this.input.addEventListener("input", () => {
      clearTimeout(this.timer);
      this.status.textContent = "正在保存…";
      this.timer = setTimeout(() => this.flush(), 800);
    });
    window.addEventListener("storage", e => {
      if (!this.id || !e.key || !e.key.startsWith(store.prefix)) return;
      const note = store.read()[this.id];
      this.showCopies(note);
      if (!this.timer && !store.pending.has(this.id) && (note?.text || "") !== this.input.value) {
        this.status.textContent = "其他窗口已更新此笔记，编辑时将保留两个版本";
      }
    });
    // Run before the pending-write guard. pagehide is already too late to offer a choice.
    window.addEventListener("beforeunload", () => this.flush());
    window.addEventListener("pagehide", () => this.flush());
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") this.flush();
    });
  }
  open(id) {
    this.flush();
    this.id = String(id);
    const note = this.store.read()[this.id];
    this.parents = this.store.base(this.id);
    this.archived = note?.conflicts || [];
    this.input.value = note ? note.text : "";
    this.status.textContent = this.store.pending.has(this.id) ? "未能保存，草稿可以导出" : note ? "已保存" : "自动保存";
    this.showCopies(note);
    this.afterChange();
  }
  showCopies(note) {
    const visible = this.input.value;
    const copies = note ? [note, ...(note.conflicts || [])].filter(v => v.text !== visible) : [];
    const viewed = this.store.base(this.id, true);
    showNoteCopies(this.copies, {conflicts: copies}, text => {
      this.flush();
      const current = this.store.read()[this.id];
      const copies = [current, ...(current?.conflicts || []), {text: this.input.value, ts: Date.now()}]
        .filter(v => v && v.text && v.text !== text);
      this.input.value = text;
      this.save(copies, [...new Set([...viewed, ...this.parents])]);
    }, () => {
      clearTimeout(this.timer); this.timer = null;
      this.save([], viewed);
    });
  }
  flush() {
    if (this.timer === null) return;
    clearTimeout(this.timer);
    this.timer = null;
    this.save();
  }
  save(copies, parents = this.parents) {
    const text = this.input.value;
    // Preserve the backup copies this editor actually displayed. A concurrent editor's
    // newer record is already durable under its own key.
    const conflicts = (copies || this.archived).filter(v => v.text !== text);
    this.archived = conflicts;
    const value = text.trim() || conflicts.length ? {text, ts: Date.now(), ...(conflicts.length ? {conflicts} : {})} : null;
    const ok = this.store.put(this.id, value, parents);
    const note = this.store.read()[this.id];
    if (ok) this.parents = [this.store.lastWriteName];
    this.status.textContent = ok ? "已保存" : "未能保存，草稿可以导出";
    this.showCopies(note);
    this.afterChange();
  }
}
function watchLearningWrites(stores, retryButton, report, onRetry) {
  const recovery = document.createElement("button");
  recovery.type = "button";
  recovery.className = "btn";
  recovery.textContent = "导出异常记录原件";
  retryButton.after(recovery);
  recovery.addEventListener("click", () => {
    const entries = Object.fromEntries(stores.flatMap(store => [...store.unreadable]));
    const data = {format:"cfa.learning.recovery", version:1, entries};
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type:"application/json"}));
    const link = document.createElement("a");
    link.href = url;
    link.download = stores[0].key + "-原始恢复资料.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  });
  function refresh() {
    const failed = stores.some(store => store.pending.size);
    retryButton.hidden = !failed;
    retryButton.style.display = failed ? "" : "none";
    const damaged = stores.some(store => store.unreadable.size);
    recovery.hidden = !damaged;
    recovery.style.display = damaged ? "" : "none";
    const messages = [];
    if (failed) messages.push("浏览器写入失败。草稿仍在此页，可重试或导出备份。");
    if (damaged) messages.push("部分本机记录损坏。可读记录可照常备份，异常原件可另行导出。");
    if (stores.some(store => store.readFailed)) messages.push("浏览器无法读取本机记录。");
    report.textContent = messages.join(" ");
  }
  retryButton.addEventListener("click", () => {
    stores.forEach(store => store.retry());
    onRetry();
    refresh();
  });
  window.addEventListener("beforeunload", e => {
    if (stores.some(store => store.pending.size)) {
      e.preventDefault();
      e.returnValue = "";
    }
  });
  refresh();
  return refresh;
}
