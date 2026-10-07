<!-- NotLoggedIn.svelte — Friendly auth gate shown when API returns 401 -->
<script lang="ts">
  import { ApiError } from '$lib/api';

  export let error: string | null = null;

  $: isAuthError = error === 'not_authenticated';
</script>

{#if isAuthError}
  <div class="card p-12 text-center">
    <div class="w-12 h-12 rounded-full bg-orange-50 border border-orange-200 flex items-center justify-center mx-auto mb-4">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" class="text-[#c2410c]">
        <rect x="3" y="11" width="18" height="11" rx="2" stroke="currentColor" stroke-width="1.8"/>
        <path d="M7 11V7a5 5 0 0110 0v4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>
    </div>
    <p class="text-text-primary font-semibold mb-1">You're not logged in</p>
    <p class="text-text-secondary text-sm mb-5">Sign in to access your dashboard.</p>
    <a href="/login" class="btn-primary mx-auto">Login to see your dashboard →</a>
  </div>
{:else if error}
  <div class="card p-8 text-center">
    <p class="text-red-700 text-sm mb-1">Something went wrong.</p>
    <p class="text-text-muted text-xs font-mono">{error}</p>
  </div>
{/if}

