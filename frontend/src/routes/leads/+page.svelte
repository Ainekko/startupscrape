<!-- /leads/+page.svelte — All leads across all runs -->
<script>
  import { onMount } from 'svelte';
  import LeadRow from '$lib/components/LeadRow.svelte';
  import ScoreBadge from '$lib/components/ScoreBadge.svelte';

  const API = import.meta.env.VITE_API_URL || '';

  let leads = [];
  let loading = true;
  let error = null;
  let search = '';
  let sortBy = 'tier1_score';
  let sortDir = -1;
  let filterCompetitor = false;

  onMount(async () => {
    try {
      const r = await fetch(`${API}/api/runs`);
      const runs = await r.json();

      // Fetch details for each run and merge leads
      const details = await Promise.all(
        runs.map(run => fetch(`${API}/api/runs/${run.run_id}`).then(r => r.json()).catch(() => null))
      );

      const seen = new Set();
      for (const d of details) {
        if (!d?.leads) continue;
        for (const l of d.leads) {
          if (!seen.has(l.id)) {
            seen.add(l.id);
            leads.push({ ...l, _run_id: d.run_id });
          }
        }
      }
      leads = [...leads]; // trigger reactivity
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  function toggleSort(col) {
    if (sortBy === col) sortDir = -sortDir;
    else { sortBy = col; sortDir = -1; }
  }

  function sortIcon(col) {
    if (sortBy !== col) return '↕';
    return sortDir === -1 ? '↓' : '↑';
  }

  $: filtered = leads
    .filter(l => !filterCompetitor || !l.is_competitor)
    .filter(l => {
      if (!search) return true;
      const q = search.toLowerCase();
      return (
        (l.company_name || '').toLowerCase().includes(q) ||
        (l.one_liner || '').toLowerCase().includes(q) ||
        (l.founder_name || '').toLowerCase().includes(q) ||
        (l.batch || '').toLowerCase().includes(q)
      );
    })
    .sort((a, b) => {
      const av = a[sortBy] ?? 0;
      const bv = b[sortBy] ?? 0;
      if (typeof av === 'string') return sortDir * av.localeCompare(bv);
      return sortDir * (av - bv);
    });
</script>

<svelte:head>
  <title>All Leads — StartupScrape</title>
</svelte:head>

<div class="animate-fade-in">
  <div class="flex items-start justify-between mb-6">
    <div>
      <h1 class="text-2xl font-semibold text-text-primary tracking-tight">All Leads</h1>
      <p class="text-sm text-text-secondary mt-1">Deduplicated across all pipeline runs</p>
    </div>
    {#if !loading}
      <span class="badge badge-gray mt-1">{leads.length} unique leads</span>
    {/if}
  </div>

  <!-- Controls -->
  <div class="flex items-center gap-3 mb-4">
    <div class="flex-1 relative">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted w-3.5 h-3.5" viewBox="0 0 16 16" fill="none">
        <circle cx="6.5" cy="6.5" r="5" stroke="currentColor" stroke-width="1.5"/>
        <path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <input
        bind:value={search}
        type="text"
        placeholder="Search leads…"
        class="w-full pl-9 pr-4 py-2 bg-surface-2 border border-border rounded-lg text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent/40 transition-colors"
      />
    </div>
    <label class="flex items-center gap-2 text-sm text-text-secondary cursor-pointer select-none">
      <input type="checkbox" bind:checked={filterCompetitor} class="rounded accent-accent w-3.5 h-3.5" />
      Hide competitors
    </label>
    <span class="text-xs text-text-muted">{filtered.length} shown</span>
  </div>

  {#if loading}
    <div class="space-y-3">
      {#each Array(6) as _}
        <div class="card p-4 animate-pulse">
          <div class="h-4 bg-surface-4 rounded w-48 mb-2"></div>
          <div class="h-3 bg-surface-3 rounded w-80"></div>
        </div>
      {/each}
    </div>
  {:else if error}
    <div class="card p-12 text-center">
      <p class="text-red-400 text-sm">{error}</p>
    </div>
  {:else}
    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border">
              <th class="px-4 py-3 text-left">
                <button on:click={() => toggleSort('tier1_score')} class="label hover:text-text-secondary transition-colors flex items-center gap-1">
                  Score {sortIcon('tier1_score')}
                </button>
              </th>
              <th class="px-4 py-3 text-left">
                <button on:click={() => toggleSort('company_name')} class="label hover:text-text-secondary transition-colors flex items-center gap-1">
                  Company {sortIcon('company_name')}
                </button>
              </th>
              <th class="px-4 py-3 text-left hidden md:table-cell">
                <button on:click={() => toggleSort('batch')} class="label hover:text-text-secondary transition-colors flex items-center gap-1">
                  Batch {sortIcon('batch')}
                </button>
              </th>
              <th class="px-4 py-3 text-left hidden lg:table-cell">
                <span class="label">Founder</span>
              </th>
              <th class="px-4 py-3 text-left hidden lg:table-cell">
                <span class="label">Email</span>
              </th>
              <th class="px-4 py-3 text-left hidden xl:table-cell">
                <span class="label">Signals</span>
              </th>
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
          <div class="py-12 text-center text-text-muted text-sm">No leads found.</div>
        {/if}
      </div>
    </div>
  {/if}
</div>
