<!-- ScoreBadge.svelte — Score indicator matching illustration style -->
<script>
  export let score = 0;
  export let maxScore = 100;

  $: pct = maxScore > 0 ? (score / maxScore) * 100 : 0;

  $: tier =
    pct >= 70 ? 'high' :
    pct >= 40 ? 'mid' :
    'low';

  $: color =
    tier === 'high' ? 'text-emerald-800 bg-emerald-50 border-emerald-200' :
    tier === 'mid'  ? 'text-amber-800 bg-amber-50 border-amber-200' :
                      'text-red-800 bg-red-50 border-red-200';
</script>

<span class="inline-flex items-center justify-center w-10 h-7 rounded-md border font-mono text-xs font-bold {color}">
  {score}
</span>
