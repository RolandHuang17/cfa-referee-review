const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {resolve} = require("node:path");
const vm = require("node:vm");
const {webcrypto} = require("node:crypto");

const root = resolve(__dirname, "..");
const json = name => JSON.parse(readFileSync(resolve(root, "data", name + ".json"), "utf8"));
const program = ["coach-handout.js","coach-model.js"].map(f => readFileSync(resolve(root, "src", f),"utf8")).join("\n");
const lessons = json("compare-lessons").lessons;
const cases = {};
for (const year of ["2026","2025","2024"]) {
  const {cases:rows, issues} = json("cases-"+year);
  for (const row of rows) {
    const issue = issues.find(entry => entry.no === row.issue);
    const match = row.conclusion.match(/^【第(\d+)期补充认定】/m);
    const later = match && issues.find(entry => entry.no === Number(match[1]));
    cases[year+"-"+row.seq] = {...row, season:year, source:issue.url, source_date:issue.date,
      ...(later ? {supplement:{issue:later.no,date:later.date,url:later.url}} : {})};
  }
}
const table = json("xlinks"), laws = json("laws");
const rules = Object.fromEntries(Object.entries(table.law_of_category).map(([id,ids]) => [id,ids.map(law=>({
  law, href:"rules.html#"+law, version:laws.season, title:laws.sections.find(x=>x.id===law).title
}))]));

function environment() {
  const hooks = {write:null, remove:null};
  const storage = Object.create(null);
  Object.defineProperties(storage, {
    setItem:{value(k,v) {if(hooks.write) hooks.write(k,v); this[k]=v;}},
    getItem:{value(k) {return Object.hasOwn(this,k) ? this[k] : null;}},
    removeItem:{value(k) {if(hooks.remove) hooks.remove(k); delete this[k];}}
  });
  const context = vm.createContext({TextEncoder,TextDecoder,URL,btoa,atob,crypto:webcrypto,localStorage:storage});
  const Model = vm.runInContext(program + "\nCoachModel", context);
  return {model:new Model(cases,lessons,rules), hooks, storage, context};
}
const plain = obj => JSON.parse(JSON.stringify(obj));
const example = (model, ids=["2026-1","2025-188"]) => ({...model.create("周五课堂"), items:ids.map(caseId=>({
  caseId, question:"观察什么？", scenario:"", note:"仅教练：暂缓展示第二角度"
}))});

test("private backup round-trip creates a new record, preserving order and notes", () => {
  const {model} = environment();
  const draft = example(model);
  draft.items.reverse();
  const original = model.save(draft);
  assert.ok(original.ok);
  const backup = model.backup(original.lesson);
  const imported = model.importBackup("\uFEFF"+backup);
  assert.ok(imported.ok);
  assert.notEqual(imported.lesson.id,original.lesson.id);
  assert.deepEqual(plain(imported.lesson.items), draft.items);
  assert.equal(model.list().length,2);
});

test("student output uses only public fields and neutral scenarios; review sources belong to selected cases", () => {
  const {model,context} = environment();
  // Public reading (including student link rendering) must not need any local storage access.
  Object.defineProperty(context, "localStorage", {get(){throw Error("禁用储存");},configurable:true});
  const lesson = example(model);
  lesson.items[0].question = '教练的公开问题 <b>示例</b> ⚽';
  const discussion = model.student(lesson);
  assert.equal(discussion.items[0].prompt,lessons[0].cases[0].prompt);
  assert.ok(discussion.items[1].prompt.includes("画面"));
  assert.equal(discussion.items[1].sources,undefined);
  const html = model.sheetHTML(discussion);
  assert.ok(html.startsWith("<!doctype html>"));
  assert.ok(html.includes("</head>") && html.endsWith("</body></html>"));
  assert.ok(!/<\/?(?:head|body|html)\b/i.test(program), "embedded module must not offer the host builder a false document boundary");
  assert.ok(html.includes("@media print") && html.includes("&lt;b&gt;示例&lt;/b&gt;"));
  const link = model.encodeShare(lesson);
  const decoded = Buffer.from(link.slice("#handout-".length),"base64url").toString("utf8");
  for (const text of [html,decoded,JSON.stringify(discussion)]) {
    assert.ok(!text.includes(lesson.items[0].note));
    assert.ok(!text.includes(cases["2026-1"].desc));
    assert.ok(!text.includes(cases["2025-188"].conclusion));
    assert.ok(!text.includes(cases["2025-188"].supplement.url));
  }
  assert.deepEqual(plain(model.decodeShare(link)), plain(discussion));
  const review = model.student(lesson,{review:true});
  assert.deepEqual(plain(review.items[1].sources.map(s=>s.issue)),[26,27]);
  assert.equal(review.items[1].rules[0].version,laws.season);
  const reviewed = model.handout(lesson,{review:true});
  assert.ok(reviewed.includes(cases["2025-188"].conclusion));
  assert.ok(reviewed.includes(cases["2025-188"].supplement.url));
  assert.ok(!reviewed.includes(lesson.items[1].note));
  assert.ok(!reviewed.includes(cases["2026-13"].conclusion));
  assert.deepEqual(plain(model.decodeShare(model.encodeShare(lesson,{review:true}))),plain(review));
  assert.equal(model.student(lesson,{review:"true"}).review,false);
  assert.equal(model.student(example(model,["2024-112"]),{review:true}).items[0].conclusion,"本期未单列评议结论，请查阅足协原文。");
});

test("custom scenario is public; empty private course can be saved, but cannot be shared", () => {
  const {model} = environment();
  const lesson = model.create("");
  assert.ok(model.save(lesson).ok);
  assert.throws(()=>model.handout(lesson),/至少一个/);
  lesson.items = [{caseId:"2026-1", scenario:"教练公开给出的中性场景", note:"私有草稿"}];
  const restored = model.decodeShare(model.encodeShare(lesson));
  assert.equal(restored.title,"未命名课单");
  assert.equal(restored.items[0].prompt,"教练公开给出的中性场景");
  assert.ok(restored.items[0].question);
});

test("unsupported files, invalid IDs, missing fields, duplicates and oversized fields never overwrite storage", () => {
  const {model,storage} = environment();
  model.save(example(model));
  const before = JSON.stringify(storage);
  const good = JSON.parse(model.backup(example(model)));
  for (const change of [
    x=>{x.version=99;}, x=>{x.format="student";}, x=>{delete x.lesson;},
    x=>{x.lesson.items[0].caseId="2026-99999";}, x=>{x.lesson.items[1]=x.lesson.items[0];},
    x=>{delete x.lesson.items[0].question;}, x=>{x.lesson.title=123;},
    x=>{x.lesson.items[0].note="超".repeat(4001);}, x=>{x.lesson.items[0].scenario=null;}
  ]) {
    const incoming = plain(good);
    change(incoming);
    assert.throws(()=>model.importBackup(JSON.stringify(incoming)));
    assert.equal(JSON.stringify(storage),before);
  }
  assert.throws(()=>model.importBackup("{"));
  for (const h of ["#other-A", "#handout-A", "#handout-**", "#handout-"+Buffer.from("[2,\"t\",false,[]]").toString("base64url")]) {
    assert.throws(()=>model.decodeShare(h));
  }
});

test("all different cases can be saved/exported, and genuinely overlong links offer a portable handout", () => {
  const {model} = environment();
  const lesson = {...model.create("全部判例"),items:Object.keys(cases).map(caseId=>({caseId,question:"情境问题".repeat(40)}))};
  assert.equal(lesson.items.length,model.maxItems);
  assert.ok(model.save(lesson).ok);
  assert.equal((model.handout(lesson).match(/<article class=/g)||[]).length,model.maxItems);
  assert.throws(()=>model.encodeShare(lesson),/HTML/);
  lesson.items.forEach(item=>{item.question="";});
  assert.equal(model.decodeShare(model.encodeShare(lesson)).items.length,model.maxItems);
});

test("quota failure preserves the saved version and all unsaved text for backup or retry", () => {
  const {model,hooks} = environment();
  const saved = model.save(example(model)).lesson;
  const edited = plain(saved);
  edited.items[0].note="未保存草稿";
  hooks.write=()=>{throw Error("模拟配额不足");};
  const failed = model.save(edited);
  assert.equal(failed.ok,false);
  assert.equal(failed.lesson.revision,saved.revision);
  assert.ok(model.backup(failed.lesson).includes("未保存草稿"));
  assert.equal(model.list()[0].items[0].note,saved.items[0].note);
  hooks.write=null;
  assert.ok(model.save(failed.lesson).ok);
  assert.equal(model.list()[0].items[0].note,"未保存草稿");
});

test("same-base simultaneous edits and later branch edits keep each presentation ID attached to its own class", () => {
  const {model,hooks} = environment();
  const original = model.save(example(model)).lesson;
  const a=plain(original), b=plain(original);
  a.items[0].note="分支 A";
  b.items[0].note="分支 B";
  hooks.write=()=>{hooks.write=null;model.save(b);};
  const saveA=model.save(a);
  const live=model.list();
  assert.equal(live.length,2);
  assert.equal(live.find(row=>row.id===saveA.lesson.id).items[0].note,"分支 A");
  const primary=live.find(r=>r.id===original.id), other=live.find(r=>r.id!==original.id);
  for (const branch of [primary,other]) {
    branch.items[0].note += " 已编辑";
    assert.ok(model.save(branch).ok);
    assert.equal(model.list().find(r=>r.id===branch.id).items[0].note,branch.items[0].note);
  }
  assert.equal(model.list().length,2);
  const stale=plain(original);
  stale.title="离线编写的另一版";
  const third=model.save(stale);
  assert.ok(third.ok && third.conflict);
  assert.equal(model.list().length,3);
});

test("a failed ancestor cleanup does not resurrect an obsolete draft on the next save", () => {
  const {model,hooks,storage} = environment();
  const first=model.save(example(model)).lesson;
  hooks.remove=()=>{throw Error("临时阻止清理");};
  first.title="第二版";
  const second=model.save(first).lesson;
  assert.equal(Object.keys(storage).length,2);
  assert.equal(model.list().length,1);
  hooks.remove=null;
  second.title="第三版";
  assert.ok(model.save(second).ok);
  assert.equal(model.list().length,1);
  assert.equal(model.list()[0].title,"第三版");
  assert.equal(Object.keys(storage).length,1);
});
