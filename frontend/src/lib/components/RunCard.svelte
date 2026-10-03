<!-- RunCard.svelte — Pipeline run card matching illustration's warm cream style -->
<script>
  export let run;

  function fmtDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('en-US', {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  }

  function fmtRunId(id) {
    const m = id.match(/run_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})/);
    if (!m) return id;
    return `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]}`;
  }

  $: scraped   = run.funnel?.scraped || 0;
  $: enriched  = run.funnel?.enriched || 0;
  $: qualified = run.funnel?.qualified || run.lead_count || 0;
  $: spend     = run.spend?.total_usd || 0;
  $: convRate  = scraped ? ((qualified / scraped) * 100).toFixed(0) : '0';

  $: statusColor =
    run.status === 'complete' ? 'bg-emerald-500' :
    run.status === 'error'    ? 'bg-red-500' :
                                'bg-amber-500 animate-pulse';

  $: statusBadge =
    run.status === 'complete' ? 'badge-green' :
    run.status === 'error'    ? 'badge-red' :
                                'badge-yellow';
</script>

<a
  href="/runs/{run.run_id}"
  class="card card-hover flex items-center justify-between p-5 group no-underline block"
>
  <div class="flex items-center gap-5 min-w-0">
    <!-- Status dot -->
    <div class="w-2.5 h-2.5 rounded-full flex-shrink-0 {statusColor}"></div>

    <!-- Run ID / time -->
    <div class="min-w-0">
      <p class="font-mono text-sm text-text-primary font-semibold group-hover:text-[#c2410c] transition-colors">
        {fmtRunId(run.run_id)}
      </p>
      <p class="text-xs text-text-muted mt-0.5 font-mono">{run.run_id}</p>
    </div>
  </div>

  <!-- Funnel numbers -->
  <div class="hidden sm:flex items-center gap-6 text-center">
    <div>
      <p class="text-sm font-semibold text-text-primary">{scraped}</p>
      <p class="text-[10px] text-text-muted uppercase tracking-wide">scraped</p>
    </div>
    <div class="w-px h-6 bg-surface-4"></div>
    <div>
      <p class="text-sm font-semibold text-text-primary">{enriched}</p>
      <p class="text-[10px] text-text-muted uppercase tracking-wide">enriched</p>
    </div>
    <div class="w-px h-6 bg-surface-4"></div>
    <div>
      <p class="text-sm font-semibold text-emerald-700">{qualified}</p>
      <p class="text-[10px] text-text-muted uppercase tracking-wide">qualified</p>
    </div>
    <div class="w-px h-6 bg-surface-4"></div>
    <div>
      <p class="text-sm font-semibold text-text-primary">{convRate}%</p>
      <p class="text-[10px] text-text-muted uppercase tracking-wide">conv.</p>
    </div>
    <div class="w-px h-6 bg-surface-4"></div>
    <div>
      <p class="text-sm font-mono font-semibold text-text-secondary">${spend.toFixed(3)}</p>
      <p class="text-[10px] text-text-muted uppercase tracking-wide">spend</p>
    </div>
  </div>

  <!-- Arrow -->
  <svg class="w-4 h-4 text-text-muted group-hover:text-[#c2410c] group-hover:translate-x-0.5 transition-all flex-shrink-0" viewBox="0 0 16 16" fill="none">
    <path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
</a>
