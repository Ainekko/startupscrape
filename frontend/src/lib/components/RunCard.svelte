<!-- RunCard.svelte -->
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
    // run_20260922_143528 → 2026-09-22 14:35
    const m = id.match(/run_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})/);
    if (!m) return id;
    return `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]}`;
  }

  $: scraped   = run.funnel?.scraped || 0;
  $: enriched  = run.funnel?.enriched || 0;
  $: qualified = run.funnel?.qualified || run.lead_count || 0;
  $: spend     = run.spend?.total_usd || 0;
  $: convRate  = scraped ? ((qualified / scraped) * 100).toFixed(0) : '0';
</script>

<a
  href="/runs/{run.run_id}"
  class="card card-hover flex items-center justify-between p-5 group no-underline block"
>
  <div class="flex items-center gap-5 min-w-0">
    <!-- Status dot -->
    <div class="w-2 h-2 rounded-full flex-shrink-0 {run.status === 'complete' ? 'bg-accent' : run.status === 'error' ? 'bg-red-400' : 'bg-yellow-400 animate-pulse'}"></div>

    <!-- Run ID / time -->
    <div class="min-w-0">
      <p class="font-mono text-sm text-text-primary font-medium group-hover:text-accent transition-colors">
        {fmtRunId(run.run_id)}
      </p>
      <p class="text-xs text-text-muted mt-0.5">{run.run_id}</p>
    </div>
  </div>

  <!-- Funnel numbers -->
  <div class="hidden sm:flex items-center gap-8 text-center">
    <div>
      <p class="text-sm font-medium text-text-primary">{scraped}</p>
      <p class="text-xs text-text-muted">scraped</p>
    </div>
    <div class="w-px h-6 bg-border"></div>
    <div>
      <p class="text-sm font-medium text-text-primary">{enriched}</p>
      <p class="text-xs text-text-muted">enriched</p>
    </div>
    <div class="w-px h-6 bg-border"></div>
    <div>
      <p class="text-sm font-medium text-accent">{qualified}</p>
      <p class="text-xs text-text-muted">qualified</p>
    </div>
    <div class="w-px h-6 bg-border"></div>
    <div>
      <p class="text-sm font-medium text-text-primary">{convRate}%</p>
      <p class="text-xs text-text-muted">conv.</p>
    </div>
    <div class="w-px h-6 bg-border"></div>
    <div>
      <p class="text-sm font-medium text-text-secondary">${spend.toFixed(3)}</p>
      <p class="text-xs text-text-muted">spend</p>
    </div>
  </div>

  <!-- Arrow -->
  <svg class="w-4 h-4 text-text-muted group-hover:text-text-secondary group-hover:translate-x-0.5 transition-all flex-shrink-0" viewBox="0 0 16 16" fill="none">
    <path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
</a>
