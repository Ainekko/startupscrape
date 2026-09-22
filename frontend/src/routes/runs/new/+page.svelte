<!-- /runs/new/+page.svelte — Trigger a new pipeline run -->
<script>
  import { goto } from '$app/navigation';

  const API = import.meta.env.VITE_API_URL || '';

  let running = false;
  let error = null;
  let status = null;
  let runId = null;

  async function startRun() {
    running = true;
    error = null;
    try {
      const r = await fetch(`${API}/api/run`, { method: 'POST' });
      if (!r.ok) {
        const body = await r.json();
        throw new Error(body.detail || 'Failed to start run');
      }
      status = 'running';
      poll();
    } catch (e) {
      error = e.message;
      running = false;
    }
  }

  function poll() {
    const iv = setInterval(async () => {
      try {
        const r = await fetch(`${API}/api/status`);
        const s = await r.json();
        if (s.status === 'done') {
          clearInterval(iv);
          running = false;
          status = 'done';
          runId = s.run_id;
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
  <title>New Run — StartupScrape</title>
</svelte:head>

<div class="max-w-lg mx-auto mt-16 animate-fade-in">
  <div class="card p-8">
    <h1 class="text-xl font-semibold text-text-primary mb-1">New Pipeline Run</h1>
    <p class="text-sm text-text-secondary mb-6">Scrape YC companies, enrich with founder data, score with JEV, and find emails.</p>

    {#if error}
      <div class="mb-4 px-4 py-3 rounded-lg bg-red-400/10 border border-red-400/20 text-sm text-red-300">
        {error}
      </div>
    {/if}

    {#if status === 'running'}
      <div class="mb-6 flex items-center gap-3 px-4 py-3 rounded-lg bg-accent/5 border border-accent/20">
        <span class="w-2 h-2 rounded-full bg-accent animate-pulse flex-shrink-0"></span>
        <p class="text-sm text-text-primary">Pipeline running — this takes 2–5 minutes…</p>
      </div>
    {/if}

    {#if status === 'done' && runId}
      <div class="mb-6 px-4 py-3 rounded-lg bg-accent/10 border border-accent/20">
        <p class="text-sm text-accent font-medium mb-2">✓ Run complete</p>
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
