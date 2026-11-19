// Use the same bundled shader offline, including when index.html is opened
// on its own and the browser disallows imports from neighboring file: URLs.
const photo = document.querySelector('[data-moment="liquid-hover"]');
async function inlineRipple() {
  if (!photo) return;
  const [{default: mount}, helpers] = await Promise.all([
    import("__LIQUID_MODULE__"), import("__MOTION_HELPERS__")
  ]);
  mount(photo, {}, {...helpers, reduced: helpers.still});
}
if (/^https?:$/.test(location.protocol)) {
  try {
    const runtime = await import("./assets/portal/moments/moments.js");
    await runtime.ready;
    if (photo?.dataset.momentFailed) await inlineRipple();
  } catch { await inlineRipple(); }
} else {
  await inlineRipple();
}
