<!-- /runs/new/+page.svelte — Trigger a new pipeline run with configurable filters -->
<script lang="ts">
  import { api } from '$lib/api';
  import GrokBot from '$lib/components/GrokBot.svelte';

  // All available YC batches (newest first)
  const ALL_BATCHES = [
    'Summer 2027', 'Winter 2027',
    'Fall 2026', 'Summer 2026', 'Spring 2026', 'Winter 2026',
    'Fall 2025', 'Summer 2025', 'Winter 2025',
    'Fall 2024', 'Summer 2024', 'Winter 2024',
    'Summer 2023', 'Winter 2023',
  ];

  // Default: all batches selected
  let selectedBatches = new Set<string>(ALL_BATCHES);
  let maxLeads = 20;
  let maxCost = 1.0;

  let running = false;
  let error: string | null = null;
  let runStatus: string | null = null;
  let runId: string | null = null;

  function toggleBatch(batch: string) {
    if (selectedBatches.has(batch)) {
      selectedBatches.delete(batch);
    } else {
      selectedBatches.add(batch);
    }
    selectedBatches = selectedBatches; // trigger reactivity
  }

  function selectAll() { selectedBatches = new Set(ALL_BATCHES); }
  function selectNone() { selectedBatches = new Set(); }
  function selectRecent() {
    selectedBatches = new Set([
      'Summer 2027', 'Winter 2027', 'Fall 2026', 'Summer 2026', 'Spring 2026', 'Winter 2026'
    ]);
  }

  async function startRun() {
    if (selectedBatches.size === 0) {
      error = 'Select at least one batch.';
      return;
    }
    running = true;
    error = null;
    try {
      const batches = selectedBatches.size === ALL_BATCHES.length
        ? null  // null = all, avoids giant payload
        : [...selectedBatches];
      await api.pipeline.startRun({
        max_leads: maxLeads,
        max_treg_cost: maxCost,
        batches,
        sources: ['yc'],
      });
      runStatus = 'running';
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
          runStatus = 'done';
          runId = s.run_id || null;
        } else if (s.status === 'error') {
          clearInterval(iv);
          running = false;
          error = s.error || 'Unknown error';
          runStatus = 'error';
        }
      } catch {}
    }, 3000);
  }
</script>

<svelte:head>
  <title>New Run — Verve</title>
</svelte:head>

<div class="max-w-lg mx-auto mt-12 animate-fade-in">
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
      <span class="text-[#c2410c] font-bold">~$0.045/lead</span>
    </div>

    <!-- ── Controls ─────────────────────────────────────────────── -->
    <div class="space-y-5 mb-6">

      <!-- Max leads -->
      <div>
        <div class="flex items-center justify-between mb-1.5">
          <label class="text-xs font-semibold text-text-primary">Max leads</label>
          <span class="text-xs font-mono font-bold text-[#c2410c]">{maxLeads}</span>
        </div>
        <input
          type="range" min="1" max="200" step="1"
          bind:value={maxLeads}
          disabled={running}
          class="w-full accent-[#c2410c]"
        />
        <div class="flex justify-between text-[10px] text-text-muted mt-0.5">
          <span>1</span><span>50</span><span>100</span><span>200</span>
        </div>
      </div>

      <!-- Max treg cost -->
      <div>
        <div class="flex items-center justify-between mb-1.5">
          <label class="text-xs font-semibold text-text-primary">Max email cost (USD)</label>
          <span class="text-xs font-mono font-bold text-[#059669]">${maxCost.toFixed(2)}</span>
        </div>
        <input
          type="range" min="0.10" max="5.00" step="0.10"
          bind:value={maxCost}
          disabled={running}
          class="w-full accent-[#059669]"
        />
        <div class="flex justify-between text-[10px] text-text-muted mt-0.5">
          <span>$0.10</span><span>$1.00</span><span>$2.50</span><span>$5.00</span>
        </div>
      </div>

      <!-- Batch filter -->
      <div>
        <div class="flex items-center justify-between mb-2">
          <label class="text-xs font-semibold text-text-primary">YC Batches ({selectedBatches.size}/{ALL_BATCHES.length})</label>
          <div class="flex gap-2 text-[10px] font-medium">
            <button on:click={selectRecent} class="text-[#7e22ce] hover:underline">Recent</button>
            <button on:click={selectAll} class="text-text-muted hover:underline">All</button>
            <button on:click={selectNone} class="text-text-muted hover:underline">None</button>
          </div>
        </div>
        <div class="flex flex-wrap gap-1.5">
          {#each ALL_BATCHES as batch}
            <button
              on:click={() => toggleBatch(batch)}
              disabled={running}
              class="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold border transition-colors
                {selectedBatches.has(batch)
                  ? 'bg-[#c2410c] text-white border-[#c2410c]'
                  : 'bg-white text-text-muted border-[#e7dfd4] hover:border-[#c2410c]'}"
            >
              {batch}
            </button>
          {/each}
        </div>
      </div>
    </div>

    <!-- Error -->
    {#if error}
      <div class="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800">
        {error}
      </div>
    {/if}

    <!-- Running indicator -->
    {#if runStatus === 'running'}
      <div class="mb-6 flex items-center gap-3 px-4 py-3 rounded-lg bg-orange-50/60 border border-orange-200">
        <span class="w-2 h-2 rounded-full bg-[#f97316] animate-pulse flex-shrink-0"></span>
        <p class="text-sm text-text-primary">Pipeline running — this takes 2–5 minutes…</p>
      </div>
    {/if}

    <!-- Done -->
    {#if runStatus === 'done' && runId}
      <div class="mb-6 px-4 py-3 rounded-lg bg-emerald-50 border border-emerald-200">
        <p class="text-sm text-emerald-800 font-semibold mb-2">✓ Run complete</p>
        <a href="/runs/{runId}" class="btn-primary text-sm">View results →</a>
      </div>
    {/if}

    {#if runStatus !== 'done'}
      <button
        on:click={startRun}
        disabled={running || selectedBatches.size === 0}
        class="btn-primary w-full justify-center py-2.5 {running || selectedBatches.size === 0 ? 'opacity-60 cursor-not-allowed' : ''}"
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
