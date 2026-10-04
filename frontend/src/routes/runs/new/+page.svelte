<!-- /runs/new/+page.svelte — Trigger a new pipeline run, warm palette -->
<script lang="ts">
  import { api } from '$lib/api';
  import GrokBot from '$lib/components/GrokBot.svelte';

  let running = false;
  let error: string | null = null;
  let status: string | null = null;
  let runId: string | null = null;

  async function startRun() {
    running = true;
    error = null;
    try {
      await api.pipeline.startRun();
      status = 'running';
      poll();
    } catch (e: any) {
      error = e.message;
      running = false;
    }
  }

  function poll() {
    const iv = setInterval(async () => {
      try {
        const s = await api.pipeline.getStatus();
        if (s.status === 'done') {
          clearInterval(iv);
          running = false;
          status = 'done';
          runId = s.run_id || null;
        } else if (s.status === 'error') {
          clearInterval(iv);
          running = false;
          error = s.error || 'Unknown error';
          status = 'error';
        }
      } catch {}
    }, 3000);
  }
</script>

<svelte:head>
  <title>New Run — Verve</title>
</svelte:head>

<div class="max-w-lg mx-auto mt-16 animate-fade-in">
  <div class="card p-8">
    <div class="flex items-center gap-3 mb-1">
      <GrokBot size={32} theme="dark" />
      <h1 class="text-xl font-bold text-text-primary">New Pipeline Run</h1>
    </div>
    <p class="text-sm text-text-secondary mb-6">Source YC companies, enrich with founder data, score with JEV, and resolve verified emails.</p>

    <!-- Cost breakdown -->
    <div class="flex items-center gap-2 mb-6 text-[10px] font-mono text-text-muted">
      <span class="text-[#c2410c] font-bold">COST:</span>
      <span>Algolia $0.00</span>
      <span class="text-text-faint">→</span>
      <span class="text-[#7e22ce]">JEV $0.04</span>
      <span class="text-text-faint">→</span>
      <span class="text-[#059669]">Treg.to $0.005</span>
      <span class="text-text-faint">=</span>
      <span class="text-[#c2410c] font-bold">$0.045/lead</span>
    </div>

    {#if error}
      <div class="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800">
        {error}
      </div>
    {/if}

    {#if status === 'running'}
      <div class="mb-6 flex items-center gap-3 px-4 py-3 rounded-lg bg-orange-50/60 border border-orange-200">
        <span class="w-2 h-2 rounded-full bg-[#f97316] animate-pulse flex-shrink-0"></span>
        <p class="text-sm text-text-primary">Pipeline running — this takes 2–5 minutes…</p>
      </div>
    {/if}

    {#if status === 'done' && runId}
      <div class="mb-6 px-4 py-3 rounded-lg bg-emerald-50 border border-emerald-200">
        <p class="text-sm text-emerald-800 font-semibold mb-2">✓ Run complete</p>
        <a href="/runs/{runId}" class="btn-primary text-sm">View results →</a>
      </div>
    {/if}

    {#if status !== 'done'}
      <button
        on:click={startRun}
        disabled={running}
        class="btn-primary w-full justify-center py-2.5 {running ? 'opacity-60 cursor-not-allowed' : ''}"
      >
        {#if running}
          <svg class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.25"/>
            <path d="M22 12a10 10 0 01-10 10" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
          </svg>
          Running…
        {:else}
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <path d="M2.5 2L10.5 6.5L2.5 11V2Z" fill="currentColor"/>
          </svg>
          Start Pipeline
        {/if}
      </button>
    {/if}

    <a href="/" class="btn-ghost w-full justify-center mt-3">← Back to runs</a>
  </div>
</div>
