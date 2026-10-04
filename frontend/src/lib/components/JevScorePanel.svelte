<!-- JevScorePanel.svelte — JEV ICP Scoring Engine panel matching the case study illustration -->
<script lang="ts">
  import GrokBot from './GrokBot.svelte';

  export let jevProbs: Record<string, Record<string, number>> = {};
  export let score: number = 0;
  export let maxScore: number = 24;

  $: scorePct = maxScore > 0 ? Math.min(Math.round((score / maxScore) * 100), 100) : 0;

  // Configuration for the 5 core JEV dimensions requested
  const DIMENSIONS = [
    {
      key: 'is_b2b',
      label: 'is b2b',
      desc: 'B2B Software Model',
      defaultVal: 'true',
      defaultPct: 95,
      isGood: (v: string) => v === 'true',
      tagGood: 'Core B2B Target',
      tagBad: 'B2C Model',
    },
    {
      key: 'has_gtm_hire',
      label: 'has gtm hire',
      desc: 'Sales Team Presence',
      defaultVal: 'false',
      defaultPct: 85,
      isGood: (v: string) => v === 'false', // false is good! (founder bottleneck)
      tagGood: 'Founder-Led Sales (0 GTM Hires)',
      tagBad: 'Dedicated Sales Team',
    },
    {
      key: 'funding_stage',
      label: 'funding stage',
      desc: 'Capital Maturity',
      defaultVal: 'seed',
      defaultPct: 65,
      isGood: () => true,
      tagGood: 'Fresh Seed Stage (<90 days)',
      tagBad: 'Unknown Stage',
    },
    {
      key: 'is_competitor',
      altKey: 'is_competitor_or_overlap',
      label: 'is competitor',
      desc: 'Product Cannibalization',
      defaultVal: 'false',
      defaultPct: 95,
      isGood: (v: string) => v === 'false',
      tagGood: 'Zero Product Overlap',
      tagBad: 'Direct Competitor Overlap',
    },
    {
      key: 'is_vertical',
      altKey: 'is_vertical_product',
      label: 'is vertical',
      desc: 'Vertical Industry Focus',
      defaultVal: 'true',
      defaultPct: 90,
      isGood: (v: string) => v === 'true',
      tagGood: 'High-Retention Vertical SaaS',
      tagBad: 'Horizontal General Tool',
    },
  ];

  function extractTop(probsObj: any) {
    if (!probsObj || typeof probsObj !== 'object') return null;
    const entries = Object.entries(probsObj).sort((a: any, b: any) => b[1] - a[1]);
    return entries[0] || null;
  }

  $: resolvedDimensions = DIMENSIONS.map((dim) => {
    const raw = jevProbs[dim.key] || (dim.altKey ? jevProbs[dim.altKey] : null);
    const top = extractTop(raw);

    const val = top ? String(top[0]) : dim.defaultVal;
    const pct = top ? Math.round(Number(top[1]) * 100) : dim.defaultPct;
    const good = dim.isGood(val);

    return {
      label: dim.label,
      desc: dim.desc,
      val,
      pct,
      good,
      tag: good ? dim.tagGood : dim.tagBad,
    };
  });
</script>

<div class="space-y-3">
  <!-- Overall ICP Intent Score Card (from illustration) -->
  <div class="bg-gradient-to-br from-[#faf5ff] to-[#fff7ed] rounded-xl p-3 border border-purple-200/90 shadow-2xs">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2.5">
        <div class="w-8 h-8 rounded-lg bg-white border border-purple-200 overflow-hidden flex items-center justify-center shadow-xs flex-shrink-0">
          <img src="/flowjoy/typesafe-ai-200x200.jfif" alt="TypeSafe AI" class="w-full h-full object-cover" />
        </div>
        <div>
          <div class="text-[9px] font-mono uppercase tracking-wider text-purple-700 font-bold flex items-center gap-1.5">
            <span>JEV ICP Intent Score</span>
            <span class="text-[8px] text-[#78716c] font-normal">320ms</span>
          </div>
          <div class="text-xl font-black tracking-tight text-[#1c1917] flex items-baseline gap-1 mt-0.5">
            {score > 0 ? score : Math.round(scorePct * 0.94)}
            <span class="text-xs font-mono font-medium text-purple-600">/{maxScore > 0 ? maxScore : 100}</span>
            <span class="text-[10px] font-mono text-[#78716c] font-normal ml-1">({scorePct}%)</span>
          </div>
        </div>
      </div>

      <div class="text-right">
        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 border border-purple-200 inline-block mb-0.5 shadow-2xs">
          Top 5% Priority
        </span>
        <div class="text-[9px] font-mono text-[#78716c]">Discards Unfit Leads</div>
      </div>
    </div>

    <!-- Animated Shimmer Gradient Progress Bar -->
    <div class="w-full bg-purple-100 h-2.5 rounded-full overflow-hidden mt-2.5 relative">
      <div
        class="score-bar-fill h-full rounded-full transition-all duration-700"
        style="width: {scorePct}%"
      ></div>
    </div>
  </div>

  <!-- Dimension Checklist with Gradient Shimmer Bars -->
  <div class="space-y-2">
    {#each resolvedDimensions as item}
      <div class="bg-white rounded-xl p-2.5 border border-[#ede7de] shadow-2xs hover:border-purple-200 transition-colors">
        <!-- Top row: key name, value pill, percentage -->
        <div class="flex items-center justify-between mb-1.5">
          <div class="flex items-center gap-2">
            <span class="text-xs font-mono font-bold text-[#1c1917]">{item.label}</span>
            <span class="text-[9px] text-[#78716c] hidden sm:inline">· {item.tag}</span>
          </div>

          <div class="flex items-center gap-1.5">
            <span
              class="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase
              {item.good
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'bg-red-50 text-red-800 border border-red-200'}"
            >
              {item.val}
            </span>
            <span class="text-xs font-mono font-bold text-[#7e22ce]">{item.pct}%</span>
          </div>
        </div>

        <!-- Dimension Animated Gradient Shimmer Bar -->
        <div class="w-full bg-[#f3e8ff] h-1.5 rounded-full overflow-hidden relative">
          <div
            class="score-bar-fill h-full rounded-full transition-all duration-700"
            style="width: {item.pct}%"
          ></div>
        </div>
      </div>
    {/each}
  </div>
</div>

<style>
  .score-bar-fill {
    background: linear-gradient(90deg, #9333ea, #f59e0b);
    position: relative;
    overflow: hidden;
  }

  .score-bar-fill::after {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.7), transparent);
    animation: barShimmer 2s infinite;
  }

  @keyframes barShimmer {
    0% { transform: translateX(0%); }
    100% { transform: translateX(200%); }
  }
</style>

