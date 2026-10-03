<!-- PipelineEconomics.svelte — Bottom bar showing pipeline cost breakdown -->
<script lang="ts">
  // Static cost breakdown, mirroring the illustration footer
</script>

<div class="pt-2 mt-1 border-t border-[#e7dfd4] flex flex-wrap items-center justify-between gap-2 text-[10px] text-text-muted font-mono">
  <div class="flex items-center gap-1.5 sm:gap-2">
    <span class="text-[#c2410c] font-bold">PIPELINE:</span>
    <span class="text-text-primary font-semibold">Algolia Search ($0.00)</span>
    <span class="text-text-faint">→</span>
    <span class="text-[#7e22ce] font-semibold">JEV ICP Score ($0.04)</span>
    <span class="text-text-faint">→</span>
    <span class="text-[#059669] font-semibold">Treg.to Verified Hit ($0.005)</span>
    <span class="text-text-faint">=</span>
    <span class="text-[#c2410c] font-bold bg-orange-50 px-1.5 py-0.5 rounded border border-orange-200">
      $0.045 Total / Qualified Lead
    </span>
  </div>

  <div class="flex items-center gap-2">
    <span class="text-text-secondary font-medium">Zero Waste Outbound Engine</span>
  </div>
</div>
