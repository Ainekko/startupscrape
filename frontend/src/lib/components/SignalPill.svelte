<!-- SignalPill.svelte — Signal tag matching illustration warm style -->
<script>
  export let sig = '';

  // Extract emoji and text
  $: emoji = sig.match(/^(\p{Emoji})/u)?.[1] || '';
  $: text  = sig.replace(/^(\p{Emoji}\s*)/u, '').replace(/\s*\([^)]+\)$/, '').trim();

  // Color by signal type heuristic — warm palette
  $: color =
    sig.includes('Core') || sig.includes('GTM')     ? 'bg-orange-50 text-[#9a3412] border-orange-200' :
    sig.includes('Tier-1') || sig.includes('Batch')  ? 'bg-blue-50 text-blue-800 border-blue-200' :
    sig.includes('Hiring') || sig.includes('Job')    ? 'bg-purple-50 text-purple-800 border-purple-200' :
                                                       'bg-surface-1 text-text-secondary border-surface-4';
</script>

<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-xs font-medium {color}" title={sig}>
  {#if emoji}<span>{emoji}</span>{/if}
  <span class="truncate max-w-[120px]">{text}</span>
</span>
