<!-- +page.svelte — Dashboard: list of runs -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { pipelineApi } from '$lib/api/pipeline';
  import type { RunSummary, RunStatus } from '$lib/api/pipeline';
  import RunCard from '$lib/components/RunCard.svelte';
  import StatusBar from '$lib/components/StatusBar.svelte';

  let runs: RunSummary[] = [];
  let status: RunStatus = { status: 'idle' };
  let loading = true;
  let error: string | null = null;

  async function fetchRuns() {
    try {
      runs = await pipelineApi.listRuns();
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function fetchStatus() {
    try {
      status = await pipelineApi.getStatus();
    } catch {}
  }

  async function triggerRun() {
    try {
      await pipelineApi.startRun();
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

  $: totalLeads = runs.reduce((s, r) => s + (r.lead_count || 0), 0);
  $: totalSpend = runs.reduce((s, r) => s + (r.spend?.total_usd || 0), 0);
</script>

<svelte:head>
  <title>StartupScrape — Runs</title>
</svelte:head>

<div class="animate-fade-in">
  <!-- Header -->
  <div class="flex items-start justify-between mb-8">
    <div>
      <h1 class="text-2xl font-semibold text-text-primary tracking-tight">Pipeline Runs</h1>
      <p class="text-sm text-text-secondary mt-1">YC startup lead enrichment & scoring</p>
    </div>
    <div class="flex items-center gap-3">
      {#if status.status === 'running'}
        <div class="flex items-center gap-2 text-sm text-accent">
          <span class="w-2 h-2 rounded-full bg-accent animate-pulse-slow"></span>
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

  <!-- Summary stats -->
  {#if runs.length > 0}
    <div class="grid grid-cols-3 gap-4 mb-8">
      <div class="card px-5 py-4">
        <p class="label mb-1">Total runs</p>
        <p class="text-2xl font-semibold text-text-primary">{runs.length}</p>
      </div>
      <div class="card px-5 py-4">
        <p class="label mb-1">Leads qualified</p>
        <p class="text-2xl font-semibold text-accent">{totalLeads}</p>
      </div>
      <div class="card px-5 py-4">
        <p class="label mb-1">Total spend</p>
        <p class="text-2xl font-semibold text-text-primary">${totalSpend.toFixed(3)}</p>
      </div>
    </div>
  {/if}

  <!-- Run list -->
  {#if loading}
    <div class="space-y-3">
      {#each Array(3) as _}
        <div class="card p-5 animate-pulse">
          <div class="h-4 bg-surface-4 rounded w-40 mb-3"></div>
          <div class="h-3 bg-surface-3 rounded w-64"></div>
        </div>
      {/each}
    </div>
  {:else if error}
    <div class="card p-8 text-center">
      <p class="text-red-400 text-sm mb-1">Could not reach the backend.</p>
      <p class="text-text-muted text-xs font-mono">{error}</p>
    </div>
  {:else if runs.length === 0}
    <div class="card p-12 text-center">
      <div class="w-12 h-12 rounded-full bg-surface-3 flex items-center justify-center mx-auto mb-4">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M2.5 2L17.5 10L2.5 18V2Z" fill="#52525b"/>
        </svg>
      </div>
      <p class="text-text-primary font-medium mb-1">No runs yet</p>
      <p class="text-text-secondary text-sm mb-5">Trigger your first pipeline run to find and score YC leads.</p>
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
