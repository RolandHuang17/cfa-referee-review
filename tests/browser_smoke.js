// playwright-cli run-code --filename tests/browser_smoke.js
async (page) => {
  const base = new URL(page.url()).origin;
  function check(condition, message) {
    if (!condition) throw new Error(message);
  }
  await page.goto(base + '/quiz.html');
  await page.getByRole('button', { name: '规则理论', exact: true }).click();
  await page.getByRole('button', { name: '考试（做完统一出分）', exact: true }).click();
  await page.locator('#segCount button[data-v="5"]').click();
  await page.locator('#btnStart').click();
  const display = await page.evaluate(() => round.qs[0]._disp);
  const right = display.indexOf(0);
  const wrong = (right + 1) % display.length;
  await page.locator('#qForm .opt').nth(wrong).click();
  await page.locator('#qForm .opt').nth(right).click();
  check(await page.locator('#qForm .opt.on').count() === 1, '理论题改选后仍有多项选中');
  await page.locator('#btnSubmit').click();
  await page.locator('#btnPrev').click();
  check(await page.evaluate(() => currentAnswer()) === 0, '原始答案下标0在返回时丢失');
  await page.keyboard.press(String(right + 1));
  check(await page.evaluate(() => currentAnswer()) === 0, '数字键没有使用显示顺序');
  const scores = await page.evaluate(() => {
    const questions = DATA.bank.filter(q => q.t === 'scale');
    const q = questions.find(q => q.dec.filter(d => d.active).length > 1);
    const active = q.dec.filter(d => d.active).map(d => d.label);
    const bad = q.dec.find(d => !d.active).label;
    return {
      blank: questions.map(q => scoreScale(q, []).got),
      partial: scoreScale(q, active.slice(0, 1)).got,
      wrong: scoreScale(q, [bad]).got,
      full: scoreScale(q, active).got,
    };
  });
  check(scores.blank.every(x => x === 0), '尺度空答获得分数');
  check(scores.partial === 1 && scores.wrong === 0 && scores.full === 2, '尺度多选分值异常');
  await page.evaluate(() => {
    sel.mode = 'practice'; sel.count = 1; sel.timer = 'off';
    startRound([DATA.bank.find(q => q.t === 'scale')]);
    window.statBefore = (qstats[round.qs[0].k]?.w || 0);
  });
  await page.locator('#btnSubmit').click();
  check(await page.evaluate(() => round.scores[0].got === 0 && round.scores[0].max === 2), '练习空答分数错误');
  await page.locator('#btnSubmit').click();
  check(await page.evaluate(() => qstats[round.qs[0].k].w === window.statBefore + 1), '练习重复记录作答');
  await page.evaluate(() => {
    sel.mode = 'exam';
    startRound([DATA.bank.find(q => q.t === 'scale')]);
    window.statBefore = (qstats[round.qs[0].k]?.w || 0);
  });
  await page.locator('#qForm .opt').first().click();
  // 考试界面不展示跳过按钮，同时验证内部末题跳过的防御分支。
  await page.evaluate(() => skipQuestion());
  await page.locator('#scrResult').waitFor();
  check(await page.evaluate(() => round.finished && round.scores[0].got === 0 && round.scores[0].max === 2 && round.answers[0].length === 0), '末题跳过没有按空答交卷');
  await page.evaluate(() => { finishExam(); finishExam(); });
  check(await page.evaluate(() => qstats[round.qs[0].k].w === window.statBefore + 1), '交卷重复记录作答');
  await page.evaluate(() => {
    startRound([DATA.bank.find(q => q.t === 'scale')]);
    window.statBefore = (qstats[round.qs[0].k]?.w || 0);
  });
  await page.locator('#btnSubmit').click();
  await page.locator('#scrResult').waitFor();
  check(await page.evaluate(() => round.finished && round.scores[0].got === 0 && round.scores[0].max === 2 && new QuizRecords().state.stats[round.qs[0].k].w === window.statBefore + 1), '考试手动空答交卷错误');
  await page.evaluate(() => {
    startRound([DATA.bank.find(q => q.t === 'scale')]);
    window.alert = message => { window.timerMessage = message; };
    window.statBefore = (qstats[round.qs[0].k]?.w || 0);
    startTimer(1);
  });
  await page.waitForFunction(() => round.finished && window.timerMessage?.includes('时间到'));
  check(await page.evaluate(() => round.scores[0].got === 0 && round.scores[0].max === 2 && qstats[round.qs[0].k].w === window.statBefore + 1), '超时空答分数或次数错误');
  check(await page.evaluate(() => ['var','theory'].every(t => {
    const q = DATA.bank.find(q => q.t === t);
    const s = t === 'var' ? scoreVar(q, null) : scoreTheory(q, null);
    return s.got === 0 && s.detail[0].yours === '（未答）';
  })), '单选题空答被显示为第一选项');
  await page.goto(base + '/search.html?q=' + encodeURIComponent('掷物'));
  const law = page.locator('#sres a[href*="rules.html#law-12-p-"]').first();
  check(await law.count() === 1, '搜索遗漏第十二章尾段');
  await law.click();
  check(await page.locator('#secTitle').innerText() === '第十二章 犯规与不正当行为', '规则定位章节错误');
  check(await page.evaluate(() => !!document.getElementById(decodeURIComponent(location.hash.slice(1)))), '规则目标段落不存在');
  await page.goto(base + '/scale.html#s2025-0-2');
  check(await page.locator('.season-tab.on').getAttribute('data-season') === '2025', '分组链接未切换2025页签');
  check(await page.locator('#s2025-0-2').isVisible(), '尺度目标分组不可见');
  await page.evaluate(() => location.hash = 's2024-0-2');
  await page.waitForFunction(() => document.querySelector('.season-tab.on').dataset.season === '2024');
  const links = await page.evaluate(() => Array.from(document.querySelectorAll('.gnav')).map(a => a.hash));
  for (const hash of links) {
    await page.evaluate(h => location.hash = h, hash);
    await page.waitForFunction(h => !!document.querySelector(h)?.getClientRects().length, hash);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(base + '/season-2026.html?case=229&hideans=1');
  check(await page.locator('#ansGate').isVisible(), '手机挑战模式提前显示答案');
  await page.locator('#ansRevealBtn').click();
  check(!(await page.locator('#ansGate').isVisible()), '手机揭示答案失败');
  if (!(await page.evaluate(() => document.documentElement.dataset.lite === '1'))) {
    await page.locator('#btnLite').click();
  }
  await page.locator('#noteBox').fill('手机专项笔记 [00:07]');
  await page.waitForFunction(() => JSON.parse(localStorage.getItem('cfa2026.notes') || '{}')['229']?.text === '手机专项笔记 [00:07]');
  await page.reload();
  check(await page.locator('#noteBox').inputValue() === '手机专项笔记 [00:07]', '手机刷新丢失笔记');
  await page.locator('#btnSb').click();
  check(await page.evaluate(() => document.body.classList.contains('sb-open')), '手机筛选抽屉未打开');
  await page.keyboard.press('Escape');
  check(await page.evaluate(() => !document.body.classList.contains('sb-open') && document.activeElement.id === 'btnSb'), '关闭抽屉未还原焦点');
  await page.evaluate(() => { window.alert = message => { window.importMessage = message; }; });
  await page.locator('#importFile').setInputFiles({
    name:'旧版笔记.json', mimeType:'application/json',
    buffer:Buffer.from(JSON.stringify({app:'cfa-referee-review-2026',notes:{'229':{text:'旧版导入笔记',ts:Date.now()+10000}},fav:{'229':{tags:['精选'],ts:Date.now()}}})),
  });
  await page.waitForFunction(() => window.importMessage?.includes('导入完成'));
  check(await page.locator('#noteBox').inputValue() === '旧版导入笔记', '导入后笔记未即时更新');
  const caseExport = await page.evaluate(async () => {
    const original = URL.createObjectURL.bind(URL);
    URL.createObjectURL = blob => { window.exportBlob = blob; return original(blob); };
    const note = document.getElementById('noteBox');
    note.value = '输入后立即导出'; note.dispatchEvent(new Event('input', {bubbles:true}));
    document.getElementById('btnExport').click();
    return JSON.parse(await window.exportBlob.text());
  });
  check(caseExport.notes['229'].text === '输入后立即导出', '判例导出遗漏未完成防抖的笔记');
  await page.goto(base + '/rules.html#law-12');
  await page.evaluate(() => { window.alert = message => { window.importMessage = message; }; });
  const oldRules = {
    app:'cfa-rules-2026',
    notes:{'law-12':{text:'旧规则章节笔记',ts:Date.now()+10000}},
    highlights:[
      {sec:'law-12',quote:'掷物',color:'y',ts:101},
      {sec:'law-12',quote:'这是一条仍需回查的旧高亮引文',color:'r',ts:102},
    ],
  };
  await page.locator('#importFileN').setInputFiles({name:'旧规则笔记.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(oldRules))});
  await page.waitForFunction(() => window.importMessage?.includes('导入完成'));
  check(await page.locator('#secNote').inputValue() === '旧规则章节笔记', '旧规则笔记未恢复到章节');
  check(await page.locator('#secHtml mark.hl').count() > 0, '旧规则高亮未定位');
  await page.locator('#hlMissing summary').click();
  check((await page.locator('#hlMissingQuotes').innerText()).includes('仍需回查的旧高亮引文'), '未定位引文无法查看');
  await page.evaluate(() => applyHl());
  check(await page.locator('mark.hl mark.hl').count() === 0, '重绘后高亮发生嵌套');
  const rulesExport = await page.evaluate(async () => {
    const original = URL.createObjectURL.bind(URL);
    URL.createObjectURL = blob => { window.exportBlob = blob; return original(blob); };
    const note = document.getElementById('secNote');
    note.value = '规则输入后立即导出'; note.dispatchEvent(new Event('input', {bubbles:true}));
    document.getElementById('btnExportN').click();
    return JSON.parse(await window.exportBlob.text());
  });
  check(rulesExport.notes['law-12'].text === '规则输入后立即导出', '规则导出遗漏未完成防抖的笔记');
  check(rulesExport.highlights.some(h=>h.ts===102), '未定位的旧引文没有保留导出');
  await page.setViewportSize({ width: 1440, height: 960 });
  return 'PASS 判分/单次记分/空答/搜索/尺度深链/手机挑战/焦点/旧笔记高亮迁移/即时导出';
}
