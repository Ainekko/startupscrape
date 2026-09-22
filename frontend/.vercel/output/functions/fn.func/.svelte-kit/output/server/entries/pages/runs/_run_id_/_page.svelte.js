import { c as create_ssr_component, b as subscribe, e as escape, d as each } from "../../../../chunks/index.js";
import { p as page } from "../../../../chunks/stores.js";
const Page = create_ssr_component(($$result, $$props, $$bindings, slots) => {
  let leads;
  let $page, $$unsubscribe_page;
  $$unsubscribe_page = subscribe(page, (value) => $page = value);
  let sortBy = "tier1_score";
  let sortDir = -1;
  let filterCompetitor = false;
  leads = [];
  leads.filter((l) => !filterCompetitor).filter((l) => {
    return true;
  }).sort((a, b) => {
    const av = a[sortBy] ?? 0;
    const bv = b[sortBy] ?? 0;
    if (typeof av === "string")
      return sortDir * av.localeCompare(bv);
    return sortDir * (av - bv);
  });
  $$unsubscribe_page();
  return `


${$$result.head += `<!-- HEAD_svelte-do8nud_START -->${$$result.title = `<title>Run ${escape($page.params.run_id)} — StartupScrape</title>`, ""}<!-- HEAD_svelte-do8nud_END -->`, ""}

${`<div class="space-y-3">${each(Array(5), (_) => {
    return `<div class="card p-4 animate-pulse"><div class="h-4 bg-surface-4 rounded w-48 mb-2"></div>
        <div class="h-3 bg-surface-3 rounded w-80"></div>
      </div>`;
  })}</div>`}`;
});
export {
  Page as default
};
