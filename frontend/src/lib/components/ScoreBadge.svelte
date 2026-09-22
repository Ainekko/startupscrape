<!-- ScoreBadge.svelte -->
<script>
  export let score = 0;

  $: tier =
    score >= 30 ? 'high' :
    score >= 15 ? 'mid' :
    'low';

  $: color =
    tier === 'high' ? 'text-lead-high bg-lead-high/10 border-lead-high/20' :
    tier === 'mid'  ? 'text-lead-mid bg-lead-mid/10 border-lead-mid/20' :
                     'text-lead-low bg-lead-low/10 border-lead-low/20';
</script>

<span class="inline-flex items-center justify-center w-10 h-7 rounded-md border font-mono text-xs font-semibold {color}">
  {score}
</span>
