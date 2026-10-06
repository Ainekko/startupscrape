<!-- /login/+page.svelte — Clean, secure single-user sign in -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api';
  import GrokBot from '$lib/components/GrokBot.svelte';

  let email = 'xander';
  let password = '';
  let loading = false;
  let error: string | null = null;

  onMount(() => {
    if (api.auth.isLoggedIn()) {
      goto('/');
    }
  });

  async function handleLogin() {
    if (!email || !password) {
      error = 'Please enter both username and password.';
      return;
    }

    loading = true;
    error = null;

    try {
      await api.auth.login({ email, password });
      goto('/');
    } catch (err: any) {
      error = err.message || 'Authentication failed. Please verify credentials.';
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>Sign In — Verve</title>
</svelte:head>

<div class="max-w-sm mx-auto mt-20 animate-fade-in">
  <div class="card p-8 shadow-sm border border-[#e7dfd4]">
    <div class="flex items-center gap-3 mb-2">
      <GrokBot size={34} theme="dark" />
      <div>
        <h1 class="text-xl font-bold text-text-primary tracking-tight">Verve Sign In</h1>
        <p class="text-xs text-text-secondary">Authorized system access</p>
      </div>
    </div>

    {#if error}
      <div class="mt-4 px-3 py-2.5 rounded-lg bg-red-50 border border-red-200 text-xs text-red-800">
        {error}
      </div>
    {/if}

    <form on:submit|preventDefault={handleLogin} class="mt-6 space-y-4">
      <div>
        <label for="username" class="block text-xs font-semibold text-text-primary mb-1">
          Username
        </label>
        <input
          id="username"
          type="text"
          bind:value={email}
          autocomplete="username"
          required
          placeholder="xander"
          class="w-full px-3 py-2 rounded-lg border border-[#ded6cc] bg-[#fbf9f5] text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-[#c2410c] focus:border-[#c2410c]"
        />
      </div>

      <div>
        <label for="password" class="block text-xs font-semibold text-text-primary mb-1">
          Password
        </label>
        <input
          id="password"
          type="password"
          bind:value={password}
          autocomplete="current-password"
          required
          placeholder="••••••••••••"
          class="w-full px-3 py-2 rounded-lg border border-[#ded6cc] bg-[#fbf9f5] text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-[#c2410c] focus:border-[#c2410c]"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        class="btn-primary w-full justify-center py-2 text-sm mt-2 {loading ? 'opacity-60 cursor-not-allowed' : ''}"
      >
        {#if loading}
          <svg class="w-4 h-4 animate-spin mr-2" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.25"/>
            <path d="M22 12a10 10 0 01-10 10" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
          </svg>
          Signing in…
        {:else}
          Sign In →
        {/if}
      </button>
    </form>
  </div>
</div>

