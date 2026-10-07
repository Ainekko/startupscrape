<!-- PipelineEconomics.svelte — Bottom bar showing pipeline stage flow with real logos -->
<script lang="ts">
</script>

<div class="pt-3 mt-2 border-t border-[#e7dfd4] flex flex-wrap items-center justify-between gap-2 text-[10px] text-[#78716c] font-mono">
  <div class="flex items-center flex-wrap gap-2">
    <span class="text-[#c2410c] font-bold">PIPELINE:</span>

    <div class="flex items-center gap-1.5">
      <img src="/flowjoy/algolia.svg" alt="Algolia" class="w-3.5 h-3.5 object-contain" />
      <span class="text-[#1c1917] font-semibold">Algolia Search</span>
    </div>

    <span class="text-[#a8a29e]">→</span>

    <div class="flex items-center gap-1.5">
      <img src="/flowjoy/typesafe-ai-200x200.jfif" alt="JEV" class="w-3.5 h-3.5 rounded-xs object-cover border border-purple-200" />
      <span class="text-[#7e22ce] font-semibold">JEV ICP Scoring</span>
    </div>

    <span class="text-[#a8a29e]">→</span>

    <div class="flex items-center gap-1.5">
      <img src="/flowjoy/treg-logo.png" alt="Treg.to" class="w-3.5 h-3.5 object-contain" />
      <span class="text-[#059669] font-semibold">Treg.to Email Enrichment</span>
    </div>
  </div>

  <div class="flex items-center gap-2">
    <span class="text-[#78716c] font-medium">Verve Autonomous Outbound Engine</span>
  </div>
</div>
