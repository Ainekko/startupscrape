<!-- StatusBar.svelte — Active run status bar, warm palette -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { api } from '$lib/api';
  import type { RunStatus } from '$lib/types';

  let status: RunStatus = { status: 'running' };
  let interval: ReturnType<typeof setInterval>;

  async function poll() {
    try { status = await api.pipeline.getStatus(); } catch {}
  }

  onMount(() => { interval = setInterval(poll, 3000); });
  onDestroy(() => clearInterval(interval));
</script>

<div class="mb-6 card px-5 py-3 flex items-center gap-3 border-orange-200 bg-orange-50/50">
  <span class="w-2 h-2 rounded-full bg-[#f97316] animate-pulse flex-shrink-0"></span>
  <div class="flex-1 min-w-0">
    <p class="text-sm text-text-primary font-medium">
      {#if status.status === 'running'}
        Pipeline running…
      {:else if status.status === 'done' && status.run_id}
        Run complete — <a href="/runs/{status.run_id}" class="text-[#c2410c] hover:underline font-semibold">view results</a>
      {:else if status.status === 'error'}
        Run failed: {status.error}
      {:else}
        Idle
      {/if}
    </p>
  </div>
  {#if status.status === 'running'}
    <div class="flex gap-1">
      <div class="w-1 h-3 bg-[#f97316] rounded-full animate-bounce" style="animation-delay:0ms"></div>
      <div class="w-1 h-3 bg-[#f97316]/70 rounded-full animate-bounce" style="animation-delay:100ms"></div>
      <div class="w-1 h-3 bg-[#f97316]/40 rounded-full animate-bounce" style="animation-delay:200ms"></div>
    </div>
  {/if}
</div>
