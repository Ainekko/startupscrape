

export const index = 1;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/fallbacks/error.svelte.js')).default;
export const imports = ["_app/immutable/nodes/1.eb979ad8.js","_app/immutable/chunks/index.aa8ac873.js","_app/immutable/chunks/stores.ef6d2b8f.js","_app/immutable/chunks/singletons.62d1657c.js","_app/immutable/chunks/paths.4d3a54b2.js"];
export const stylesheets = [];
export const fonts = [];
