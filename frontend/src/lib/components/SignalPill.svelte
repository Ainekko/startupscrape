<!-- SignalPill.svelte -->
<script>
  export let sig = '';

  // Extract emoji and text
  $: emoji = sig.match(/^(\p{Emoji})/u)?.[1] || '';
  $: text  = sig.replace(/^(\p{Emoji}\s*)/u, '').replace(/\s*\([^)]+\)$/, '').trim();

  // Color by signal type heuristic
  $: color =
    sig.includes('Core') || sig.includes('GTM')     ? 'bg-accent/10 text-accent border-accent/15' :
    sig.includes('Tier-1') || sig.includes('Batch')  ? 'bg-blue-400/10 text-blue-300 border-blue-400/15' :
    sig.includes('Hiring') || sig.includes('Job')    ? 'bg-purple-400/10 text-purple-300 border-purple-400/15' :
                                                       'bg-surface-4 text-text-secondary border-border';
</script>

<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-xs {color}" title={sig}>
  {#if emoji}<span>{emoji}</span>{/if}
  <span class="truncate max-w-[120px]">{text}</span>
</span>
