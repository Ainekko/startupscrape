<!-- StatusBar.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { pipelineApi } from '$lib/api/pipeline';
  import type { RunStatus } from '$lib/api/pipeline';

  let status: RunStatus = { status: 'running' };
  let interval: ReturnType<typeof setInterval>;

  async function poll() {
    try { status = await pipelineApi.getStatus(); } catch {}
  }

  onMount(() => { interval = setInterval(poll, 3000); });
  onDestroy(() => clearInterval(interval));
</script>

<div class="mb-6 card px-5 py-3 flex items-center gap-3 border-accent/20 bg-accent/5">
  <span class="w-2 h-2 rounded-full bg-accent animate-pulse flex-shrink-0"></span>
  <div class="flex-1 min-w-0">
    <p class="text-sm text-text-primary font-medium">
      {#if status.status === 'running'}
        Pipeline running…
      {:else if status.status === 'done' && status.run_id}
        Run complete — <a href="/runs/{status.run_id}" class="text-accent hover:underline">view results</a>
      {:else if status.status === 'error'}
        Run failed: {status.error}
      {:else}
        Idle
      {/if}
    </p>
  </div>
  {#if status.status === 'running'}
    <div class="flex gap-1">
      <div class="w-1 h-3 bg-accent rounded-full animate-bounce" style="animation-delay:0ms"></div>
      <div class="w-1 h-3 bg-accent/70 rounded-full animate-bounce" style="animation-delay:100ms"></div>
      <div class="w-1 h-3 bg-accent/40 rounded-full animate-bounce" style="animation-delay:200ms"></div>
    </div>
  {/if}
</div>
