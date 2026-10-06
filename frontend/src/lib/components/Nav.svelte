<!-- Nav.svelte — Responsive header: hamburger on mobile, full bar on desktop -->
<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import GrokBot from './GrokBot.svelte';
  import { api } from '$lib/api';

  let menuOpen = false;

  // Close menu on navigation
  $: $page, (menuOpen = false);

  function logout() {
    api.auth.logout();
    goto('/login');
  }

  function isActive(path: string) {
    return path === '/'
      ? $page.url.pathname === '/'
      : $page.url.pathname.startsWith(path);
  }
</script>

<nav class="sticky top-0 z-50 w-full border-b border-[#e7dfd4] bg-[#fbf9f5]/95 backdrop-blur-md">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex h-14 items-center justify-between gap-3">

      <!-- Logo (always visible) -->
      <a href="/" class="flex items-center gap-2.5 group no-underline flex-shrink-0">
        <GrokBot size={28} theme="dark" />
        <div class="flex items-center gap-1.5">
          <span class="text-base font-extrabold text-[#1c1917] tracking-tight group-hover:text-[#c2410c] transition-colors">
            Verve
          </span>
          <span class="hidden sm:inline text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-orange-50 text-[#c2410c] border border-orange-200">
            Pipeline
          </span>
        </div>
      </a>

      <!-- Desktop nav links (hidden on mobile) -->
      <div class="hidden sm:flex items-center gap-1 flex-1 justify-center">
        <a
          href="/"
          class="px-3 py-1.5 rounded-lg text-sm transition-colors {isActive('/') ? 'text-text-primary bg-white shadow-xs font-semibold border border-surface-4' : 'text-text-muted hover:text-text-primary hover:bg-surface-3'}"
        >Runs</a>
        <a
          href="/leads"
          class="px-3 py-1.5 rounded-lg text-sm transition-colors {isActive('/leads') ? 'text-text-primary bg-white shadow-xs font-semibold border border-surface-4' : 'text-text-muted hover:text-text-primary hover:bg-surface-3'}"
        >All Leads</a>
      </div>

      <!-- Right: New Run CTA + hamburger -->
      <div class="flex items-center gap-2 flex-shrink-0">
        <!-- New Run — always visible, prominent -->
        <a href="/runs/new" class="btn-primary text-xs px-3 py-1.5 gap-1.5">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M6 1v10M1 6h10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
          <span class="hidden xs:inline">New Run</span>
          <span class="xs:hidden">Run</span>
        </a>

        <!-- Desktop logout -->
        <button
          on:click={logout}
          class="hidden sm:inline-flex px-3 py-1.5 rounded-lg text-xs text-text-muted hover:text-text-primary hover:bg-surface-3 transition-colors"
        >
          Sign out
        </button>

        <!-- Hamburger (mobile only) -->
        <button
          on:click={() => (menuOpen = !menuOpen)}
          class="sm:hidden flex items-center justify-center w-9 h-9 rounded-lg text-text-muted hover:bg-surface-3 transition-colors"
          aria-label="Toggle menu"
        >
          {#if menuOpen}
            <!-- X icon -->
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M4 4l10 10M14 4L4 14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          {:else}
            <!-- Hamburger icon -->
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M3 5h12M3 9h12M3 13h12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          {/if}
        </button>
      </div>
    </div>
  </div>

  <!-- Mobile dropdown menu -->
  {#if menuOpen}
    <div class="sm:hidden border-t border-[#e7dfd4] bg-[#fbf9f5] px-4 py-3 space-y-1">
      <a
        href="/"
        class="flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors {isActive('/') ? 'text-text-primary bg-white border border-surface-4 font-semibold' : 'text-text-muted hover:text-text-primary hover:bg-surface-3'}"
      >Runs</a>
      <a
        href="/leads"
        class="flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors {isActive('/leads') ? 'text-text-primary bg-white border border-surface-4 font-semibold' : 'text-text-muted hover:text-text-primary hover:bg-surface-3'}"
      >All Leads</a>
      <div class="pt-1 border-t border-[#e7dfd4] mt-1">
        <button
          on:click={logout}
          class="flex items-center w-full px-3 py-2.5 rounded-lg text-sm text-text-muted hover:text-text-primary hover:bg-surface-3 transition-colors"
        >Sign out</button>
      </div>
    </div>
  {/if}
</nav>
