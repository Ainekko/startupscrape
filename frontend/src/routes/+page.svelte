<!-- +page.svelte — Dashboard: pipeline runs overview -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { funnelMetrics, totalSpend } from '$lib/types';
  import type { RunSummary, RunStatus } from '$lib/types';
  import RunCard from '$lib/components/RunCard.svelte';
  import StatusBar from '$lib/components/StatusBar.svelte';
  import GrokBot from '$lib/components/GrokBot.svelte';

  let runs: RunSummary[] = [];
  let status: RunStatus = { status: 'idle' };
  let loading = true;
  let error: string | null = null;

  async function fetchRuns() {
    try {
      runs = await api.pipeline.listRuns();
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function fetchStatus() {
    try {
      status = await api.pipeline.getStatus();
    } catch {}
  }

  function pollStatus() {
    const iv = setInterval(async () => {
      await fetchStatus();
      if (status.status !== 'running') {
        clearInterval(iv);
        await fetchRuns();
      }
    }, 3000);
  }

  onMount(() => {
    fetchRuns();
    fetchStatus();
    // if a run was already in progress when we landed, keep polling
    fetchStatus().then(() => {
      if (status.status === 'running') pollStatus();
    });
  });

  // Aggregate stats from actual backend data
  $: aggScraped   = runs.reduce((s, r) => s + (funnelMetrics(r.funnel || {}).scraped), 0);
  $: aggQualified = runs.reduce((s, r) => s + (funnelMetrics(r.funnel || {}).qualified), 0);
  $: aggSpend     = runs.reduce((s, r) => s + totalSpend(r.spend || {}), 0);
  $: avgYield     = aggScraped > 0 ? ((aggQualified / aggScraped) * 100).toFixed(0) : '—';
</script>

<svelte:head>
  <title>Verve — Autonomous YC Lead Pipeline</title>
</svelte:head>

<div class="animate-fade-in">
  <!-- Header -->
  <div class="mb-6">
    <h1 class="text-2xl font-bold text-text-primary tracking-tight">Pipeline Runs</h1>
    <p class="text-sm text-text-secondary mt-1">Autonomous YC startup sourcing, scoring &amp; verified enrichment</p>
    {#if status.status === 'running'}
      <div class="flex items-center gap-2 text-sm text-[#c2410c] font-medium mt-2">
        <span class="w-2 h-2 rounded-full bg-[#f97316] animate-pulse-slow"></span>
        Run in progress…
      </div>
    {/if}
  </div>

  {#if status.status === 'running'}
    <StatusBar />
  {/if}

  <!-- Pipeline Workflow Header Bar -->
  <div class="mb-6 flex flex-wrap items-center justify-between gap-3 text-xs font-mono bg-white border border-[#e7dfd4] px-4 py-3 rounded-2xl shadow-sm">
    <div class="flex items-center gap-2.5">
      <GrokBot size={30} theme="dark" />
      <span class="text-[11px] font-black text-[#c2410c] tracking-wider uppercase">PIPELINE:</span>
    </div>

    <div class="flex items-center flex-wrap gap-2">
      <div class="flex items-center gap-1.5 px-2.5 py-1 bg-[#fbf9f5] rounded-lg border border-[#e5ddd0]">
        <div class="w-4 h-4 rounded overflow-hidden flex items-center justify-center flex-shrink-0">
          <img src="/flowjoy/algolia.svg" alt="Algolia" class="w-full h-full object-contain" />
        </div>
        <div class="w-3.5 h-3.5 rounded overflow-hidden flex items-center justify-center flex-shrink-0 -ml-0.5">
          <img src="/flowjoy/yc.svg" alt="YC" class="w-full h-full object-contain" />
        </div>
        <span class="font-bold text-[#1c1917] text-[11px]">Algolia Search</span>
      </div>

      <span class="text-[#a8a29e] font-bold text-sm">→</span>

      <div class="flex items-center gap-1.5 px-2.5 py-1 bg-[#fbf9f5] rounded-lg border border-purple-200">
        <div class="w-4 h-4 rounded-xs overflow-hidden flex-shrink-0 border border-purple-100">
          <img src="/flowjoy/typesafe-ai-200x200.jfif" alt="JEV" class="w-full h-full object-cover" />
        </div>
        <span class="font-bold text-[#7e22ce] text-[11px]">JEV ICP Scoring</span>
      </div>

      <span class="text-[#a8a29e] font-bold text-sm">→</span>

      <div class="flex items-center gap-1.5 px-2.5 py-1 bg-[#fbf9f5] rounded-lg border border-emerald-200">
        <div class="w-4 h-4 rounded overflow-hidden flex items-center justify-center flex-shrink-0">
          <img src="/flowjoy/treg.svg" alt="Treg.to" class="w-full h-full object-contain" />
        </div>
        <span class="font-bold text-[#059669] text-[11px]">Treg.to Email Enrichment</span>
      </div>
    </div>
  </div>

  <!-- Summary stats -->
  {#if runs.length > 0}
    <div class="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-8">
      <div class="card px-4 py-3">
        <p class="label mb-1">Runs</p>
        <p class="text-xl font-bold text-text-primary">{runs.length}</p>
      </div>
      <div class="card px-4 py-3">
        <p class="label mb-1">Scraped</p>
        <p class="text-xl font-bold text-text-primary">{aggScraped}</p>
      </div>
      <div class="card px-4 py-3">
        <p class="label mb-1">Qualified</p>
        <p class="text-xl font-bold text-emerald-700">{aggQualified}</p>
      </div>
      <div class="card px-4 py-3">
        <p class="label mb-1">Yield</p>
        <p class="text-xl font-bold text-text-primary">{avgYield}{avgYield !== '—' ? '%' : ''}</p>
      </div>
      <div class="card px-4 py-3">
        <p class="label mb-1">Treg Spend</p>
        <p class="text-xl font-bold text-text-primary font-mono">${aggSpend.toFixed(3)}</p>
      </div>
    </div>
  {/if}

  <!-- Run list -->
  {#if loading}
    <div class="space-y-3">
      {#each Array(3) as _}
        <div class="card p-5 animate-pulse">
          <div class="h-4 bg-surface-3 rounded w-40 mb-3"></div>
          <div class="h-3 bg-surface-4 rounded w-64"></div>
        </div>
      {/each}
    </div>
  {:else if error}
    <div class="card p-8 text-center">
      <p class="text-red-700 text-sm mb-1">Could not reach the backend.</p>
      <p class="text-text-muted text-xs font-mono">{error}</p>
    </div>
  {:else if runs.length === 0}
    <div class="card p-12 text-center">
      <div class="w-12 h-12 rounded-full bg-orange-50 border border-orange-200 flex items-center justify-center mx-auto mb-4">
        <span class="text-[#c2410c] text-lg">⚡</span>
      </div>
      <p class="text-text-primary font-semibold mb-1">No runs yet</p>
      <p class="text-text-secondary text-sm">Trigger your first pipeline run using the <strong>New Run</strong> button above.</p>
    </div>
  {:else}
    <div class="space-y-3 animate-slide-up">
      {#each runs as run}
        <RunCard {run} />
      {/each}
    </div>
  {/if}
</div>
