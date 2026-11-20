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
