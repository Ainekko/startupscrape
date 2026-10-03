<script>
  import '../app.css';
  import Nav from '$lib/components/Nav.svelte';
  import PipelineEconomics from '$lib/components/PipelineEconomics.svelte';
</script>

<div class="min-h-screen flex flex-col bg-surface-0">
  <Nav />
  <main class="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
    <slot />
  </main>
  <footer class="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 pb-6">
    <PipelineEconomics />
  </footer>
</div>
