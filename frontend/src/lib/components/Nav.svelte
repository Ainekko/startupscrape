<!-- Nav.svelte — Header bar with GrokBot logo -->
<script>
  import { page } from '$app/stores';
  import GrokBot from './GrokBot.svelte';
</script>

<nav class="sticky top-0 z-50 w-full border-b border-[#e7dfd4] bg-[#fbf9f5]/90 backdrop-blur-md">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex h-14 items-center justify-between">
      <!-- Logo -->
      <a href="/" class="flex items-center gap-2.5 group no-underline">
        <GrokBot size={30} theme="dark" />
        <div class="flex items-center gap-2">
          <span class="text-base font-extrabold text-[#1c1917] tracking-tight group-hover:text-[#c2410c] transition-colors">
            Verve
          </span>
          <span class="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-orange-50 text-[#c2410c] border border-orange-200">
            Pipeline
          </span>
        </div>
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

      <!-- New run button -->
      <a href="/runs/new" class="btn-primary text-xs px-3 py-1.5">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M6 1v10M1 6h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        New Run
      </a>
    </div>
  </div>
</nav>
