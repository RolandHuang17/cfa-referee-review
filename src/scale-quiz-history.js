// A shared old ID describes the whole group. Only the last missed question can
// have enough evidence to replay a specific scene. Its counts stay under the old ID.
class ScaleQuizHistory {
  constructor(published, bank) {
    this.published = published;
    this.bank = bank;
    this.importBank = Object.assign(Object.create(null), bank);
    for (const id of Object.keys(published))
      this.importBank[id] = {t:"scale", s:id.split("-")[1]};
  }
  entries(wrong, stats) {
    return Object.keys(this.published).filter(id => wrong[id] || stats[id]);
  }
  candidates(id) {
    return Object.keys(this.published[id]).map(key => this.bank[key]).filter(Boolean);
  }
  lastQuestion(id, row) {
    if (!row || (row.t && row.t !== "scale")) return null;
    const decisions = this.published[id];
    let keys = Object.keys(decisions);
    let hasEvidence = false;
    const raw = Array.isArray(row.correct) ? row.correct.join("、") : row.correct;
    if (typeof raw === "string" && raw.trim()) {
      // Historical scoreScale appended the missed labels, even on an empty answer.
      const normalize = text => text.split("、").map(s=>s.trim()).sort().join("、");
      const answer = normalize(raw.split(/、(?:漏选\s|无漏选)/)[0]);
      keys = keys.filter(key=>normalize(decisions[key]) === answer);
      hasEvidence = true;
    }
    for (const field of ["link", "series", "title"]) {
      if (typeof row[field] !== "string" || !row[field]) continue;
      keys = keys.filter(key => this.bank[key]?.[field] === row[field]);
      hasEvidence = true;
    }
    return hasEvidence && keys.length === 1 ? this.bank[keys[0]] || null : null;
  }
  exportStats(stats) {
    return Object.fromEntries(Object.keys(this.published).filter(id=>stats[id]).map(id=>[id,stats[id]]));
  }
  importStats(backup, current) {
    const rows = Object.create(null);
    let conflicts = 0;
    if (!("legacyScaleStats" in backup)) return {rows, conflicts};
    if (!QuizRecords.object(backup.legacyScaleStats)) throw Error("旧尺度题成绩格式错误");
    for (const [id,value] of Object.entries(backup.legacyScaleStats)) {
      if (!Object.hasOwn(this.published,id)) throw Error("旧尺度题编号无效：" + id);
      if (!QuizRecords.object(value) || !QuizRecords.count(value.r) || !QuizRecords.count(value.w))
        throw Error("旧尺度题成绩无效：" + id);
      if (!current[id]) rows[id] = {r:value.r,w:value.w};
      else if (current[id].r !== value.r || current[id].w !== value.w) conflicts++;
    }
    return {rows, conflicts};
  }
}
