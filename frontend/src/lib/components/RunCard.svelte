<!-- RunCard.svelte — Pipeline run card, human-friendly dates, GrokBot, and funnel stats -->
<script lang="ts">
  import { funnelMetrics, totalSpend } from '$lib/types';
  import GrokBot from './GrokBot.svelte';

  export let run: any;

  // Human-readable date and time formatting
  function fmtRunId(id: string): { date: string; time: string } {
    const m = id.match(/run_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})?/);
    if (!m) return { date: 'Pipeline Execution', time: id };
    const d = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] ?? '0'));
    return {
      date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
      time: d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }),
    };
  }

  $: metrics = funnelMetrics(run.funnel || {});
  $: spend = totalSpend(run.spend || {});
  $: convRate = metrics.scraped > 0 ? ((metrics.qualified / metrics.scraped) * 100).toFixed(0) : '—';
  $: label = fmtRunId(run.run_id);

  $: statusColor =
    run.status === 'complete' ? 'bg-emerald-500' :
    run.status === 'error'    ? 'bg-red-500' :
                                'bg-amber-500 animate-pulse';
  $: statusLabel =
    run.status === 'complete' ? 'Completed' :
    run.status === 'error'    ? 'Failed' :
                                'Running';
</script>

<a
  href="/runs/{run.run_id}"
  class="card card-hover flex items-center justify-between p-4 group no-underline block gap-4 transition-all duration-200"
>
  <div class="flex items-center gap-3.5 min-w-0">
    <!-- GrokBot avatar with live status indicator -->
    <div class="flex-shrink-0 relative">
      <GrokBot size={36} theme="dark" />
      <span class="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white {statusColor}"></span>
    </div>

    <!-- Friendly Date & Time -->
    <div class="min-w-0">
      <p class="font-bold text-sm text-text-primary group-hover:text-[#c2410c] transition-colors leading-tight">
        {label.date}
      </p>
      <p class="text-xs text-[#78716c] mt-0.5 font-medium">
        {label.time} · <span class="font-semibold {run.status === 'complete' ? 'text-emerald-700' : 'text-[#78716c]'}">{statusLabel}</span>
      </p>
    </div>
  </div>

  <!-- Funnel Stats Bar -->
  <div class="hidden sm:flex items-center gap-4 text-center flex-shrink-0">
    <div>
      <p class="text-sm font-bold text-text-primary">{metrics.scraped}</p>
      <p class="text-[9px] text-[#78716c] uppercase tracking-wide font-medium">scraped</p>
    </div>
    <span class="text-[#a8a29e] text-xs">→</span>
    <div>
      <p class="text-sm font-bold text-text-primary">{metrics.scored}</p>
      <p class="text-[9px] text-[#78716c] uppercase tracking-wide font-medium">scored</p>
    </div>
    <span class="text-[#a8a29e] text-xs">→</span>
    <div>
      <p class="text-sm font-bold text-text-primary">{metrics.withEmail}</p>
      <p class="text-[9px] text-[#78716c] uppercase tracking-wide font-medium">emails</p>
    </div>
    <span class="text-[#a8a29e] text-xs">→</span>
    <div>
      <p class="text-sm font-bold text-emerald-700">{metrics.qualified}</p>
      <p class="text-[9px] text-[#78716c] uppercase tracking-wide font-medium">qualified</p>
    </div>

    <div class="w-px h-6 bg-[#e7dfd4] mx-1"></div>

    <div class="text-right">
      <p class="text-sm font-mono font-bold text-text-secondary">{convRate}{convRate !== '—' ? '%' : ''}</p>
      <p class="text-[9px] text-[#78716c] uppercase tracking-wide font-medium">yield</p>
    </div>

    <div class="text-right hidden lg:block">
      <p class="text-sm font-mono font-bold text-text-secondary">${spend.toFixed(3)}</p>
      <p class="text-[9px] text-[#78716c] uppercase tracking-wide font-medium">cost</p>
    </div>
  </div>

  <!-- Right Chevron -->
  <svg class="w-4 h-4 text-text-muted group-hover:text-[#c2410c] group-hover:translate-x-0.5 transition-all flex-shrink-0" viewBox="0 0 16 16" fill="none">
    <path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
</a>
