<!-- PipelineSteps.svelte — Pipeline stage filter tabs -->
<script lang="ts">
  export let activeStep: number = 0; // 0=all, 1=sourcing, 2=scorer, 3=enrichment
</script>

<div class="flex items-center gap-1 py-1.5 overflow-x-auto scrollbar-none">
  <div class="flex items-center gap-1 bg-[#ede8e1]/80 p-0.5 rounded-xl border border-[#ded6cc] text-[11px]">
    <button
      type="button"
      on:click={() => (activeStep = 0)}
      class="px-2.5 py-1 rounded-lg transition-all font-medium {activeStep === 0 ? 'bg-white text-text-primary shadow-xs font-semibold' : 'text-text-muted hover:text-text-primary'}"
    >
      All Steps
    </button>
    <button
      type="button"
      on:click={() => (activeStep = 1)}
      class="px-2.5 py-1 rounded-lg transition-all font-medium flex items-center gap-1.5 {activeStep === 1 ? 'bg-white text-[#c2410c] shadow-xs font-semibold' : 'text-text-muted hover:text-text-primary'}"
    >
      <span class="w-1.5 h-1.5 rounded-full bg-pipeline-source"></span>
      <span>01 Sourcing</span>
    </button>
    <button
      type="button"
      on:click={() => (activeStep = 2)}
      class="px-2.5 py-1 rounded-lg transition-all font-medium flex items-center gap-1.5 {activeStep === 2 ? 'bg-white text-[#7e22ce] shadow-xs font-semibold' : 'text-text-muted hover:text-text-primary'}"
    >
      <span class="w-1.5 h-1.5 rounded-full bg-pipeline-score"></span>
      <span>02 JEV Scoring</span>
    </button>
    <button
      type="button"
      on:click={() => (activeStep = 3)}
      class="px-2.5 py-1 rounded-lg transition-all font-medium flex items-center gap-1.5 {activeStep === 3 ? 'bg-white text-[#1d4ed8] shadow-xs font-semibold' : 'text-text-muted hover:text-text-primary'}"
    >
      <span class="w-1.5 h-1.5 rounded-full bg-pipeline-enrich"></span>
      <span>03 Enrichment</span>
    </button>
  </div>
</div>
