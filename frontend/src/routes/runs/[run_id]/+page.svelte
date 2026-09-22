<!-- /runs/[run_id]/+page.svelte — Run detail with lead table -->
<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { pipelineApi } from '$lib/api/pipeline';
  import type { Run, Lead } from '$lib/api/pipeline';
  import LeadRow from '$lib/components/LeadRow.svelte';

  let run: Run | null = null;
  let loading = true;
  let error: string | null = null;
  let search = '';
  let sortBy: keyof Lead = 'tier1_score';
  let sortDir = -1;
  let filterCompetitor = false;

  onMount(async () => {
    try {
      run = await pipelineApi.getRun($page.params.run_id);
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  function toggleSort(col: keyof Lead) {
    if (sortBy === col) sortDir = -sortDir;
    else { sortBy = col; sortDir = -1; }
  }

  function sortIcon(col: keyof Lead) {
    if (sortBy !== col) return '↕';
    return sortDir === -1 ? '↓' : '↑';
  }

  $: leads = run?.leads ?? [];

  $: filtered = leads
    .filter(l => !filterCompetitor || !l.is_competitor)
    .filter(l => {
      if (!search) return true;
      const q = search.toLowerCase();
      return (
        l.company_name?.toLowerCase().includes(q) ||
        l.one_liner?.toLowerCase().includes(q) ||
        l.founder_name?.toLowerCase().includes(q) ||
        l.batch?.toLowerCase().includes(q)
      );
    })
    .sort((a, b) => {
      const av = (a[sortBy] as any) ?? 0;
      const bv = (b[sortBy] as any) ?? 0;
      if (typeof av === 'string') return sortDir * av.localeCompare(bv);
      return sortDir * (av - bv);
    });

  function fmtRunId(id: string) {
    const m = id.match(/run_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})/);
    if (!m) return id;
    return `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]}`;
  }
</script>

<svelte:head>
  <title>Run {$page.params.run_id} — StartupScrape</title>
</svelte:head>

{#if loading}
  <div class="space-y-3">
    {#each Array(5) as _}
      <div class="card p-4 animate-pulse">
        <div class="h-4 bg-surface-4 rounded w-48 mb-2"></div>
        <div class="h-3 bg-surface-3 rounded w-80"></div>
      </div>
    {/each}
  </div>
{:else if error}
  <div class="card p-12 text-center">
    <p class="text-red-400 text-sm">{error}</p>
    <a href="/" class="btn-ghost mt-4 inline-flex">← Back to runs</a>
  </div>
{:else if run}
  <div class="animate-fade-in">
    <!-- Breadcrumb -->
    <div class="flex items-center gap-3 mb-1">
      <a href="/" class="text-text-muted hover:text-text-secondary transition-colors text-sm">Runs</a>
      <span class="text-text-muted text-sm">/</span>
      <span class="text-text-secondary text-sm font-mono">{fmtRunId(run.run_id)}</span>
    </div>

    <div class="flex items-start justify-between mb-6">
      <div>
        <h1 class="text-xl font-semibold text-text-primary">{fmtRunId(run.run_id)}</h1>
        <p class="text-xs text-text-muted font-mono mt-0.5">{run.run_id}</p>
      </div>
      <span class="badge {run.status === 'complete' ? 'badge-green' : 'badge-yellow'} mt-1">
        {run.status ?? 'complete'}
      </span>
    </div>

    <!-- Stats strip -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      <div class="card px-4 py-3">
        <p class="label mb-1">Scraped</p>
        <p class="text-xl font-semibold text-text-primary">{run.funnel?.scraped ?? '—'}</p>
      </div>
      <div class="card px-4 py-3">
        <p class="label mb-1">Enriched</p>
        <p class="text-xl font-semibold text-text-primary">{run.funnel?.enriched ?? '—'}</p>
      </div>
      <div class="card px-4 py-3">
        <p class="label mb-1">Qualified</p>
        <p class="text-xl font-semibold text-accent">{run.funnel?.qualified ?? leads.length}</p>
      </div>
      <div class="card px-4 py-3">
        <p class="label mb-1">Spend</p>
        <p class="text-xl font-semibold text-text-primary">${(run.spend?.total_usd ?? 0).toFixed(3)}</p>
      </div>
    </div>

    <!-- Controls -->
    <div class="flex items-center gap-3 mb-4">
      <div class="flex-1 relative">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted w-3.5 h-3.5" viewBox="0 0 16 16" fill="none">
          <circle cx="6.5" cy="6.5" r="5" stroke="currentColor" stroke-width="1.5"/>
          <path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <input bind:value={search} type="text" placeholder="Search leads…"
          class="w-full pl-9 pr-4 py-2 bg-surface-2 border border-border rounded-lg text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent/40 transition-colors" />
      </div>
      <label class="flex items-center gap-2 text-sm text-text-secondary cursor-pointer select-none">
        <input type="checkbox" bind:checked={filterCompetitor} class="rounded accent-accent w-3.5 h-3.5" />
        Hide competitors
      </label>
      <span class="text-xs text-text-muted">{filtered.length} leads</span>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border">
              <th class="px-4 py-3 text-left">
                <button on:click={() => toggleSort('tier1_score')} class="label hover:text-text-secondary transition-colors flex items-center gap-1">Score {sortIcon('tier1_score')}</button>
              </th>
              <th class="px-4 py-3 text-left">
                <button on:click={() => toggleSort('company_name')} class="label hover:text-text-secondary transition-colors flex items-center gap-1">Company {sortIcon('company_name')}</button>
              </th>
              <th class="px-4 py-3 text-left hidden md:table-cell">
                <button on:click={() => toggleSort('batch')} class="label hover:text-text-secondary transition-colors flex items-center gap-1">Batch {sortIcon('batch')}</button>
              </th>
              <th class="px-4 py-3 text-left hidden lg:table-cell"><span class="label">Founder</span></th>
              <th class="px-4 py-3 text-left hidden lg:table-cell"><span class="label">Email</span></th>
              <th class="px-4 py-3 text-left hidden xl:table-cell"><span class="label">Signals</span></th>
              <th class="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {#each filtered as lead (lead.id)}
              <LeadRow {lead} />
            {/each}
          </tbody>
        </table>
        {#if filtered.length === 0}
          <div class="py-12 text-center text-text-muted text-sm">No leads match your filter.</div>
        {/if}
      </div>
    </div>
  </div>
{/if}
