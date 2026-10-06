<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import Nav from '$lib/components/Nav.svelte';
  import PipelineEconomics from '$lib/components/PipelineEconomics.svelte';
  import { api } from '$lib/api';

  const PUBLIC = ['/login', '/pitch'];
  $: isPublic = PUBLIC.some(p => $page.url.pathname === p || $page.url.pathname.startsWith(p + '/'));

  // Redirect to login if not authenticated on protected pages
  onMount(() => {
    if (!isPublic && !api.auth.isLoggedIn()) {
      goto('/login');
    }
  });
</script>

{#if isPublic}
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
