const assert = require("node:assert/strict");
const {test} = require("node:test");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const {webcrypto} = require("node:crypto");
const source = fs.readFileSync(path.join(__dirname, "../src/quiz-records.js"), "utf8");

class StorageMock {
  getItem(key) { return this[key] ?? null; }
  setItem(key, value) { this[key] = String(value); }
  removeItem(key) { delete this[key]; }
}
const miss = id => ({id, miss:{t:"var",s:"ifab",your:0,correct:"官方答案"}});
function setup(locks) {
  const storage = new StorageMock();
  const Records = vm.runInNewContext(source + "\nQuizRecords", {crypto:webcrypto,navigator:{locks},localStorage:storage});
  return {storage,Records,a:new Records(storage),b:new Records(storage)};
}

test("legacy scale stats keep the local aggregate through imports and reloads", () => {
  const {a,b,storage,Records} = setup();
  Records.legacyScaleIds = new Set(["sc-2025-1","sc-2025-7"]);
  storage.setItem("cfa.quiz.stats",JSON.stringify({"sc-2025-1":{r:1,w:2}}));
  const change = {kind:"import",rows:{},legacyScaleStats:{"sc-2025-1":{r:5,w:6},"sc-2025-7":{r:2,w:1}}};
  a.write(change);
  b.write(change);
  assert.equal(JSON.stringify(a.read().stats),JSON.stringify({"sc-2025-1":{r:1,w:2},"sc-2025-7":{r:2,w:1}}));
  assert.equal(Object.keys(a.state.wrong).length,0);
  for (const legacyScaleStats of [null, {"sc-2025-1":{r:-1,w:2}}, {"var-1":{r:0,w:1}}, {"sc-2025-6":{r:1,w:1}}])
    assert.equal(Records.validEvent({...change,legacyScaleStats,time:1,order:1}),false);
  assert.equal(Records.validEvent({kind:"import",rows:{},time:1,order:1}),true);
});

test("simultaneous attempts retain both results, star and history on the same question without Web Locks", () => {
  const {a,b,storage,Records} = setup();
  const exam = {got:0,max:1,n:1};
  // Interrupt A after it observed the old state and before it writes. Both tabs
  // must therefore create entries with the same logical order.
  Object.defineProperty(storage,"setItem",{configurable:true,value(key,value) {
    delete this.setItem;
    b.write({kind:"attempt",answers:[miss("var-1")],exam});
    this.setItem(key,value);
  }});
  a.write({kind:"attempt",answers:[miss("var-1")],exam});
  const row = a.read();
  assert.equal(row.wrong["var-1"].wrong,2);
  assert.equal(row.stats["var-1"].w,2);
  assert.equal(row.history.length,2);
  a.write({kind:"star",id:"var-1",value:true});
  b.write({kind:"attempt",answers:[{id:"var-1"},miss("var-2")]});
  b.write({kind:"attempt",answers:[{id:"var-1"}]});
  assert.equal(Records.readWrong()["var-1"].stage,2);
  assert.equal(Records.readWrong()["var-1"].star,true);
  a.write({kind:"remove",ids:["var-1"]});
  b.write({kind:"star",id:"var-1",value:false});
  assert.deepEqual(Object.keys(a.read().wrong),["var-2"]);
  assert.equal(a.state.stats["var-1"].r,2);
});

test("legacy records, recent twenty exams and damaged siblings survive recovery", () => {
  const {a,storage} = setup();
  const raw = JSON.stringify({"var-good":{t:"var",star:true,correct:["旧答案"]},"var-bad":null});
  storage.setItem("cfa.quiz.wrong",raw);
  storage.setItem("cfa.quiz.stats",JSON.stringify({"var-good":{r:3,w:2},bad:{r:"x",w:1}}));
  storage.setItem("cfa.quiz.history",JSON.stringify([{t:1,got:1,max:2,n:2},null]));
  assert.equal(a.read().damaged,3);
  assert.equal(a.state.wrong["var-good"].correct,"旧答案");
  assert.equal(a.state.history.length,1);
  for (let i=1; i<=23; i++) a.write({kind:"attempt",answers:[{id:"var-good"}],exam:{got:i,max:30,n:30}});
  const state = a.read();
  assert.equal(state.history.length,20);
  assert.equal(state.history[0].got,23);
  assert.equal(state.history[19].got,4);
  assert.equal(state.stats["var-good"].r,26);
  assert.equal(state.wrong["var-good"].done,true);
  assert.equal(storage.getItem("cfa.quiz.wrong"),raw);
});

test("backup validation rejects mixed invalid rows, accepts older rows and ignores retired questions", () => {
  const {Records} = setup(), bank = {a:{t:"case",s:"2026"},b:{t:"scale",s:"2025"}};
  const wrong = {a:{t:"case",your:{r:null,v:"wrong"},star:true},b:null};
  assert.throws(()=>Records.importRows({wrong},bank),/b：/);
  assert.throws(()=>Records.importRows({wrong:[]},bank),/JSON/);
  assert.throws(()=>Records.importRows({app:"cfa-rules-2026",wrong:{}},bank),/JSON/);
  const rows = Records.importRows({wrong:{a:wrong.a,retired:{t:"case"}}},bank);
  assert.deepEqual(Object.keys(rows),["a"]);
  assert.equal(rows.a.t,"case");
  assert.equal(rows.a.s,"2026");
});

test("failed writes remain visible and retry exactly once; failed imports never mutate the draft", () => {
  const {storage,a} = setup();
  Object.defineProperty(storage,"setItem",{configurable:true,value() {throw Error("quota");}});
  assert.equal(a.write({kind:"attempt",answers:[miss("var-1")]}),false);
  assert.equal(a.read().stats["var-1"].w,1);
  assert.throws(()=>a.write({kind:"import",rows:{b:{t:"var"}}},false),/存储/);
  assert.equal(a.pending.size,1);
  assert.equal(a.read().wrong.b,undefined);
  delete storage.setItem;
  assert.equal(a.retry(),true);
  assert.equal(a.retry(),true);
  assert.equal(a.read().wrong["var-1"].wrong,1);
});

test("interrupted cleanup cannot duplicate old events when another tab compacts", async () => {
  const locks = {request:(_,options,cb)=>Promise.resolve().then(()=>cb({name:"lock"}))};
  const {a,b,storage} = setup(locks);
  const settled = () => new Promise(resolve => setImmediate(resolve));
  for (let i=0; i<64; i++) a.write({kind:"attempt",answers:[miss("var-1")]});
  Object.defineProperty(storage,"removeItem",{configurable:true,value() {throw Error("tab closed after checkpoint");}});
  a.write({kind:"attempt",answers:[miss("var-1")]});
  await settled();
  assert.equal(b.read().stats["var-1"].w,65);
  delete storage.removeItem;
  for (let i=0; i<65; i++) b.write({kind:"attempt",answers:[miss("var-1")]});
  await settled();
  assert.equal(a.read().stats["var-1"].w,130);
  assert.equal(Object.keys(storage).filter(k=>k.includes(".event.")).length,0);
});

test("a broken event is quarantined as a whole; the recovery export preserves original strings", () => {
  const {storage,a,b,Records} = setup();
  const bad1 = Records.prefix+"truncated", bad2 = Records.prefix+"bad-item";
  const incomplete = JSON.stringify({kind:"attempt",order:1,time:42,answers:[miss("var-q1"),null]});
  a.write({kind:"attempt",answers:[miss("var-q1")]});
  storage.setItem(bad1,"{");
  storage.setItem(bad2,incomplete);
  assert.equal(b.read().stats["var-q1"].w,1);
  assert.equal(b.damagedStorage,true);
  b.write({kind:"attempt",answers:[miss("var-q1")]});
  assert.equal(a.read().wrong["var-q1"].wrong,2);
  assert.equal(a.recoveryArchive().records[bad1],"{");
  assert.equal(a.recoveryArchive().records[bad2],incomplete);
});

test("an intact independent checkpoint recovers all compacted answers and subsequent events", async () => {
  const locks = {request:(_,options,cb)=>Promise.resolve().then(()=>cb({}))};
  const {a,b,storage,Records} = setup(locks);
  for (let i=0;i<64;i++) a.write({kind:"attempt",answers:[miss("var-q1")]});
  await new Promise(resolve=>setImmediate(resolve));
  const cp = storage.getItem(Records.checkpoint);
  assert.ok(cp);
  assert.equal(cp,storage.getItem(Records.recovery));
  assert.equal(Object.keys(storage).filter(k=>k.startsWith(Records.prefix)).length,0);
  const changed = JSON.parse(cp);
  changed.state.stats["var-q1"].w=99; // syntactically valid data, mismatched checksum
  const bad = JSON.stringify(changed);
  storage.setItem(Records.checkpoint,bad);
  b.write({kind:"attempt",answers:[miss("var-q1")]});
  assert.equal(a.read().stats["var-q1"].w,65);
  assert.equal(a.damagedStorage,true);
  await a.compact();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(storage.getItem(Records.checkpoint),bad);
  assert.equal(a.recoveryArchive().records[Records.checkpoint],bad);
});

test("partial checkpoints without coverage metadata preserve identifiable counts without counting overlapping events twice", () => {
  const {a,storage,Records} = setup();
  a.write({kind:"attempt",answers:[miss("var-q1")]});
  const partial = JSON.stringify({state:{stats:{"var-q1":{r:0,w:1},"var-q2":{r:4,w:6}},
    wrong:{"var-q2":{t:"var",wrong:6},bad:null}}});
  storage.setItem(Records.checkpoint,partial);
  assert.equal(a.read().stats["var-q1"].w,1);
  assert.equal(a.state.stats["var-q2"].w,6);
  a.write({kind:"attempt",answers:[miss("var-q2")]});
  assert.equal(a.read().stats["var-q2"].w,7);
  assert.equal(a.read().wrong["var-q2"].wrong,7);
  assert.equal(a.recoveryArchive().records[Records.checkpoint],partial);
});

test("unreadable storage cannot acknowledge a retry; confirmation after compaction does not replay the draft twice", async () => {
  const locks = {request:(_,options,cb)=>Promise.resolve().then(()=>cb({}))};
  const {a,b,storage} = setup(locks);
  Object.defineProperty(storage,"setItem",{configurable:true,value() {throw Error("quota");}});
  a.write({kind:"attempt",answers:[miss("var-q1")]});
  delete storage.setItem;
  const blockRead = () => Object.defineProperty(storage,"getItem",{configurable:true,value() {throw Error("read blocked");}});
  blockRead();
  assert.equal(a.retry(),false);
  assert.equal(a.pending.size,1);
  assert.equal(a.read().stats["var-q1"].w,1);
  assert.equal(a.recoveryArchive().pending[Array.from(a.pending.keys())[0]].kind,"attempt");
  delete storage.getItem;
  Object.defineProperty(storage,"setItem",{configurable:true,value(key,value) {
    delete this.setItem; this.setItem(key,value); blockRead();
  }});
  assert.equal(a.retry(),false);
  assert.equal(a.pending.size,1);
  delete storage.getItem;
  for(let i=0;i<64;i++) b.write({kind:"attempt",answers:[miss("var-q1")]});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(a.retry(),true);
  assert.equal(a.pending.size,0);
  assert.equal(a.read().stats["var-q1"].w,65);
});

test("insufficient quota for redundant checkpoints preserves all events and reclaims the temporary copy", async () => {
  const locks = {request:(_,options,cb)=>Promise.resolve().then(()=>cb({}))};
  const {a,storage,Records} = setup(locks);
  Object.defineProperty(storage,"setItem",{configurable:true,value(key,value) {
    if(key===Records.checkpoint) throw Error("quota");
    StorageMock.prototype.setItem.call(this,key,value);
  }});
  for(let i=0;i<64;i++) a.write({kind:"attempt",answers:[miss("var-q1")]});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(storage.getItem(Records.recovery),null);
  assert.equal(Object.keys(storage).filter(k=>k.startsWith(Records.prefix)).length,64);
  assert.equal(a.read().stats["var-q1"].w,64);
});
