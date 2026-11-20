// One browser tab owns its draft. The record contains selections, never the answer key or scored feedback.
class QuizSession {
  static key = "cfa.quiz.exam.v1";

  constructor(bank, version, axes) {
    this.bank = bank;
    this.version = version;
    this.axes = axes;
    this.stored = false;
  }
  static id() {
    return Array.from(crypto.getRandomValues(new Uint8Array(16)), n => n.toString(16).padStart(2,"0")).join("");
  }
  save(round) {
    const orders = Object.create(null);
    for (const q of round.qs) if (q.t === "theory") orders[q.k] = q._disp;
    const draft = {version:1, bank:this.version, id:round.id, opened:round.opened, index:round.i,
      timer:round.timer, deadline:round.deadline ?? null, submitting:!!round.submitting,
      keys:round.qs.map(q=>q.k), orders, answers:round.answers};
    try {
      sessionStorage.setItem(QuizSession.key,JSON.stringify(draft));
      this.stored = true;
      return true;
    } catch (_) { return false; }
  }
  clear() {
    try { sessionStorage.removeItem(QuizSession.key); this.stored = false; return true; }
    catch (_) { return !this.stored; }
  }
  validAnswer(q, a) {
    if (a === null) return true;
    if (q.t === "case") {
      return QuizRecords.object(a) && Object.entries(a).every(([axis,value]) =>
        Object.hasOwn(this.axes,axis) && (value === null || ((axis === "v" || q.ans?.[axis]) &&
          this.axes[axis].some(([id]) => id === value))));
    }
    if (q.t === "scale") {
      return Array.isArray(a) && new Set(a).size === a.length && a.every(v => q.dec.some(d=>d.label === v));
    }
    return (typeof a === "number" || (typeof a === "string" && /^\d+$/.test(a))) &&
      Number.isInteger(+a) && +a >= 0 && +a < q.opts.length;
  }
  load() {
    let raw;
    try { raw = sessionStorage.getItem(QuizSession.key); }
    catch (_) { this.readable = false; return null; }
    this.readable = true;
    if (raw === null) return null;
    this.stored = true;
    let d;
    try { d = JSON.parse(raw); } catch (_) {}
    if (d?.version === 1 && d.bank !== this.version) throw Error("题库已更新，旧试卷已停止恢复。重新开考会替换暂存试卷，历史成绩保留。");
    const invalid = () => { throw Error("暂存试卷不完整，未据此计分。请重新开始考试。"); };
    if (!d || d.version !== 1 || !QuizRecords.examId(d.id) || !QuizRecords.count(d.opened) ||
        !Array.isArray(d.keys) || !d.keys.length || d.keys.length > Object.keys(this.bank).length ||
        new Set(d.keys).size !== d.keys.length || !Number.isInteger(d.index) || d.index < 0 || d.index >= d.keys.length ||
        !Array.isArray(d.answers) || d.answers.length !== d.keys.length || !QuizRecords.object(d.orders) ||
        typeof d.submitting !== "boolean" || !["off","std","relaxed"].includes(d.timer) ||
        (d.deadline !== null && (!QuizRecords.count(d.deadline) || d.deadline === 0)) ||
        ((d.timer === "off") !== (d.deadline === null))) invalid();
    const qs = d.keys.map((key,i) => {
      const q = this.bank[key];
      if (typeof key !== "string" || !q || !this.validAnswer(q,d.answers[i])) invalid();
      if (q.t !== "theory") return q;
      const order = d.orders[key];
      if (!Array.isArray(order) || order.length !== q.opts.length || new Set(order).size !== order.length ||
          !order.every(n => Number.isInteger(n) && n >= 0 && n < order.length)) invalid();
      return {...q,_disp:order};
    });
    return {qs,i:d.index,answers:d.answers,scores:qs.map(()=>null),mode:"exam",locked:false,
      id:d.id,opened:d.opened,timer:d.timer,deadline:d.deadline,submitting:d.submitting};
  }
}
