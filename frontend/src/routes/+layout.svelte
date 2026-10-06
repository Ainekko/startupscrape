<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import Nav from '$lib/components/Nav.svelte';
  import PipelineEconomics from '$lib/components/PipelineEconomics.svelte';
  import { api } from '$lib/api';

  // /pitch renders standalone (no nav/footer), everything else uses the shell
  const STANDALONE = ['/pitch'];
  $: isStandalone = STANDALONE.some(p => $page.url.pathname === p || $page.url.pathname.startsWith(p + '/'));

  // Redirect unauthenticated users to login (skip for /login and /pitch)
  const NO_AUTH = ['/login', '/pitch'];
  $: isNoAuth = NO_AUTH.some(p => $page.url.pathname === p || $page.url.pathname.startsWith(p + '/'));

  onMount(() => {
    if (!isNoAuth && !api.auth.isLoggedIn()) {
      goto('/login');
    }
  });
</script>

{#if isStandalone}
  <slot />
{:else}
  <div class="min-h-screen flex flex-col bg-surface-0">
    <Nav />
    <main class="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
      <slot />
    </main>
    <footer class="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 pb-6">
      <PipelineEconomics />
    </footer>
  </div>
{/if}
