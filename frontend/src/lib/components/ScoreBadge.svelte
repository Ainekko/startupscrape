<!-- ScoreBadge.svelte — Score indicator with JEV-style ring -->
<script>
  export let score = 0;
  export let maxScore = 24;

  $: pct = maxScore > 0 ? Math.min((score / maxScore) * 100, 100) : 0;

  $: tier =
    pct >= 70 ? 'high' :
    pct >= 40 ? 'mid' :
    'low';

  $: ringColor =
    tier === 'high' ? '#059669' :
    tier === 'mid'  ? '#d97706' :
                      '#dc2626';

  $: textColor =
    tier === 'high' ? 'text-emerald-800' :
    tier === 'mid'  ? 'text-amber-800' :
                      'text-red-800';

  // SVG arc math
  const R = 11;
  const CIRC = 2 * Math.PI * R;
  $: dash = (pct / 100) * CIRC;
  $: gap = CIRC - dash;
</script>

<div class="relative inline-flex items-center justify-center w-[38px] h-[38px]">
  <svg width="38" height="38" viewBox="0 0 38 38" fill="none" class="-rotate-90">
    <!-- Track -->
    <circle cx="19" cy="19" r={R} stroke="#e7e5e4" stroke-width="2.5" fill="none"/>
    <!-- Progress arc -->
    <circle
      cx="19" cy="19" r={R}
      stroke={ringColor}
      stroke-width="2.5"
      fill="none"
      stroke-linecap="round"
      stroke-dasharray="{dash} {gap}"
    />
  </svg>
  <span class="absolute text-[10px] font-black {textColor} leading-none">{score}</span>
</div>
