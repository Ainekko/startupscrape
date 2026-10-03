<!-- PipelineSteps.svelte — Three-column pipeline progress bar (illustration header tabs) -->
<script lang="ts">
  export let activeStep: number = 0; // 0=overview, 1=sourcing, 2=scorer, 3=enrichment
</script>

<div class="flex items-center justify-between gap-1 py-1.5 overflow-x-auto scrollbar-none">
  <div class="flex items-center gap-1 bg-[#ede8e1]/80 p-0.5 rounded-xl border border-[#ded6cc] text-[11px]">
    <button
      type="button"
      on:click={() => (activeStep = 0)}
      class="px-2.5 py-1 rounded-lg transition-all font-medium {activeStep === 0 ? 'bg-white text-text-primary shadow-xs font-semibold' : 'text-text-muted hover:text-text-primary'}"
    >
      Pipeline Overview
    </button>
    <button
      type="button"
      on:click={() => (activeStep = 1)}
      class="px-2.5 py-1 rounded-lg transition-all font-medium flex items-center gap-1.5 {activeStep === 1 ? 'bg-white text-[#c2410c] shadow-xs font-semibold' : 'text-text-muted hover:text-text-primary'}"
    >
      <span class="w-1.5 h-1.5 rounded-full bg-pipeline-source"></span>
      <span>01 Sourcing ($0.00)</span>
    </button>
    <button
      type="button"
      on:click={() => (activeStep = 2)}
      class="px-2.5 py-1 rounded-lg transition-all font-medium flex items-center gap-1.5 {activeStep === 2 ? 'bg-white text-[#7e22ce] shadow-xs font-semibold' : 'text-text-muted hover:text-text-primary'}"
    >
      <span class="w-1.5 h-1.5 rounded-full bg-pipeline-score"></span>
      <span>02 JEV Scoring ($0.04)</span>
    </button>
    <button
      type="button"
      on:click={() => (activeStep = 3)}
      class="px-2.5 py-1 rounded-lg transition-all font-medium flex items-center gap-1.5 {activeStep === 3 ? 'bg-white text-[#1d4ed8] shadow-xs font-semibold' : 'text-text-muted hover:text-text-primary'}"
    >
      <span class="w-1.5 h-1.5 rounded-full bg-pipeline-enrich"></span>
      <span>03 Treg.to ($0.005)</span>
    </button>
  </div>

  <div class="hidden lg:flex items-center gap-2 text-[10px] text-text-muted font-mono">
    <span class="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 font-semibold border border-emerald-200">
      91% CHEAPER THAN APOLLO
    </span>
    <span>•</span>
    <span class="text-text-secondary">50 Leads = $0.22 Total</span>
  </div>
</div>
