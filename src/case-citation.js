// Shared links must also be usable when copied from another person's offline copy.
function caseShareLink(season, seq, canonical, hideAnswer) {
  const page = canonical && /^https?:\/\//i.test(canonical) ? canonical : "season-" + season + ".html";
  return page + (hideAnswer ? "?case=" + seq + "&hideans=1" : "") + "#case-" + seq;
}

function citationDate(value) {
  return value.replace(/^(\d{4})(\d{2})(\d{2})$/, "$1-$2-$3");
}

function formatCaseCitation(data, item, canonical, showDecision) {
  const season = data.cfg.season;
  const title = [item.comp, item.round, [item.home, item.away].filter(Boolean).join(" 对 ")].filter(Boolean).join(" · ");
  const lines = ["中国足球协会 · " + season + " 赛季裁判评议 · 第 " + item.issue + " 期 · 判例 " + item.no];
  if (title) lines.push(title);

  function source(issueNo, label) {
    const issue = data.issues[issueNo];
    return label + "（" + citationDate(issue.date) + "） " + issue.url;
  }
  // A copied file:// link points to the teacher's own machine. Use the site's
  // public canonical URL when present, and a portable relative path otherwise.
  const publicPage = canonical && /^https?:\/\//i.test(canonical) ? canonical : "";
  const deepLink = caseShareLink(season, item.seq, publicPage, !showDecision);
  if (showDecision) {
    if (item.conclusion) {
      lines.push("", "足协评议组认定", item.conclusion);
    } else {
      lines.push("", "本案未单列评议认定，请查阅当期足协原文。");
    }
    const rule = item.rule_context;
    if (rule?.edition) {
      lines.push("", "比赛当日执行版本参考 · " + rule.edition + "（比赛日期 " + rule.date + "）");
      if (rule.source) lines.push("执行依据 " + rule.source);
    } else {
      lines.push("", "比赛当日适用规则版本待核");
    }
    const laws = data.xlinks[item.category]?.laws || [];
    for (const law of laws) {
      const target = publicPage ? new URL(law.url, publicPage).href : law.url;
      lines.push("现行规则参考 · " + data.rulebookEdition + " · " + law.title + " " + target);
    }
  }
  lines.push("", source(item.issue, "第 " + item.issue + " 期足协原文"));
  if (item.supplementIssue) lines.push(source(item.supplementIssue, "第 " + item.supplementIssue + " 期补充认定"));
  lines.push("平台判例 " + deepLink);
  return lines.join("\n");
}
