

export const index = 3;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/leads/_page.svelte.js')).default;
export const imports = ["_app/immutable/nodes/3.0f5b6971.js","_app/immutable/chunks/index.aa8ac873.js","_app/immutable/chunks/LeadRow.54ff308b.js"];
export const stylesheets = [];
export const fonts = [];
