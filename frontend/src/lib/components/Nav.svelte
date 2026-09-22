<!-- Nav.svelte -->
<script>
  import { page } from '$app/stores';
</script>

<nav class="sticky top-0 z-50 w-full border-b border-border bg-surface-1/80 backdrop-blur-md">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex h-14 items-center justify-between">
      <!-- Logo -->
      <a href="/" class="flex items-center gap-2.5 group">
        <div class="w-7 h-7 rounded-lg bg-accent/10 border border-accent/30 flex items-center justify-center group-hover:bg-accent/20 transition-colors">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="7" cy="7" r="6" stroke="#6ee7b7" stroke-width="1.5"/>
            <path d="M4 7l2 2 4-4" stroke="#6ee7b7" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <span class="text-sm font-semibold text-text-primary">startupscrape</span>
      </a>

      <!-- Nav links -->
      <div class="flex items-center gap-1">
        <a
          href="/"
          class="px-3 py-1.5 rounded-lg text-sm transition-colors {$page.url.pathname === '/' ? 'text-text-primary bg-surface-3' : 'text-text-secondary hover:text-text-primary hover:bg-surface-3'}"
        >
          Runs
        </a>
        <a
          href="/leads"
          class="px-3 py-1.5 rounded-lg text-sm transition-colors {$page.url.pathname.startsWith('/leads') ? 'text-text-primary bg-surface-3' : 'text-text-secondary hover:text-text-primary hover:bg-surface-3'}"
        >
          All Leads
        </a>
      </div>

      <!-- Run button -->
      <div class="flex items-center gap-3">
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
