<!-- Nav.svelte — Warm header bar matching case study illustration -->
<script>
  import { page } from '$app/stores';
</script>

<nav class="sticky top-0 z-50 w-full border-b border-[#e7dfd4] bg-[#fbf9f5]/90 backdrop-blur-md">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex h-14 items-center justify-between">
      <!-- Logo -->
      <a href="/" class="flex items-center gap-2.5 group">
        <span class="text-[#c2410c] font-black text-base">⚡</span>
        <span class="text-sm font-bold text-text-primary tracking-tight">StartupScrape</span>
        <span class="text-[10px] font-mono font-bold text-[#c2410c] bg-orange-50 px-2 py-0.5 rounded-full border border-orange-200 hidden sm:inline">
          $0.045 / Lead
        </span>
      </a>

      <!-- Nav links -->
      <div class="flex items-center gap-1">
        <a
          href="/"
          class="px-3 py-1.5 rounded-lg text-sm transition-colors {$page.url.pathname === '/' ? 'text-text-primary bg-white shadow-xs font-semibold border border-surface-4' : 'text-text-muted hover:text-text-primary hover:bg-surface-3'}"
        >
          Runs
        </a>
        <a
          href="/leads"
          class="px-3 py-1.5 rounded-lg text-sm transition-colors {$page.url.pathname.startsWith('/leads') ? 'text-text-primary bg-white shadow-xs font-semibold border border-surface-4' : 'text-text-muted hover:text-text-primary hover:bg-surface-3'}"
        >
          All Leads
        </a>
      </div>

      <!-- Run button -->
      <div class="flex items-center gap-3">
        <!-- Tech stack pills (hidden on small) -->
        <div class="hidden lg:flex items-center gap-1.5">
          <span class="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 font-semibold border border-emerald-200 text-[10px] font-mono">
            91% CHEAPER
          </span>
        </div>
        <a href="/runs/new" class="btn-primary text-xs px-3 py-1.5">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M6 1v10M1 6h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          New Run
        </a>
      </div>
    </div>
  </div>
</nav>
