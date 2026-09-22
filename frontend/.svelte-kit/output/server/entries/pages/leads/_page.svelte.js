import { c as create_ssr_component, f as add_attribute, e as escape, d as each } from "../../../chunks/index.js";
const Page = create_ssr_component(($$result, $$props, $$bindings, slots) => {
  let filtered;
  let leads = [];
  let search = "";
  let sortBy = "tier1_score";
  let sortDir = -1;
  let filterCompetitor = false;
  filtered = leads.filter((l) => !filterCompetitor).filter((l) => {
    return true;
  }).sort((a, b) => {
    const av = a[sortBy] ?? 0;
    const bv = b[sortBy] ?? 0;
    if (typeof av === "string")
      return sortDir * av.localeCompare(bv);
    return sortDir * (av - bv);
  });
  return `


${$$result.head += `<!-- HEAD_svelte-1rmntao_START -->${$$result.title = `<title>All Leads — StartupScrape</title>`, ""}<!-- HEAD_svelte-1rmntao_END -->`, ""}

<div class="animate-fade-in"><div class="flex items-start justify-between mb-6"><div><h1 class="text-2xl font-semibold text-text-primary tracking-tight">All Leads</h1>
      <p class="text-sm text-text-secondary mt-1">Deduplicated across all pipeline runs</p></div>
    ${``}</div>

  
  <div class="flex items-center gap-3 mb-4"><div class="flex-1 relative"><svg class="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted w-3.5 h-3.5" viewBox="0 0 16 16" fill="none"><circle cx="6.5" cy="6.5" r="5" stroke="currentColor" stroke-width="1.5"></circle><path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"></path></svg>
      <input type="text" placeholder="Search leads…" class="w-full pl-9 pr-4 py-2 bg-surface-2 border border-border rounded-lg text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent/40 transition-colors"${add_attribute("value", search, 0)}></div>
    <label class="flex items-center gap-2 text-sm text-text-secondary cursor-pointer select-none"><input type="checkbox" class="rounded accent-accent w-3.5 h-3.5"${add_attribute("checked", filterCompetitor, 1)}>
      Hide competitors
    </label>
    <span class="text-xs text-text-muted">${escape(filtered.length)} shown</span></div>

  ${`<div class="space-y-3">${each(Array(6), (_) => {
    return `<div class="card p-4 animate-pulse"><div class="h-4 bg-surface-4 rounded w-48 mb-2"></div>
          <div class="h-3 bg-surface-3 rounded w-80"></div>
        </div>`;
  })}</div>`}</div>`;
});
export {
  Page as default
};
