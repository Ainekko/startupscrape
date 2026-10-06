<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import Nav from '$lib/components/Nav.svelte';
  import PipelineEconomics from '$lib/components/PipelineEconomics.svelte';
  import { api } from '$lib/api';

  // Redirect to login if not authenticated (skip on /login itself)
  onMount(() => {
    if ($page.url.pathname !== '/login' && !api.auth.isLoggedIn()) {
      goto('/login');
    }
  });
</script>

{#if $page.url.pathname === '/login'}
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
