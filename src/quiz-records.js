// One completed attempt (a whole exam, or one practice answer) is one storage write.
// Each tab writes its own event key, including on file:// where Web Locks may be absent.
class QuizRecords {
  static prefix = "cfa.quiz.v2.event.";
  static checkpoint = "cfa.quiz.v2.checkpoint";
  static intervals = [0, 1, 3, 7, 14, 30];

  constructor(storage) {
    try { this.storage = storage ?? globalThis.localStorage; }
    catch (_) { /* Browser storage is disabled. Keep new attempts in memory. */ }
    this.pending = new Map();
    this.state = this.empty();
    this.read();
  }
  empty() {
    return {wrong:Object.create(null), stats:Object.create(null), history:[], order:0, damaged:0};
  }
  static readWrong() {
    try { return new QuizRecords(localStorage).state.wrong; }
    catch (_) { return {}; }
  }
  static related(key) {
    return key === null || key.startsWith(this.prefix) || key === this.checkpoint ||
      ["cfa.quiz.wrong", "cfa.quiz.stats", "cfa.quiz.history"].includes(key);
  }
  static object(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }
  static count(value) {
    return Number.isSafeInteger(value) && value >= 0;
  }
  static strings(value) {
    return Array.isArray(value) && value.every(s => typeof s === "string");
  }
  static wrongEntry(value, question) {
    if (!this.object(value)) throw Error("错题记录应为对象");
    const type = value.t ?? question?.t;
    if (!["case","scale","var","theory"].includes(type) || (question && question.t !== type))
      throw Error("题型与题库不符");
    if (value.s != null && !["string","number"].includes(typeof value.s))
      throw Error("赛季字段无效");
    for (const key of ["star","done"]) {
      if (key in value && typeof value[key] !== "boolean") throw Error("收藏或掌握状态无效");
    }
    for (const key of ["wrong","last","due","stage"]) {
      if (key in value && !this.count(value[key])) throw Error("次数、时间或复习档位无效");
    }
    if (value.stage >= this.intervals.length) throw Error("复习档位超出范围");
    const your = value.your;
    if (your != null && your !== "") {
      if (type === "case") {
        if (!this.object(your) || Object.values(your).some(v => v != null && typeof v !== "string"))
          throw Error("判例作答格式错误");
      } else if (type === "scale") {
        if (!this.strings(your)) throw Error("多选答案应为文字数组");
      } else if (!this.count(your) && !(typeof your === "string" && /^\d+$/.test(your))) {
        throw Error("单选答案应为选项编号");
      }
    }
    const correct = value.correct ?? "";
    if (typeof correct !== "string" && !this.strings(correct)) throw Error("正确答案格式错误");
    return {...value, t:type, s:question?.s ?? value.s, correct:Array.isArray(correct) ? correct.join("、") : correct};
  }
  static importRows(backup, bank) {
    if (!this.object(backup) || (backup.app != null && backup.app !== "cfa-referee-quiz") || !this.object(backup.wrong))
      throw Error("请选择考题错题本 JSON 备份");
    const rows = Object.create(null);
    for (const [id, value] of Object.entries(backup.wrong)) {
      if (!Object.prototype.hasOwnProperty.call(bank, id)) continue; // Retired question.
      try { rows[id] = this.wrongEntry(value, bank[id]); }
      catch (error) { throw Error(id + "：" + error.message); }
    }
    return rows;
  }
  legacy() {
    const state = this.empty();
    const load = (name, fallback) => {
      const raw = this.storage.getItem(name);
      if (raw === null) return fallback;
      try {
        const result = JSON.parse(raw);
        if (Array.isArray(fallback) ? Array.isArray(result) : QuizRecords.object(result)) return result;
      } catch (_) { /* Report the unreadable key while retaining the original bytes. */ }
      state.damaged++;
      return fallback;
    };
    for (const [id, row] of Object.entries(load("cfa.quiz.wrong", {}))) {
      try { state.wrong[id] = QuizRecords.wrongEntry(row); }
      catch (_) { state.damaged++; }
    }
    for (const [id, row] of Object.entries(load("cfa.quiz.stats", {}))) {
      if (QuizRecords.object(row) && QuizRecords.count(row.r) && QuizRecords.count(row.w)) state.stats[id] = row;
      else state.damaged++;
    }
    for (const h of load("cfa.quiz.history", [])) {
      if (QuizRecords.object(h) && [h.t,h.got,h.max,h.n].every(QuizRecords.count)) state.history.push(h);
      else state.damaged++;
    }
    state.history = state.history.slice(0,20);
    return state;
  }
  static apply(state, event) {
    state.order = Math.max(state.order,event.order);
    if (event.kind === "attempt") {
      for (const item of event.answers) {
        const stat = state.stats[item.id] ??= {r:0,w:0};
        const entry = state.wrong[item.id];
        if (item.miss) {
          stat.w++;
          state.wrong[item.id] = {...item.miss, star:entry?.star || false, wrong:(entry?.wrong || 0)+1,
            stage:0, done:false, last:event.time, due:event.time};
        } else {
          stat.r++;
          if (entry) {
            entry.stage = Math.min((entry.stage || 0)+1, this.intervals.length-1);
            entry.due = event.time + this.intervals[entry.stage]*86400000;
            entry.done = entry.stage === this.intervals.length-1;
          }
        }
      }
      if (event.exam) {
        state.history.unshift({t:event.time,...event.exam});
        state.history.length = Math.min(state.history.length,20);
      }
    } else if (event.kind === "star") {
      if (state.wrong[event.id]) state.wrong[event.id].star = event.value;
    } else if (event.kind === "remove") {
      for (const id of event.ids) delete state.wrong[id];
    } else if (event.kind === "import") {
      for (const [id, row] of Object.entries(event.rows)) {
        if (!state.wrong[id] || (row.last || 0) > (state.wrong[id].last || 0))
          state.wrong[id] = {...row};
      }
    }
  }
  capture() {
    // The checkpoint is published before its included keys are removed. Retry if
    // a compactor published a different checkpoint while this tab read the keys.
    let raw, state, entries, covered;
    do {
      raw = this.storage.getItem(QuizRecords.checkpoint);
      const cp = raw === null ? null : JSON.parse(raw);
      state = cp ? cp.state : this.legacy();
      state.wrong = Object.assign(Object.create(null), state.wrong);
      state.stats = Object.assign(Object.create(null), state.stats);
      covered = new Set(cp?.covered);
      entries = [];
      for (const key of Object.keys(this.storage)) {
        if (!key.startsWith(QuizRecords.prefix) || covered.has(key)) continue;
        const value = this.storage.getItem(key);
        if (value !== null) entries.push([key,JSON.parse(value)]);
      }
    } while (raw !== this.storage.getItem(QuizRecords.checkpoint));
    return {state,entries,covered};
  }
  replay(state, entries) {
    entries.sort(([a,x],[b,y]) => x.order-y.order || (a < b ? -1 : a > b ? 1 : 0));
    for (const [,event] of entries) QuizRecords.apply(state,event);
    return state;
  }
  read() {
    try {
      const {state,entries} = this.capture();
      this.eventCount = entries.length;
      const combined = new Map(entries);
      for (const [key,event] of this.pending) combined.set(key,event);
      this.state = this.replay(state,[...combined]);
      this.unavailable = false;
    } catch (_) { this.unavailable = true; }
    return this.state;
  }
  write(change, keepDraft = true) {
    const state = this.read();
    const event = {...change,order:state.order+1,time:Date.now()};
    const token = Array.from(crypto.getRandomValues(new Uint32Array(3)),n=>n.toString(36)).join("-");
    const key = QuizRecords.prefix + token;
    try {
      if (this.unavailable) throw Error("记录暂时不可读取");
      this.storage.setItem(key,JSON.stringify(event));
    } catch (_) {
      if (!keepDraft) throw Error("浏览器存储不可写，现有记录已保留");
      this.pending.set(key,event);
      QuizRecords.apply(this.state,event);
      return false;
    }
    QuizRecords.apply(this.state,event);
    if (this.eventCount >= 64) this.compact();
    return true;
  }
  retry() {
    for (const [key,event] of this.pending) {
      try { this.storage.setItem(key,JSON.stringify(event)); }
      catch (_) { break; }
      this.pending.delete(key);
    }
    this.read();
    return !this.pending.size;
  }
  compact() {
    // Writes never depend on this optional optimization. Only one compactor can
    // replace the checkpoint; overlapping writers retain their separate keys.
    const locks = globalThis.navigator?.locks;
    if (!locks || this.compacting) return;
    this.compacting = true;
    locks.request(QuizRecords.checkpoint, {ifAvailable:true}, lock => {
      if (!lock) return;
      const {state,entries,covered:previous} = this.capture();
      if (entries.length < 64) return;
      // Finish cleanup of an interrupted compaction before forgetting its covered IDs.
      for (const key of previous) this.storage.removeItem(key);
      const covered = entries.map(([key])=>key);
      this.replay(state,entries);
      this.storage.setItem(QuizRecords.checkpoint,JSON.stringify({state,covered}));
      for (const key of covered) this.storage.removeItem(key);
    }).catch(()=>{}).finally(()=>{ this.compacting = false; });
  }
}
