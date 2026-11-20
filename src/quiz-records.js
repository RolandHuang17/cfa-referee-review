// One completed attempt (a whole exam, or one practice answer) is one storage write.
// Each tab writes its own event key, including on file:// where Web Locks may be absent.
class QuizRecords {
  static prefix = "cfa.quiz.v2.event.";
  static checkpoint = "cfa.quiz.v2.checkpoint";
  static recovery = "cfa.quiz.v2.recovery";
  static intervals = [0, 1, 3, 7, 14, 30];
  static legacyScaleIds = new Set();
  static receiptLimit = 128;
  static examId(id) { return typeof id === "string" && /^[0-9a-f]{32}$/.test(id); }
  static examStatus(state, id, opened) {
    if (state.examReceipts.some(([run])=>run === id) || state.history.some(h=>h.id === id)) return "recorded";
    return opened < state.examFloor ? "uncertain" : "new";
  }
  static rememberExam(state, id, order) {
    state.examReceipts.push([id,order]);
    if (state.examReceipts.length > this.receiptLimit)
      state.examFloor = Math.max(state.examFloor,state.examReceipts.shift()[1]);
  }

  constructor(storage) {
    try { this.storage = storage ?? globalThis.localStorage; }
    catch (_) { /* Browser storage is disabled. Keep new attempts in memory. */ }
    this.pending = new Map();
    this.savedPending = new Set();
    this.checked = new Map();
    this.state = this.empty();
    this.read();
  }
  empty() {
    return {wrong:Object.create(null), stats:Object.create(null), history:[], examReceipts:[], examFloor:0, order:0, damaged:0};
  }
  static readWrong() {
    if (!this.portalReader) this.portalReader = new QuizRecords();
    else this.portalReader.read();
    return this.portalReader.state.wrong;
  }
  static related(key) {
    return key === null || key.startsWith(this.prefix) || key === this.checkpoint || key === this.recovery ||
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
  static validResult(row) {
    return this.object(row) && [row.got,row.max,row.n].every(this.count) && row.got <= row.max;
  }
  static validEvent(event) {
    if (!this.object(event) || !this.count(event.order) || !event.order || !this.count(event.time)) return false;
    const id = value => typeof value === "string" && value.length > 0;
    switch (event.kind) {
    case "attempt":
      if ("examId" in event && (!this.examId(event.examId) || !this.count(event.opened) || !event.exam)) return false;
      return Array.isArray(event.answers) && event.answers.length > 0 && event.answers.every(item => {
        if (!this.object(item) || !id(item.id)) return false;
        if ("miss" in item) item.miss = this.wrongEntry(item.miss);
        return true;
      }) && (!("exam" in event) || this.validResult(event.exam));
    case "star": return id(event.id) && typeof event.value === "boolean";
    case "remove": return Array.isArray(event.ids) && event.ids.every(id);
    case "import":
      if (!this.object(event.rows)) return false;
      for (const [key,row] of Object.entries(event.rows)) {
        if (!id(key)) return false;
        event.rows[key] = this.wrongEntry(row);
      }
      if ("legacyScaleStats" in event && (!this.object(event.legacyScaleStats) ||
        !Object.entries(event.legacyScaleStats).every(([key,row]) => this.legacyScaleIds.has(key)
          && this.object(row) && this.count(row.r) && this.count(row.w)))) return false;
      return true;
    default: return false;
    }
  }
  cleanState(raw) {
    const state = this.empty();
    if (!QuizRecords.object(raw.wrong)) state.damaged++;
    else for (const [id,row] of Object.entries(raw.wrong)) {
      try { state.wrong[id] = QuizRecords.wrongEntry(row); }
      catch (_) { state.damaged++; }
    }
    if (!QuizRecords.object(raw.stats)) state.damaged++;
    else for (const [id,row] of Object.entries(raw.stats)) {
      if (QuizRecords.object(row) && QuizRecords.count(row.r) && QuizRecords.count(row.w)) state.stats[id] = {r:row.r,w:row.w};
      else state.damaged++;
    }
    if (!Array.isArray(raw.history)) state.damaged++;
    else for (const h of raw.history) {
      if (QuizRecords.validResult(h) && QuizRecords.count(h.t)) state.history.push(h);
      else state.damaged++;
    }
    state.history = state.history.slice(0,20);
    if ("examFloor" in raw){
      if (QuizRecords.count(raw.examFloor)) state.examFloor = raw.examFloor;
      else state.damaged++;
    }
    if ("examReceipts" in raw){
      if (!Array.isArray(raw.examReceipts)) state.damaged++;
      else for (const item of raw.examReceipts){
        if (Array.isArray(item) && QuizRecords.examId(item[0]) && QuizRecords.count(item[1]))
          QuizRecords.rememberExam(state,item[0],item[1]);
        else state.damaged++;
      }
    }
    return state;
  }
  legacy() {
    const load = (key,fallback) => {
      const raw = this.storage.getItem(key);
      if (raw === null) return fallback;
      try { return JSON.parse(raw); } catch (_) { return null; }
    };
    return this.cleanState({wrong:load("cfa.quiz.wrong",{}),stats:load("cfa.quiz.stats",{}),history:load("cfa.quiz.history",[])});
  }
  static checksum(state, covered) {
    const bytes = JSON.stringify([state,covered]);
    let hash = 2166136261;
    for (let i=0; i<bytes.length; i++) hash = Math.imul(hash ^ bytes.charCodeAt(i),16777619);
    return (hash >>> 0).toString(16);
  }
  decodeCheckpoint(raw) {
    if (this.checked.has(raw)) return this.checked.get(raw);
    let candidate = null;
    try {
      const parsed = JSON.parse(raw);
      if (QuizRecords.object(parsed?.state)) {
        const state = this.cleanState(parsed.state);
        const validOrder = QuizRecords.count(parsed.state.order);
        const validCovered = QuizRecords.strings(parsed.covered) && parsed.covered.every(key=>key.startsWith(QuizRecords.prefix));
        const intact = parsed.checksum === undefined || parsed.checksum === QuizRecords.checksum(parsed.state,parsed.covered);
        const complete = validOrder && validCovered && intact && !state.damaged;
        state.order = validOrder ? parsed.state.order : 0;
        state.damaged += QuizRecords.count(parsed.state.damaged) ? parsed.state.damaged : 0;
        candidate = {state,complete,covered:validCovered ? new Set(parsed.covered) : null};
      }
    } catch (_) { /* The other copy or surviving original events may still be readable. */ }
    this.checked.set(raw,candidate);
    return candidate;
  }
  cloneState(state) {
    // Replay replaces individual records, so copying only the maps and the history list
    // keeps the cached, validated checkpoint immutable.
    return {...state,wrong:Object.assign(Object.create(null),state.wrong),
      stats:Object.assign(Object.create(null),state.stats),history:state.history.slice(),examReceipts:state.examReceipts.slice()};
  }
  static apply(state, event) {
    state.order = Math.max(state.order,event.order);
    if (event.kind === "attempt") {
      if (event.examId){
        if (this.examStatus(state,event.examId,event.opened) !== "new") return;
        this.rememberExam(state,event.examId,event.order);
      }
      for (const item of event.answers) {
        const stat = state.stats[item.id] || {r:0,w:0};
        const entry = state.wrong[item.id];
        if (item.miss) {
          state.stats[item.id] = {r:stat.r,w:stat.w+1};
          state.wrong[item.id] = {...item.miss, star:entry?.star || false, wrong:(entry?.wrong || 0)+1,
            stage:0, done:false, last:event.time, due:event.time};
        } else {
          state.stats[item.id] = {r:stat.r+1,w:stat.w};
          if (entry) {
            const stage = Math.min((entry.stage || 0)+1, this.intervals.length-1);
            state.wrong[item.id] = {...entry,stage,due:event.time + this.intervals[stage]*86400000,done:stage === this.intervals.length-1};
          }
        }
      }
      if (event.exam) {
        state.history.unshift({t:event.time,...event.exam});
        state.history.length = Math.min(state.history.length,20);
      }
    } else if (event.kind === "star") {
      if (state.wrong[event.id]) state.wrong[event.id] = {...state.wrong[event.id],star:event.value};
    } else if (event.kind === "remove") {
      for (const id of event.ids) delete state.wrong[id];
    } else if (event.kind === "import") {
      for (const [id, row] of Object.entries(event.rows)) {
        if (!state.wrong[id] || (row.last || 0) > (state.wrong[id].last || 0))
          state.wrong[id] = {...row};
      }
      // An imported aggregate may overlap a local one. Retain the local counts.
      for (const [id,row] of Object.entries(event.legacyScaleStats || {}))
        if (!state.stats[id]) state.stats[id] = {r:row.r,w:row.w};
    }
  }
  mergeFragment(state, fragment) {
    // Without usable checkpoint metadata a surviving row and an old event may describe
    // the same attempt. Keep the larger verifiable count; never add them together.
    for (const [id,stat] of Object.entries(fragment.stats)) {
      const other = state.stats[id] || {r:0,w:0};
      state.stats[id] = {r:Math.max(stat.r,other.r),w:Math.max(stat.w,other.w)};
    }
    for (const [id,row] of Object.entries(fragment.wrong)) {
      const other = state.wrong[id];
      if (!other) state.wrong[id] = row;
      else {
        const latest = (row.last || 0) >= (other.last || 0) ? row : other;
        state.wrong[id] = {...latest,wrong:Math.max(row.wrong || 0,other.wrong || 0)};
      }
    }
    // Preserve genuine identical exams within a single source, including timestamp ties.
    const counts = new Map();
    const identity = h => [h.t,h.got,h.max,h.n].join("/");
    for (const h of state.history) counts.set(identity(h),(counts.get(identity(h)) || 0)+1);
    for (const h of fragment.history) {
      if (h.id && state.history.some(other => other.id === h.id)) continue;
      const key = identity(h), n = counts.get(key) || 0;
      if (n) counts.set(key,n-1);
      else state.history.push(h);
    }
    state.history.sort((a,b)=>b.t-a.t);
    state.history = state.history.slice(0,20);
    state.examFloor = Math.max(state.examFloor,fragment.examFloor);
    const receipts = new Map([...state.examReceipts,...fragment.examReceipts]);
    state.examReceipts = [];
    for (const [id,order] of [...receipts].sort((a,b)=>a[1]-b[1])) QuizRecords.rememberExam(state,id,order);
    state.order = Math.max(state.order,fragment.order);
  }
  scan(primary, recovery) {
    const snapshots = [...new Set([primary,recovery].filter(raw=>raw !== null))];
    for (const key of this.checked.keys()) if (!snapshots.includes(key)) this.checked.delete(key);
    const candidates = snapshots.map(raw=>this.decodeCheckpoint(raw));
    const damagedSnapshot = candidates.some(cp=>!cp?.complete);
    const sorted = candidates.filter(Boolean).sort((a,b)=>Number(b.complete)-Number(a.complete) || b.state.order-a.state.order);
    const chosen = sorted[0];
    let state = chosen?.complete ? this.cloneState(chosen.state) : this.legacy();
    const covered = chosen?.covered || new Set();
    const entries = [], uncertain = [];
    const observed = new Map();
    let damaged = damagedSnapshot, size = 0;
    for (const key of Object.keys(this.storage)) {
      if (!key.startsWith(QuizRecords.prefix)) continue;
      const raw = this.storage.getItem(key);
      if (raw === null) continue;
      let event;
      try {
        event = JSON.parse(raw);
        if (!QuizRecords.validEvent(event)) throw Error("无效操作");
      } catch (_) { damaged = true; continue; }
      observed.set(key,raw);
      if (covered.has(key)) {
        if (chosen && !chosen.complete) uncertain.push([key,event]);
      } else if (chosen && !chosen.complete && !chosen.covered && !event.afterRecovery &&
          (!chosen.state.order || event.order <= chosen.state.order)) {
        uncertain.push([key,event]);
      } else {
        entries.push([key,event]);
        size += raw.length;
      }
    }
    if (chosen && !chosen.complete) {
      this.replay(state,uncertain);
      this.mergeFragment(state,chosen.state);
    }
    return {state,entries,observed,size,damaged,damagedSnapshot};
  }
  capture() {
    // A compactor publishes both copies before removing the events they contain.
    // A reader overlapping publication retries from the new pair.
    let primary, recovery, result;
    do {
      primary = this.storage.getItem(QuizRecords.checkpoint);
      recovery = this.storage.getItem(QuizRecords.recovery);
      result = this.scan(primary,recovery);
    } while (primary !== this.storage.getItem(QuizRecords.checkpoint) || recovery !== this.storage.getItem(QuizRecords.recovery));
    return result;
  }
  replay(state, entries) {
    entries.sort(([a,x],[b,y]) => x.order-y.order || (a < b ? -1 : a > b ? 1 : 0));
    for (const [,event] of entries) QuizRecords.apply(state,event);
    return state;
  }
  read() {
    try {
      if (!this.storage) this.storage = globalThis.localStorage;
      const {state,entries,size,damaged,damagedSnapshot} = this.capture();
      this.eventCount = entries.length;
      this.eventSize = size;
      this.damagedStorage = damaged;
      this.damagedSnapshot = damagedSnapshot;
      const combined = new Map(entries);
      // A restored pending exam can predate a durable copy that was temporarily unreadable.
      // Compare against durable receipts before combining drafts or retrying their writes.
      const durable = [...this.pending.values()].some(e=>e.examId) ? this.replay(this.cloneState(state),entries.slice()) : null;
      for (const [key,event] of this.pending){
        if (event.examId && QuizRecords.examStatus(durable,event.examId,event.opened) !== "new") this.savedPending.add(key);
        if (!this.savedPending.has(key)) combined.set(key,event);
      }
      this.state = this.replay(state,[...combined]);
      for (const key of this.savedPending) this.pending.delete(key);
      this.savedPending.clear();
      this.unavailable = false;
    } catch (_) { this.unavailable = true; }
    return this.state;
  }
  commitExam(change) {
    const state = this.read();
    const status = QuizRecords.examStatus(state,change.examId,change.opened);
    if (status !== "new"){
      return [...this.pending.values()].some(e=>e.examId === change.examId) ? "pending" : status;
    }
    return this.append(change,state,true) ? "written" : "pending";
  }
  write(change, keepDraft = true) {
    return this.append(change,this.read(),keepDraft);
  }
  append(change, state, keepDraft) {
    const event = {...change,order:state.order+1,time:Date.now()};
    if (this.damagedStorage) event.afterRecovery = true;
    const serialized = JSON.stringify(event);
    const token = Array.from(crypto.getRandomValues(new Uint32Array(3)),n=>n.toString(36)).join("-");
    const key = QuizRecords.prefix + token;
    try {
      if (this.unavailable) throw Error("记录暂时不可读取");
      this.storage.setItem(key,serialized);
    } catch (_) {
      if (!keepDraft) throw Error("浏览器存储不可写，现有记录已保留");
      this.pending.set(key,event);
      QuizRecords.apply(this.state,event);
      return false;
    }
    QuizRecords.apply(this.state,event);
    if (!this.damagedSnapshot && (this.eventCount+1 >= 64 || this.eventSize+serialized.length >= 65536)) this.compact();
    return true;
  }
  retry() {
    // A successful setItem need not still have a key: another tab may already
    // have compacted it. Never write that operation again while confirming it.
    this.read();
    if (this.unavailable) return false;
    for (const [key,event] of this.pending) {
      try { this.storage.setItem(key,JSON.stringify(event)); }
      catch (_) { break; }
      this.savedPending.add(key);
    }
    this.read();
    return !this.unavailable && !this.pending.size;
  }
  recoveryArchive() {
    const records = Object.create(null);
    let complete = true;
    try {
      for (const key of Object.keys(this.storage)) {
        if (!QuizRecords.related(key)) continue;
        const raw = this.storage.getItem(key);
        if (raw !== null) records[key] = raw;
      }
    } catch (_) { complete = false; }
    return {app:"cfa-quiz-records-recovery",exported:new Date().toISOString(),
      complete,records,pending:Object.fromEntries(this.pending)};
  }
  compact() {
    // Writes never depend on this optional optimization. Only one compactor can
    // replace the checkpoint; overlapping writers retain their separate keys.
    const locks = globalThis.navigator?.locks;
    if (!locks || this.compacting) return;
    this.compacting = true;
    locks.request(QuizRecords.checkpoint, {ifAvailable:true}, lock => {
      if (!lock) return;
      const {state,entries,size,damagedSnapshot,observed} = this.capture();
      if (damagedSnapshot || (entries.length < 64 && size < 65536)) return;
      this.replay(state,entries);
      const covered = [...observed.keys()];
      const raw = JSON.stringify({state,covered,checksum:QuizRecords.checksum(state,covered)});
      // If either write fails, the original events stay intact and replay is idempotent.
      const previousRecovery = this.storage.getItem(QuizRecords.recovery);
      this.storage.setItem(QuizRecords.recovery,raw);
      try { this.storage.setItem(QuizRecords.checkpoint,raw); }
      catch (_) {
        // Free the extra space if quota allowed only one of the two writes.
        if (previousRecovery === null) this.storage.removeItem(QuizRecords.recovery);
        else this.storage.setItem(QuizRecords.recovery,previousRecovery);
        return;
      }
      for (const [key,value] of observed) {
        if (this.storage.getItem(key) === value) this.storage.removeItem(key);
      }
    }).catch(()=>{}).finally(()=>{ this.compacting = false; });
  }
}
