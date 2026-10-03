<!-- +page.svelte — Dashboard: pipeline runs overview -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { funnelMetrics, totalSpend } from '$lib/types';
  import type { RunSummary, RunStatus } from '$lib/types';
  import RunCard from '$lib/components/RunCard.svelte';
  import StatusBar from '$lib/components/StatusBar.svelte';

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

  async function triggerRun() {
    try {
      await api.pipeline.startRun();
      status = { status: 'running' };
      pollStatus();
    } catch (e: any) {
      error = e.message;
    }
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
  });

  // Aggregate stats from actual backend data
  $: aggScraped = runs.reduce((s, r) => s + (funnelMetrics(r.funnel || {}).scraped), 0);
  $: aggQualified = runs.reduce((s, r) => s + (funnelMetrics(r.funnel || {}).qualified), 0);
  $: aggSpend = runs.reduce((s, r) => s + totalSpend(r.spend || {}), 0);
  $: avgYield = aggScraped > 0 ? ((aggQualified / aggScraped) * 100).toFixed(0) : '—';
</script>

<svelte:head>
  <title>StartupScrape — Pipeline</title>
</svelte:head>

<div class="animate-fade-in">
  <!-- Header -->
  <div class="flex items-start justify-between mb-6">
    <div>
      <h1 class="text-2xl font-bold text-text-primary tracking-tight">Pipeline Runs</h1>
      <p class="text-sm text-text-secondary mt-1">YC startup sourcing, scoring & enrichment</p>
    </div>
    <div class="flex items-center gap-3">
      {#if status.status === 'running'}
        <div class="flex items-center gap-2 text-sm text-[#c2410c] font-medium">
          <span class="w-2 h-2 rounded-full bg-[#f97316] animate-pulse-slow"></span>
          Run in progress…
        </div>
      {:else}
        <button on:click={triggerRun} class="btn-primary">
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <path d="M2.5 2L10.5 6.5L2.5 11V2Z" fill="currentColor"/>
          </svg>
          Run Pipeline
        </button>
      {/if}
    </div>
  </div>

  {#if status.status === 'running'}
    <StatusBar />
  {/if}

  <!-- Summary stats — computed from real backend data -->
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
      <p class="text-text-secondary text-sm mb-5">Trigger your first pipeline run to source and score YC leads.</p>
      <button on:click={triggerRun} class="btn-primary mx-auto">Run Pipeline</button>
    </div>
  {:else}
    <div class="space-y-3 animate-slide-up">
      {#each runs as run}
        <RunCard {run} />
      {/each}
    </div>
  {/if}
</div>
