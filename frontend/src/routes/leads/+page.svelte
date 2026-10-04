<!-- /leads/+page.svelte — All leads, deduped, with pipeline header -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import type { Lead } from '$lib/types';
  import LeadRow from '$lib/components/LeadRow.svelte';
  import PipelineFlowHeader from '$lib/components/PipelineFlowHeader.svelte';

  let leads: Lead[] = [];
  let totalCount = 0;
  let rawCount = 0;
  let loading = true;
  let error: string | null = null;
  let search = '';
  let sortBy: string = 'final_score';
  let sortDir = -1;
  let filterCompetitor = false;
  let filterHasEmail = false;

  async function loadLeads() {
    loading = true;
    error = null;
    try {
      // Deduped view for display
      const deduped = await api.leads.list({ limit: 500, dedupe: true });
      leads = deduped.items || [];
      totalCount = deduped.total || leads.length;

      // Raw count for context
      const raw = await api.leads.list({ limit: 1, dedupe: false });
      rawCount = raw.total || 0;
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(() => loadLeads());

  function toggleSort(col: string) {
    if (sortBy === col) sortDir = -sortDir;
    else { sortBy = col; sortDir = -1; }
  }

  function sortIcon(col: string) {
    if (sortBy !== col) return '↕';
    return sortDir === -1 ? '↓' : '↑';
  }

  $: filtered = leads
    .filter(l => !filterCompetitor || !l.is_competitor)
    .filter(l => !filterHasEmail || !!(l.email || l.email_result?.email))
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
    .sort((a: any, b: any) => {
      const av = a[sortBy] ?? 0;
      const bv = b[sortBy] ?? 0;
      if (typeof av === 'string') return sortDir * av.localeCompare(bv);
      return sortDir * (av - bv);
    });
</script>

<svelte:head>
  <title>Verified Leads — Verve</title>
</svelte:head>

<div class="animate-fade-in">
  <!-- Pipeline flow header (replaces boring DB subtitle) -->
  <PipelineFlowHeader uniqueCount={loading ? null : totalCount} leadCount={loading ? null : rawCount} />

  <!-- Controls -->
  <div class="flex items-center gap-2 mb-4 flex-wrap">
    <div class="flex-1 relative min-w-[180px]">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted w-3.5 h-3.5" viewBox="0 0 16 16" fill="none">
        <circle cx="6.5" cy="6.5" r="5" stroke="currentColor" stroke-width="1.5"/>
        <path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <input
        bind:value={search}
        type="text"
        placeholder="Search company, founder, pitch…"
        class="w-full pl-9 pr-4 py-2 bg-white border border-border rounded-lg text-sm text-text-primary placeholder-text-faint focus:outline-none focus:border-[#c2410c]/40 focus:ring-2 focus:ring-[#c2410c]/10 transition-colors"
      />
    </div>

    <label class="flex items-center gap-2 text-xs text-text-secondary cursor-pointer select-none px-3 py-2 bg-white border border-border rounded-lg hover:bg-surface-3 transition-colors">
      <input type="checkbox" bind:checked={filterCompetitor} class="rounded accent-[#c2410c] w-3.5 h-3.5" />
      Hide competitors
    </label>
    <label class="flex items-center gap-2 text-xs text-text-secondary cursor-pointer select-none px-3 py-2 bg-white border border-border rounded-lg hover:bg-surface-3 transition-colors">
      <input type="checkbox" bind:checked={filterHasEmail} class="rounded accent-emerald-600 w-3.5 h-3.5" />
      Email only
    </label>

    <span class="text-xs text-text-muted font-mono ml-auto">{filtered.length} shown</span>
  </div>

  {#if loading}
    <div class="space-y-2">
      {#each Array(8) as _}
        <div class="card p-4 animate-pulse flex gap-4 items-center">
          <div class="w-10 h-10 rounded-full bg-surface-3"></div>
          <div class="flex-1">
            <div class="h-3.5 bg-surface-3 rounded w-36 mb-2"></div>
            <div class="h-2.5 bg-surface-4 rounded w-56"></div>
          </div>
        </div>
      {/each}
    </div>
  {:else if error}
    <div class="card p-12 text-center">
      <p class="text-red-700 text-sm">{error}</p>
    </div>
  {:else}
    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border bg-[#faf7f3]">
              <th class="px-4 py-3 text-left w-12">
                <span class="label">Score</span>
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
              <th class="px-4 py-3 w-8"></th>
            </tr>
          </thead>
          <tbody>
            {#each filtered as lead (lead.id)}
              <LeadRow {lead} />
            {:else}
              <tr>
                <td colspan="7" class="py-14 text-center text-text-muted text-sm">No leads match your filter.</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>
