class CompareAttempts {
  constructor() {
    this.store = new LearningRecords("cfa.compare.attempts.v1");
    this.current = null;
    this.owned = false;
  }
  uniqueId() {
    return Array.from(crypto.getRandomValues(new Uint32Array(3)), n => n.toString(36)).join("-");
  }
  list(lesson) {
    const all = Object.values(this.store.read()).filter(a =>
      a && a.lesson === lesson && typeof a.id === "string" && typeof a.revision === "string" &&
      Array.isArray(a.picks) && a.picks.length <= 2 && a.picks.every(p => p && typeof p.verdict === "string") &&
      Array.isArray(a.drafts) && a.drafts.length === 2 && a.drafts.every(d => d && typeof d === "object"));
    // A resumed tab writes a separate version. Hide its predecessor only if that
    // exact revision still exists; another tab may have continued editing it.
    const superseded = new Set(all.map(a => a.parentRevision));
    return all.filter(a => !superseded.has(a.revision))
      .sort((a, b) => b.updated - a.updated || b.id.localeCompare(a.id));
  }
  start(lesson, id) {
    const attempts = this.list(lesson);
    const saved = id ? attempts.find(a => a.id === id) : attempts[0];
    if (!saved) return this.fresh(lesson);
    this.current = JSON.parse(JSON.stringify(saved));
    this.owned = false;
    return this.current;
  }
  fresh(lesson) {
    this.current = {id:this.uniqueId(), lesson, picks:[], drafts:[{}, {}], reflection:"", updated:0};
    this.owned = true;
    return this.current;
  }
  save() {
    const a = this.current;
    if (!this.owned) {
      a.parentRevision = a.revision;
      a.id = this.uniqueId();
      this.owned = true;
    }
    a.updated = Date.now();
    a.revision = this.uniqueId();
    return this.store.put(a.id, JSON.parse(JSON.stringify(a)), this.store.base(a.id));
  }
}
