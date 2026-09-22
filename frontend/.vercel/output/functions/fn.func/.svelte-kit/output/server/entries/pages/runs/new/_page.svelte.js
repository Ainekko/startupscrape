import { c as create_ssr_component, e as escape } from "../../../../chunks/index.js";
const Page = create_ssr_component(($$result, $$props, $$bindings, slots) => {
  return `


${$$result.head += `<!-- HEAD_svelte-kvwauj_START -->${$$result.title = `<title>New Run — StartupScrape</title>`, ""}<!-- HEAD_svelte-kvwauj_END -->`, ""}

<div class="max-w-lg mx-auto mt-16 animate-fade-in"><div class="card p-8"><h1 class="text-xl font-semibold text-text-primary mb-1">New Pipeline Run</h1>
    <p class="text-sm text-text-secondary mb-6">Scrape YC companies, enrich with founder data, score with JEV, and find emails.</p>

    ${``}

    ${``}

    ${``}

    ${`<button ${""} class="${"btn-primary w-full justify-center py-2.5 " + escape("", true)}">${`<svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M2.5 2L10.5 6.5L2.5 11V2Z" fill="currentColor"></path></svg>
          Start Pipeline`}</button>`}

    <a href="/" class="btn-ghost w-full justify-center mt-3">← Back to runs</a></div></div>`;
});
export {
  Page as default
};
