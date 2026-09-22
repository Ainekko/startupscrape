import { c as create_ssr_component, e as escape, d as each } from "../../chunks/index.js";
const Page = create_ssr_component(($$result, $$props, $$bindings, slots) => {
  let totalLeads;
  let totalSpend;
  let runs = [];
  totalLeads = runs.reduce((s, r) => s + (r.lead_count || 0), 0);
  totalSpend = runs.reduce((s, r) => s + (r.spend?.total_usd || 0), 0);
  return `


${$$result.head += `<!-- HEAD_svelte-14giolq_START -->${$$result.title = `<title>StartupScrape — Runs</title>`, ""}<!-- HEAD_svelte-14giolq_END -->`, ""}

<div class="animate-fade-in">
  <div class="flex items-start justify-between mb-8"><div><h1 class="text-2xl font-semibold text-text-primary tracking-tight">Pipeline Runs</h1>
      <p class="text-sm text-text-secondary mt-1">YC startup lead enrichment &amp; scoring</p></div>
    <div class="flex items-center gap-3">${`<button class="btn-primary"><svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M2.5 2L10.5 6.5L2.5 11V2Z" fill="currentColor"></path></svg>
          Run Pipeline
        </button>`}</div></div>

  ${``}

  
  ${runs.length > 0 ? `<div class="grid grid-cols-3 gap-4 mb-8"><div class="card px-5 py-4"><p class="label mb-1">Total runs</p>
        <p class="text-2xl font-semibold text-text-primary">${escape(runs.length)}</p></div>
      <div class="card px-5 py-4"><p class="label mb-1">Leads qualified</p>
        <p class="text-2xl font-semibold text-accent">${escape(totalLeads)}</p></div>
      <div class="card px-5 py-4"><p class="label mb-1">Total spend</p>
        <p class="text-2xl font-semibold text-text-primary">$${escape(totalSpend.toFixed(3))}</p></div></div>` : ``}

  
  ${`<div class="space-y-3">${each(Array(3), (_) => {
    return `<div class="card p-5 animate-pulse"><div class="h-4 bg-surface-4 rounded w-40 mb-3"></div>
          <div class="h-3 bg-surface-3 rounded w-64"></div>
        </div>`;
  })}</div>`}</div>`;
});
export {
  Page as default
};
