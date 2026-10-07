<!-- PipelineFlowHeader.svelte — Interactive workflow header with real logos and GrokBot -->
<script lang="ts">
  import GrokBot from './GrokBot.svelte';

  export let leadCount: number | null = null;
  export let uniqueCount: number | null = null;
</script>

<div class="mb-7 bg-white border border-[#e7dfd4] rounded-2xl p-4 sm:p-5 shadow-sm">
  <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
    <!-- Left: GrokBot + Title -->
    <div class="flex items-center gap-3.5">
      <GrokBot size={44} theme="dark" />
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-xl font-bold text-[#1c1917] tracking-tight">Verified Startup Leads</h1>
          <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
            Live
          </span>
        </div>
        <p class="text-xs text-[#78716c] mt-0.5 font-medium">
          {#if uniqueCount !== null}
            <span class="font-bold text-[#1c1917]">{uniqueCount}</span> unique qualified prospects
            {#if leadCount && leadCount !== uniqueCount}
              <span class="text-[#a8a29e]"> · {leadCount} runs scanned</span>
            {/if}
          {:else}
            Evaluating pipeline leads…
          {/if}
        </p>
      </div>
    </div>

    <!-- Right: Pipeline workflow banner with real logos -->
    <div class="flex items-center flex-wrap gap-2 text-xs font-mono bg-[#fbf9f5] border border-[#ded6cc] px-3 py-2 rounded-xl shadow-2xs">
      <span class="text-[11px] font-black text-[#c2410c] tracking-wider uppercase mr-0.5">PIPELINE:</span>

      <!-- Step 1: Algolia Search -->
      <div class="flex items-center gap-1.5 px-2.5 py-1 bg-white rounded-lg border border-[#e5ddd0] shadow-xs">
        <div class="w-4 h-4 rounded flex items-center justify-center overflow-hidden flex-shrink-0">
          <img src="/flowjoy/algolia.svg" alt="Algolia" class="w-full h-full object-contain" />
        </div>
        <div class="w-3.5 h-3.5 rounded flex items-center justify-center overflow-hidden flex-shrink-0 -ml-0.5">
          <img src="/flowjoy/yc.svg" alt="YC" class="w-full h-full object-contain" />
        </div>
        <span class="font-bold text-[#1c1917] text-[11px]">Algolia Search</span>
      </div>

      <!-- Arrow -->
      <span class="text-[#a8a29e] font-bold text-sm">→</span>

      <!-- Step 2: JEV ICP Scoring -->
      <div class="flex items-center gap-1.5 px-2.5 py-1 bg-white rounded-lg border border-purple-200 shadow-xs">
        <div class="w-4 h-4 rounded-xs overflow-hidden flex-shrink-0 border border-purple-100">
          <img src="/flowjoy/typesafe-ai-200x200.jfif" alt="JEV" class="w-full h-full object-cover" />
        </div>
        <span class="font-bold text-[#7e22ce] text-[11px]">JEV ICP Scoring</span>
      </div>

      <!-- Arrow -->
      <span class="text-[#a8a29e] font-bold text-sm">→</span>

      <!-- Step 3: Treg.to Email Enrichment -->
      <div class="flex items-center gap-1.5 px-2.5 py-1 bg-white rounded-lg border border-emerald-200 shadow-xs">
        <div class="w-4 h-4 rounded flex items-center justify-center overflow-hidden flex-shrink-0">
          <img src="/flowjoy/treg-logo.png" alt="Treg.to" class="w-full h-full object-contain" />
        </div>
        <span class="font-bold text-[#059669] text-[11px]">Treg.to Email Enrichment</span>
      </div>
    </div>
  </div>
</div>
