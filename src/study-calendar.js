function studyDay(date) {
  const pad = number => String(number).padStart(2, "0");
  return [date.getFullYear(), pad(date.getMonth() + 1), pad(date.getDate())].join("-");
}
function previousStudyDay(date) {
  const previous = new Date(date);
  previous.setDate(previous.getDate() - 1);
  return studyDay(previous);
}
function currentStudyStreak(streak, date = new Date()) {
  if (!streak || ![studyDay(date), previousStudyDay(date)].includes(streak.last)) return 0;
  return Number.isSafeInteger(streak.days) && streak.days > 0 ? streak.days : 0;
}
function touchStudyDay(date = new Date()) {
  try {
    const record = JSON.parse(localStorage.getItem("cfa.streak") || "null");
    const today = studyDay(date);
    if (record && record.last === today) return;
    const days = currentStudyStreak(record, date) + 1;
    localStorage.setItem("cfa.streak", JSON.stringify({last: today, days}));
  } catch (_) {}
}
