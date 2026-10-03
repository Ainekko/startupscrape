<!-- PipelineEconomics.svelte — Bottom bar showing pipeline stage flow -->
<script lang="ts">
  // Pipeline stage labels — no hardcoded costs, those come from data
</script>

<div class="pt-2 mt-1 border-t border-[#e7dfd4] flex flex-wrap items-center justify-between gap-2 text-[10px] text-text-muted font-mono">
  <div class="flex items-center gap-1.5 sm:gap-2">
    <span class="text-[#c2410c] font-bold">PIPELINE:</span>
    <span class="text-text-primary font-semibold">Algolia Search</span>
    <span class="text-text-faint">→</span>
    <span class="text-[#7e22ce] font-semibold">JEV ICP Scoring</span>
    <span class="text-text-faint">→</span>
    <span class="text-[#059669] font-semibold">Treg.to Email Enrichment</span>
  </div>

  <div class="flex items-center gap-2">
    <span class="text-text-secondary font-medium">StartupScrape Pipeline v1.1</span>
  </div>
</div>
