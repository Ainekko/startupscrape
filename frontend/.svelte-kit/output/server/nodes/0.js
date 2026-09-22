

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_layout.svelte.js')).default;
export const imports = ["_app/immutable/nodes/0.2ea1f3a8.js","_app/immutable/chunks/index.aa8ac873.js","_app/immutable/chunks/stores.ef6d2b8f.js","_app/immutable/chunks/singletons.62d1657c.js","_app/immutable/chunks/paths.4d3a54b2.js"];
export const stylesheets = ["_app/immutable/assets/0.7a179b41.css"];
export const fonts = [];
