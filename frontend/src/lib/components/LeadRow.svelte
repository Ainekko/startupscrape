<!-- LeadRow.svelte — Expandable table row for a single lead, warm palette -->
<script>
  import ScoreBadge from './ScoreBadge.svelte';
  import SignalPill from './SignalPill.svelte';

  export let lead;
  let expanded = false;

  $: email = lead.email_result?.email || lead.email || null;
  $: emailVerified = lead.email_result?.verified || lead.email_status === 'verified' || false;
  $: signals = lead.signals || [];
  $: jevProbs = lead.jev_probs || {};

  function extractDomain(url) {
    if (!url) return null;
    try {
      return new URL(url.startsWith('http') ? url : 'https://' + url).hostname.replace(/^www\./, '');
    } catch { return url; }
  }
</script>

<!-- Main row -->
<tr
  class="table-row-base cursor-pointer"
  on:click={() => (expanded = !expanded)}
>
  <!-- Score -->
  <td class="px-4 py-3">
    <ScoreBadge score={lead.tier1_score || lead.final_score || 0} />
  </td>

  <!-- Company -->
  <td class="px-4 py-3">
    <div class="flex items-center gap-2.5">
      <div>
        <p class="font-medium text-text-primary leading-tight">{lead.company_name || lead.id}</p>
        <p class="text-xs text-text-muted mt-0.5 line-clamp-1 max-w-[200px]">{lead.one_liner || ''}</p>
      </div>
      {#if lead.is_competitor}
        <span class="badge badge-red text-xs flex-shrink-0">competitor</span>
      {/if}
      {#if lead.is_vertical_product}
        <span class="badge badge-yellow text-xs flex-shrink-0">vertical</span>
      {/if}
    </div>
  </td>

  <!-- Batch -->
  <td class="px-4 py-3 hidden md:table-cell">
    {#if lead.batch}
      <span class="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-[#ff6600]/10 text-[#ea580c] border border-[#ff6600]/20">
        {lead.batch}
      </span>
    {:else}
      <span class="text-text-muted">—</span>
    {/if}
  </td>

  <!-- Founder -->
  <td class="px-4 py-3 hidden lg:table-cell">
    {#if lead.founder_name}
      <p class="text-text-primary text-sm font-medium">{lead.founder_name}</p>
      <p class="text-xs text-text-muted">{lead.founder_title || ''}</p>
    {:else}
      <span class="text-text-muted">—</span>
    {/if}
  </td>

  <!-- Email -->
  <td class="px-4 py-3 hidden lg:table-cell">
    {#if email}
      <div class="flex items-center gap-1.5">
        <a
          href="mailto:{email}"
          class="font-mono text-xs text-blue-700 hover:underline"
          on:click|stopPropagation
        >{email}</a>
        {#if emailVerified}
          <span class="text-[8px] font-mono font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded-full border border-emerald-200">✓ VERIFIED</span>
        {/if}
      </div>
    {:else}
      <span class="text-text-muted">—</span>
    {/if}
  </td>

  <!-- Signals (first 2) -->
  <td class="px-4 py-3 hidden xl:table-cell">
    <div class="flex flex-wrap gap-1">
      {#each signals.slice(0, 2) as sig}
        <SignalPill {sig} />
      {/each}
      {#if signals.length > 2}
        <span class="badge badge-gray">+{signals.length - 2}</span>
      {/if}
    </div>
  </td>

  <!-- Expand toggle -->
  <td class="px-4 py-3 text-right">
    <svg
      class="w-4 h-4 text-text-muted transition-transform duration-200 inline-block {expanded ? 'rotate-90' : ''}"
      viewBox="0 0 16 16" fill="none"
    >
      <path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </td>
</tr>

<!-- Expanded detail row -->
{#if expanded}
<tr>
  <td colspan="7" class="px-0 py-0">
    <div class="detail-panel open">
      <div>
        <div class="px-6 py-5 bg-surface-1 border-b border-border grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">

          <!-- Company info -->
          <div>
            <p class="label mb-2">Company</p>
            <p class="text-text-primary font-semibold">{lead.company_name}</p>
            {#if lead.one_liner}
              <p class="text-text-secondary text-sm mt-1">{lead.one_liner}</p>
            {/if}
            <div class="flex flex-wrap gap-2 mt-3">
              {#if lead.website}
                <a href={lead.website} target="_blank" rel="noopener" class="btn-ghost text-xs py-1 px-2.5">
                  🌐 {extractDomain(lead.website)}
                </a>
              {/if}
              {#if lead.yc_url}
                <a href={lead.yc_url} target="_blank" rel="noopener" class="btn-ghost text-xs py-1 px-2.5">YC ↗</a>
              {/if}
              {#if lead.linkedin_url}
                <a href={lead.linkedin_url} target="_blank" rel="noopener" class="btn-ghost text-xs py-1 px-2.5">LinkedIn ↗</a>
              {/if}
            </div>
          </div>

          <!-- Founder info -->
          <div>
            <p class="label mb-2">Founder</p>
            {#if lead.founders && lead.founders.length > 0}
              {#each lead.founders as f}
                <div class="mb-2">
                  <p class="text-text-primary font-medium text-sm">{f.name}</p>
                  {#if f.title}<p class="text-text-muted text-xs">{f.title}</p>{/if}
                  <div class="flex gap-2 mt-1.5">
                    {#if f.linkedin_url}
                      <a href={f.linkedin_url} target="_blank" rel="noopener" class="text-xs text-blue-700 hover:underline">LinkedIn ↗</a>
                    {/if}
                    {#if f.twitter_url}
                      <a href={f.twitter_url} target="_blank" rel="noopener" class="text-xs text-blue-700 hover:underline">X ↗</a>
                    {/if}
                  </div>
                </div>
              {/each}
            {:else}
              <p class="text-text-muted text-sm">No founder data</p>
            {/if}
            {#if email}
              <div class="mt-2 flex items-center gap-2">
                <span class="font-mono text-xs text-blue-700">{email}</span>
                {#if emailVerified}
                  <span class="text-emerald-700 text-xs font-semibold">✓ verified</span>
                {:else}
                  <span class="text-text-muted text-xs">unverified</span>
                {/if}
              </div>
            {/if}
          </div>

          <!-- Signals & JEV -->
          <div>
            <p class="label mb-2">Signals</p>
            <div class="flex flex-wrap gap-1.5 mb-4">
              {#each signals as sig}
                <SignalPill {sig} />
              {/each}
            </div>

            {#if Object.keys(jevProbs).length > 0}
              <p class="label mb-2">JEV Scores</p>
              <div class="space-y-1.5">
                {#each Object.entries(jevProbs) as [key, probs]}
                  {@const mainEntry = Object.entries(probs).sort((a,b) => b[1] - a[1])[0]}
                  <div class="flex items-center justify-between text-xs">
                    <span class="text-text-muted capitalize">{key.replace(/_/g, ' ')}</span>
                    <span class="font-mono text-text-secondary">{mainEntry[0]} {(mainEntry[1] * 100).toFixed(0)}%</span>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        </div>
      </div>
    </div>
  </td>
</tr>
{/if}
