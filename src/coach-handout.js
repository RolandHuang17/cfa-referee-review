// An offline handout has no runtime or data attachment. Its body is also used by the in-app student view.
const CoachHandout = (() => {
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
  })[c]);

  function absoluteHTTP(value) {
    try {
      const url = new URL(value);
      return ["https:","http:"].includes(url.protocol) ? url.href : null;
    } catch (_) { return null; }
  }

  function ruleLink(rule, standalone) {
    const label = esc(rule.title) + "（" + esc(rule.version) + "）";
    if (!/^rules\.html#[\w-]+$/.test(rule.href)) return label;
    let href = rule.href;
    if (standalone) {
      // A handout can sit anywhere on disk. Its text and citations always work offline.
      const canonical = globalThis.document?.querySelector('link[rel="canonical"]')?.href;
      if (!absoluteHTTP(canonical)) return label;
      href = new URL(rule.href, canonical).href;
    }
    return '<a href="' + esc(href) + '">' + label + '</a>';
  }

  function sourceLink(source) {
    const label = esc(source.label), href = absoluteHTTP(source.url);
    const date = String(source.date || "").replace(/^(\d{4})(\d{2})(\d{2})$/,"$1-$2-$3");
    return (href ? '<a href="' + esc(href) + '">' + label + '</a>' : label) + (date ? ' · ' + esc(date) : '');
  }

  function body(sheet, standalone=false) {
    const review = sheet.review === true;
    const items = sheet.items.map((item,i) => {
      const evidence = review ? '<h3>足协评议认定</h3><blockquote>' + esc(item.conclusion) + '</blockquote>' +
        '<p class="coach-handout-sources">' + item.sources.map(sourceLink).join('　') + '</p>' +
        (item.rules.length ? '<p>现行规则参考 · ' + item.rules.map(rule => ruleLink(rule,standalone)).join('　') + '</p>' : '') : '';
      return '<article class="coach-handout-item"><header><p>' + esc(item.citation) + '</p><h2>' + (i+1) + '. ' +
        esc(item.match) + '</h2></header><p class="coach-handout-text">' + esc(item.prompt) + '</p><h3>课堂问题</h3><p class="coach-handout-text">' +
        esc(item.question) + '</p>' + evidence + '</article>';
    });
    return '<header class="coach-handout-header"><p>' + (review ? "复盘版" : "讨论版") + ' · ' + items.length +
      ' 个判例</p><h1>' + esc(sheet.title) + '</h1></header>' + items.join("");
  }

  // Keep document delimiters inside the emitted handout, outside the host template pass.
  function documentHTML(sheet) {
    return '\x3c!doctype html>\x3chtml lang="zh-CN">\x3chead>\x3cmeta charset="utf-8">\x3cmeta name="viewport" content="width=device-width,initial-scale=1">' +
      '\x3cmeta name="referrer" content="no-referrer">\x3ctitle>' + esc(sheet.title) + '\x3c/title>\x3cstyle>' +
      '*,*::before,*::after{box-sizing:border-box}html{color:#172622;background:#f4f2eb;font:17px/1.65 system-ui,sans-serif}body{margin:0}main,nav{max-width:52rem;margin:auto;padding:1rem clamp(1rem,5vw,3rem)}' +
      'nav{text-align:right}button{font:inherit;color:inherit;background:#fff;border:1px solid #66726a;border-radius:.3em;padding:.4em 1em;cursor:pointer}' +
      'h1,h2,h3{line-height:1.28;margin:0 0 .6em}h1{font-size:clamp(1.8rem,5vw,3rem)}h2{font-size:1.4rem}h3{font-size:1.05rem;margin-top:1.4em}' +
      'p,blockquote{margin:.45em 0 .9em}a{color:#07564c;text-underline-offset:.15em}main{overflow-wrap:anywhere}.coach-handout-text,blockquote{white-space:pre-wrap}' +
      '.coach-handout-item{padding:1.5rem 0;border-top:1px solid #a4aaa0}.coach-handout-item header p,.coach-handout-header>p{color:#47584e}.coach-handout-header{margin-bottom:1.5rem}' +
      'blockquote{padding-left:1rem;border-left:3px solid #6b8374}@media(scripting:none){nav button{display:none}}@page{margin:16mm}@media print{html{font-size:11pt;background:white;color:black}nav{display:none}main{padding:0;max-width:none}' +
      'h1,h2,h3,header{break-after:avoid}.coach-handout-item{padding:1rem 0}p,blockquote{orphans:3;widows:3}a{color:inherit}}' +
      '\x3c/style>\x3c/head>\x3cbody><nav aria-label="讲义操作"><button type="button" onclick="window.print()">打印讲义</button><noscript>可从浏览器菜单打印讲义或另存为 PDF。</noscript></nav><main>' +
      body(sheet,true) + '</main>\x3c/body>\x3c/html>';
  }

  return {body, document:documentHTML};
})();
