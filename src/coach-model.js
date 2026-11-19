// Private lesson sheets stay in this browser. Student links carry only the selected public fields.
class CoachModel {
  static get limits() {
    return {title:100, question:1000, scenario:2000, note:4000, hash:24000};
  }

  constructor(cases, lessons, rulesByCategory) {
    this.cases = cases;
    this.rules = rulesByCategory;
    this.maxItems = Object.keys(cases).length;
    this.prompts = new Map(lessons.flatMap(lesson => lesson.cases.map(item => [item.id, item.prompt])));
    this.prefix = "cfa.coach.lessons.v1.entry.";
    this.storageError = "";
  }

  create(title="未命名课单") {
    return {id:this.newId(), revision:null, updated:0, title, items:[]};
  }

  newId() {
    return Array.from(crypto.getRandomValues(new Uint32Array(4)), n => n.toString(16).padStart(8,"0")).join("");
  }

  validText(value, field) {
    const labels = {title:"课单标题", question:"课堂问题", scenario:"学员情境", note:"教练备注"};
    if (typeof value !== "string") throw Error(labels[field] + "必须是文字。");
    if (value.length > CoachModel.limits[field]) throw Error(labels[field] + "最多 " + CoachModel.limits[field] + " 个字符。");
    return value;
  }

  content(value, strict=false) {
    if (!value || !Array.isArray(value.items)) throw Error("课单缺少案例清单。");
    const title = this.validText(value.title, "title");
    if (value.items.length > this.maxItems) throw Error("案例数超出本版本的判例库数量。");
    const seen = new Set();
    const items = value.items.map(item => {
      if (!item || typeof item.caseId !== "string" || !Object.hasOwn(this.cases, item.caseId)) {
        throw Error("课单中有本版本无法识别的判例。");
      }
      if (seen.has(item.caseId)) throw Error("同一堂课不能重复添加判例 " + item.caseId + "。");
      seen.add(item.caseId);
      const normalized = {caseId:item.caseId};
      for (const key of ["question","scenario","note"]) {
        const text = !strict && item[key] === undefined ? "" : item[key];
        normalized[key] = this.validText(text, key);
      }
      return normalized;
    });
    return {title,items};
  }

  // Each write gets its own key. Even two tabs committing the same parent at once
  // leave two distinct children. Only the observed ancestor can be compacted.
  readRecords() {
    const store = localStorage;
    const entries = [];
    for (const key of Object.keys(store)) {
      if (!key.startsWith(this.prefix)) continue;
      const raw = store.getItem(key);
      if (raw === null) continue;
      const row = JSON.parse(raw);
      if (!row || !/^[0-9a-f]{32}$/.test(row.id) || !/^[0-9a-f]{32}$/.test(row.revision) ||
          key !== this.prefix + row.revision || !Number.isFinite(row.updated)) throw Error("课单存储记录不完整。");
      const parents = row.parents || (row.parent ? [row.parent] : []);
      const anchors = row.anchors || [];
      if (!Array.isArray(parents) || !parents.every(p => /^[0-9a-f]{32}$/.test(p)) ||
          !Array.isArray(anchors) || !anchors.every(a => /^\d{16}-[0-9a-f]{32}$/.test(a))) {
        throw Error("课单版本索引不完整。");
      }
      entries.push({...this.content(row, true), id:row.id, revision:row.revision, updated:row.updated, parents, anchors});
    }
    const superseded = new Set(entries.flatMap(entry => entry.parents));
    const groups = new Map();
    for (const row of entries.filter(entry => !superseded.has(entry.revision))) {
      if (!groups.has(row.id)) groups.set(row.id, []);
      groups.get(row.id).push(row);
    }
    const common = (left, right) => {
      let n = 0;
      while (n < left.length && n < right.length && left[n] === right[n]) n++;
      return n;
    };
    const live = [];
    for (const siblings of groups.values()) {
      if (siblings.length > 1) {
        // Keep the ordered fork point, not a changing leaf timestamp, as each
        // branch's identity. Compact to just enough ancestry to name that fork.
        const ranked = siblings.map(row => ({
          row, path:[...row.anchors, String(row.updated).padStart(16,"0") + "-" + row.revision]
        })).sort((a,b) => a.path.join("/").localeCompare(b.path.join("/")));
        ranked.forEach(({row,path}, i) => {
          const before = common(path, ranked[i-1]?.path || []);
          const after = common(path, ranked[i+1]?.path || []);
          if (i) row.id = path[before].slice(-32);
          row.anchors = path.slice(0, Math.max(before,after)+1);
        });
      }
      live.push(...siblings);
    }
    return live.sort((a,b) => b.updated - a.updated || b.revision.localeCompare(a.revision));
  }

  list() {
    try {
      const items = this.readRecords();
      this.storageError = "";
      return items.map(({parents,anchors,...lesson}) => lesson);
    } catch (_) {
      this.storageError = "无法读取本机课单。仍可编辑并导出教练备份。";
      return [];
    }
  }

  save(lesson) {
    const content = this.content(lesson);
    if (!/^[0-9a-f]{32}$/.test(lesson.id) ||
        (lesson.revision !== null && !/^[0-9a-f]{32}$/.test(lesson.revision))) throw Error("课程记录编号无效。");
    let conflict = false;
    let saved;
    const draft = {...content, id:lesson.id, revision:lesson.revision, updated:lesson.updated || 0};
    try {
      const live = this.readRecords();
      const base = lesson.revision ? live.find(row => row.revision === lesson.revision) : null;
      conflict = !base && (lesson.revision !== null || live.some(row => row.id === lesson.id));
      const id = base ? base.id : conflict ? this.newId() : lesson.id;
      saved = {...content, id, revision:this.newId(), updated:Date.now()};
      const parents = base ? [base.revision, ...base.parents.filter(p => localStorage.getItem(this.prefix + p) !== null)] : [];
      localStorage.setItem(this.prefix + saved.revision, JSON.stringify({...saved, parents, anchors:base?.anchors || []}));
      for (const parent of parents) {
        // Each child remembers surviving ancestors until cleanup actually succeeds.
        try { localStorage.removeItem(this.prefix + parent); } catch (_) { /* Retry when this branch next saves. */ }
      }
      // A competing writer could have committed while this tab was storing its
      // revision. Return the resolved route for the draft just saved, when visible.
      try {
        const resolved = this.readRecords().find(row => row.revision === saved.revision);
        if (resolved && resolved.id !== saved.id) {
          saved.id = resolved.id;
          conflict = true;
        }
      } catch (_) { /* The revision was already durably written. */ }
      this.storageError = "";
    } catch (_) {
      this.storageError = "本机保存失败。草稿仍在，可重试保存或导出教练备份。";
      return {lesson:draft, ok:false, conflict:false, error:this.storageError};
    }
    return {lesson:saved, ok:true, conflict};
  }

  backup(lesson) {
    return JSON.stringify({format:"cfa.coach.backup",version:1,lesson:this.content(lesson)}, null, 2);
  }

  importBackup(text) {
    const limits = CoachModel.limits;
    const bound = 4096 + this.maxItems * (6 * (limits.question + limits.note + limits.scenario) + 512);
    if (typeof text !== "string" || text.length > bound) throw Error("备份文件过大或格式错误。");
    let parsed;
    try { parsed = JSON.parse(text.replace(/^\uFEFF/,"")); } catch (_) { throw Error("文件不是有效的 JSON 课单备份。"); }
    if (parsed?.format !== "cfa.coach.backup" || parsed.version !== 1) throw Error("未知的教练备份格式或版本。");
    const content = this.content(parsed.lesson, true);
    return this.save({...this.create(content.title), items:content.items});
  }

  student(lesson, {review=false}={}) {
    const {title,items} = this.content(lesson);
    if (!items.length) throw Error("请先为课单添加至少一个判例。");
    const withReview = review === true;
    return {title:title.trim() || "未命名课单", review:withReview, items:items.map(item => {
      const c = this.cases[item.caseId];
      const out = {
        caseId:item.caseId, match:c.home && c.away ? c.home + " 对 " + c.away : c.comp || "足协赛季评议",
        citation:c.season + " 赛季 · 第 " + c.issue + " 期 · 判例 " + c.no,
        prompt:item.scenario.trim() || this.prompts.get(item.caseId) || "请根据课堂提供的画面或情境记录可观察到的事实。若材料不足，写下还需要的画面或角度。",
        question:item.question.trim() || "你观察到了什么？哪些细节支持你的判断？"
      };
      if (withReview) {
        out.conclusion = c.conclusion || "本期未单列评议结论，请查阅足协原文。";
        out.sources = [{issue:c.issue,date:c.source_date,url:c.source,label:"第 " + c.issue + " 期足协原文"}];
        if (c.supplement) {
          const s = c.supplement;
          out.sources.push({issue:s.issue,date:s.date,url:s.url,label:"第 " + s.issue + " 期补充认定"});
        }
        out.rules = (this.rules[c.category] || []).map(({law,title,version,href}) => ({law,title,version,href}));
      }
      return out;
    })};
  }

  encodeShare(lesson, {review=false}={}) {
    const {title,items} = this.content(lesson);
    if (!items.length) throw Error("请先为课单添加至少一个判例。");
    // Empty trailing fields use the same neutral defaults when the recipient opens the link.
    const rows = items.map(({caseId,question,scenario}) => {
      if (scenario) return [caseId,question,scenario];
      return question ? [caseId,question] : [caseId];
    });
    const bytes = new TextEncoder().encode(JSON.stringify([1,title,review === true,rows]));
    if (bytes.length * 4 / 3 + 9 > CoachModel.limits.hash) throw Error("课单链接过长，请导出独立 HTML 讲义。");
    const binary = Array.from(bytes, b => String.fromCharCode(b)).join("");
    return "#handout-" + btoa(binary).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");
  }

  decodeShare(hash) {
    if (typeof hash !== "string" || hash.length > CoachModel.limits.hash ||
        !/^#handout-[A-Za-z0-9_-]+$/.test(hash)) throw Error("学员分享链接无效或过长。");
    let payload;
    try {
      const text = atob(hash.slice(9).replace(/-/g,"+").replace(/_/g,"/"));
      const bytes = Uint8Array.from(text, c => c.charCodeAt(0));
      payload = JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(bytes));
    } catch (_) { throw Error("学员分享链接损坏，无法读取。"); }
    if (!Array.isArray(payload) || payload.length !== 4 || payload[0] !== 1 ||
        typeof payload[2] !== "boolean" || !Array.isArray(payload[3])) throw Error("未知的学员链接格式或版本。");
    const items = payload[3].map(row => {
      if (!Array.isArray(row) || row.length < 1 || row.length > 3 || !row.every(v => typeof v === "string")) {
        throw Error("学员分享中的判例信息不完整。");
      }
      return {caseId:row[0], question:row[1] || "", scenario:row[2] || ""};
    });
    return this.student({title:payload[1],items}, {review:payload[2]});
  }

  sheetBody(student) { return CoachHandout.body(student); }
  sheetHTML(student) { return CoachHandout.document(student); }
  handout(lesson, options) { return this.sheetHTML(this.student(lesson, options)); }
}
