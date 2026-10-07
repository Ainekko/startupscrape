<!-- LeadRow.svelte — Expandable table row: real logos (YC, LinkedIn, Treg.to, TypeSafe AI) & JEV Scoring -->
<script lang="ts">
  import ScoreBadge from './ScoreBadge.svelte';
  import SignalPill from './SignalPill.svelte';
  import JevScorePanel from './JevScorePanel.svelte';

  export let lead: any;
  let expanded = false;

  $: email = lead.email_result?.email || lead.email || null;
  $: emailVerified = lead.email_result?.verified || lead.email_status === 'verified' || lead.email_status === 'valid' || false;
  $: signals = lead.signals || [];
  $: jevProbs = lead.jev_probs || {};
  $: score = lead.final_score || lead.tier1_score || 0;

  function extractDomain(url: string | null) {
    if (!url) return null;
    try {
      return new URL(url.startsWith('http') ? url : 'https://' + url).hostname.replace(/^www\./, '');
    } catch {
      return url;
    }
  }
</script>

<!-- Main Row -->
<tr
  class="table-row-base cursor-pointer hover:bg-[#faf7f3] transition-colors"
  on:click={() => (expanded = !expanded)}
>
  <!-- Score -->
  <td class="px-4 py-3">
    <ScoreBadge {score} maxScore={24} />
  </td>

  <!-- Company -->
  <td class="px-4 py-3">
    <div class="flex items-center gap-2.5">
      <div class="min-w-0">
        <p class="font-bold text-text-primary leading-tight truncate max-w-[190px]">{lead.company_name || lead.id}</p>
        <p class="text-xs text-text-muted mt-0.5 line-clamp-1 max-w-[220px]">{lead.one_liner || ''}</p>
      </div>
      {#if lead.is_competitor}
        <span class="badge badge-red text-[9px] flex-shrink-0">competitor</span>
      {/if}
      {#if lead.is_vertical_product && !lead.is_competitor}
        <span class="badge badge-yellow text-[9px] flex-shrink-0">vertical</span>
      {/if}
    </div>
  </td>

  <!-- Batch — YC logo from /flowjoy/yc.svg -->
  <td class="px-4 py-3 hidden md:table-cell">
    {#if lead.batch}
      <div class="inline-flex items-center gap-1.5 px-2 py-0.5 bg-orange-50 border border-orange-200 rounded-md">
        <div class="w-3.5 h-3.5 rounded-xs overflow-hidden flex-shrink-0">
          <img src="/flowjoy/yc.svg" alt="YC" class="w-full h-full object-contain" />
        </div>
        <span class="text-[10px] font-mono font-bold text-[#ea580c]">{lead.batch}</span>
      </div>
    {:else}
      <span class="text-text-muted text-sm">—</span>
    {/if}
  </td>

  <!-- Founder -->
  <td class="px-4 py-3 hidden lg:table-cell">
    {#if lead.founder_name}
      <p class="text-text-primary text-sm font-semibold">{lead.founder_name}</p>
      <p class="text-xs text-text-muted">{lead.founder_title || ''}</p>
    {:else}
      <span class="text-text-muted text-sm">—</span>
    {/if}
  </td>

  <!-- Email with Treg.to logo -->
  <td class="px-4 py-3 hidden lg:table-cell">
    {#if email}
      <div class="flex items-center gap-1.5">
        <div class="w-3.5 h-3.5 rounded flex items-center justify-center overflow-hidden flex-shrink-0">
          <img src="/flowjoy/treg-logo.png" alt="Treg.to" class="w-full h-full object-contain" />
        </div>
        <a
          href="mailto:{email}"
          class="font-mono text-xs text-blue-700 hover:underline truncate max-w-[140px] block"
          on:click|stopPropagation
        >
          {email}
        </a>
        {#if emailVerified}
          <span class="text-[8px] font-bold text-emerald-700 bg-emerald-50 px-1 py-0.2 rounded border border-emerald-200">
            ✓
          </span>
        {/if}
      </div>
    {:else}
      <span class="text-text-muted text-sm">—</span>
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

  <!-- Expand toggle chevron -->
  <td class="px-4 py-3 text-right">
    <svg
      class="w-4 h-4 text-text-muted transition-transform duration-200 inline-block {expanded ? 'rotate-90' : ''}"
      viewBox="0 0 16 16"
      fill="none"
    >
      <path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </td>
</tr>

<!-- ── Expanded Detail Panel ─────────────────────────────────────────── -->
{#if expanded}
<tr>
  <td colspan="7" class="px-0 py-0">
    <div class="detail-panel open">
      <div class="px-5 py-5 bg-[#fdf9f4] border-b border-[#e7dfd4] grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

        <!-- Column 1: Company Profile & Verified Links -->
        <div>
          <p class="label mb-2.5">Company Intel</p>
          <div class="bg-white rounded-xl p-3 border border-[#ede7de] shadow-2xs">
            <p class="text-text-primary font-bold text-sm">{lead.company_name}</p>
            {#if lead.one_liner}
              <p class="text-text-secondary text-xs mt-1 leading-relaxed">{lead.one_liner}</p>
            {/if}

            <!-- Company External Links with Real Logos -->
            <div class="flex flex-wrap gap-1.5 mt-3 pt-2.5 border-t border-[#f5efe6]">
              {#if lead.website}
                <a
                  href={lead.website}
                  target="_blank"
                  rel="noopener"
                  class="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#faf8f5] border border-[#e5ddd0] rounded-lg text-xs font-medium text-[#44403c] hover:bg-white hover:text-black transition-all shadow-2xs"
                >
                  <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
                    <circle cx="6" cy="6" r="5.25" stroke="currentColor" stroke-width="1.2"/>
                    <path d="M6 1.5C6 1.5 4 3.5 4 6s2 4.5 2 4.5M6 1.5C6 1.5 8 3.5 8 6s-2 4.5-2 4.5M1.5 6h9" stroke="currentColor" stroke-width="1.2"/>
                  </svg>
                  <span>{extractDomain(lead.website)}</span>
                </a>
              {/if}

              {#if lead.yc_url}
                <a
                  href={lead.yc_url}
                  target="_blank"
                  rel="noopener"
                  class="inline-flex items-center gap-1.5 px-2.5 py-1 bg-orange-50/80 border border-orange-200 rounded-lg text-xs font-semibold text-[#c2410c] hover:bg-orange-100/80 transition-all shadow-2xs"
                >
                  <div class="w-3.5 h-3.5 rounded-xs overflow-hidden flex-shrink-0">
                    <img src="/flowjoy/yc.svg" alt="YC" class="w-full h-full object-contain" />
                  </div>
                  <span>YC Profile</span>
                </a>
              {/if}

              {#if lead.linkedin_url}
                <a
                  href={lead.linkedin_url}
                  target="_blank"
                  rel="noopener"
                  class="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#0a66c2]/8 border border-[#0a66c2]/20 rounded-lg text-xs font-semibold text-[#0a66c2] hover:bg-[#0a66c2]/15 transition-all shadow-2xs"
                >
                  <!-- LinkedIn brand logo SVG -->
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="#0a66c2">
                    <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z"/>
                  </svg>
                  <span>Company LinkedIn</span>
                </a>
              {/if}
            </div>
          </div>
        </div>

        <!-- Column 2: Founder Details & Verified Contact -->
        <div>
          <p class="label mb-2.5">Founder & Contact</p>
          <div class="bg-white rounded-xl p-3 border border-[#ede7de] shadow-2xs">
            {#if lead.founders && lead.founders.length > 0}
              {#each lead.founders as f}
                <div class="mb-3 last:mb-0 pb-2.5 last:pb-0 border-b last:border-b-0 border-[#f5efe6]">
                  <p class="text-text-primary font-bold text-sm">{f.name}</p>
                  {#if f.title}<p class="text-text-muted text-xs mt-0.5">{f.title}</p>{/if}
                  <div class="flex gap-2 mt-2 flex-wrap">
                    {#if f.linkedin_url}
                      <a
                        href={f.linkedin_url}
                        target="_blank"
                        rel="noopener"
                        class="inline-flex items-center gap-1.5 px-2 py-0.5 bg-[#0a66c2]/8 border border-[#0a66c2]/20 rounded-lg text-[11px] font-medium text-[#0a66c2] hover:bg-[#0a66c2]/15 transition-all"
                      >
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="#0a66c2">
                          <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z"/>
                        </svg>
                        <span>Founder LinkedIn</span>
                      </a>
                    {/if}
                    {#if f.twitter_url}
                      <a
                        href={f.twitter_url}
                        target="_blank"
                        rel="noopener"
                        class="inline-flex items-center gap-1 px-2 py-0.5 bg-[#faf8f5] border border-[#e5ddd0] rounded-lg text-[11px] text-text-secondary hover:text-black transition-all"
                      >
                        <span>𝕏</span>
                      </a>
                    {/if}
                  </div>
                </div>
              {/each}
            {:else if lead.founder_name}
              <div class="mb-2">
                <p class="text-text-primary font-bold text-sm">{lead.founder_name}</p>
                {#if lead.founder_title}<p class="text-text-muted text-xs mt-0.5">{lead.founder_title}</p>{/if}
              </div>
            {:else}
              <p class="text-text-muted text-xs">No founder profile recorded</p>
            {/if}

            <!-- Verified Email Box with Treg.to Logo -->
            {#if email}
              <div class="mt-3 flex items-center justify-between gap-2 p-2.5 bg-[#faf8f5] border border-[#e5ddd0] rounded-xl shadow-2xs">
                <div class="flex items-center gap-2 min-w-0">
                  <div class="w-4 h-4 rounded overflow-hidden flex-shrink-0">
                    <img src="/flowjoy/treg-logo.png" alt="Treg.to" class="w-full h-full object-contain" />
                  </div>
                  <a
                    href="mailto:{email}"
                    class="font-mono text-xs text-blue-700 hover:underline truncate"
                    on:click|stopPropagation
                  >
                    {email}
                  </a>
                </div>
                {#if emailVerified}
                  <span class="text-[9px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 flex-shrink-0 font-mono">
                    ✓ VERIFIED
                  </span>
                {/if}
              </div>
            {/if}
          </div>
        </div>

        <!-- Column 3: JEV ICP Scoring Engine -->
        <div>
          <p class="label mb-2.5">ICP Scoring Engine</p>
          <JevScorePanel {jevProbs} {score} maxScore={24} />
        </div>

      </div>
    </div>
  </td>
</tr>
{/if}
