import * as universal from '../entries/pages/runs/_run_id_/_page.js';

export const index = 4;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/runs/_run_id_/_page.svelte.js')).default;
export { universal };
export const universal_id = "src/routes/runs/[run_id]/+page.js";
export const imports = ["_app/immutable/nodes/4.29ffefd8.js","_app/immutable/chunks/index.aa8ac873.js","_app/immutable/chunks/stores.4d877b9c.js","_app/immutable/chunks/singletons.8d582864.js","_app/immutable/chunks/paths.d49600e0.js","_app/immutable/chunks/pipeline.be248491.js","_app/immutable/chunks/LeadRow.54ff308b.js"];
export const stylesheets = [];
export const fonts = [];
