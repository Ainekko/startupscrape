

export const index = 1;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/fallbacks/error.svelte.js')).default;
export const imports = ["_app/immutable/nodes/1.dc97872e.js","_app/immutable/chunks/index.aa8ac873.js","_app/immutable/chunks/stores.4d877b9c.js","_app/immutable/chunks/singletons.8d582864.js","_app/immutable/chunks/paths.d49600e0.js"];
export const stylesheets = [];
export const fonts = [];
