<!-- /pitch/+page.svelte — FlowJoy Verve pitch page for video creators -->
<svelte:head>
  <title>How FlowJoy Finds Your Next Client — Automatically</title>
  <meta name="description" content="A live case study: how FlowJoy's autonomous lead pipeline finds and qualifies B2B startup founders — while you sleep." />
</svelte:head>

<div class="min-h-screen bg-[#fbf9f5] text-[#1c1917]">

  <!-- ── HERO ─────────────────────────────────────────────────────────────── -->
  <section class="max-w-3xl mx-auto px-6 pt-20 pb-16 text-center">
    <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-orange-50 border border-orange-200 text-[#c2410c] text-xs font-bold font-mono mb-6 uppercase tracking-wider">
      Live Case Study · FlowJoy
    </div>
    <h1 class="text-4xl sm:text-5xl font-black tracking-tight leading-tight mb-5">
      Your next client is already out there.<br/>
      <span class="text-[#c2410c]">This finds them for you.</span>
    </h1>
    <p class="text-lg text-[#57534e] leading-relaxed max-w-2xl mx-auto mb-8">
      Verve is a private lead pipeline that automatically sources, qualifies, and enriches B2B startup founders — the exact people who need GTM help right now. Tap a button from your phone. Get a ranked list of warm prospects by the time your coffee's ready.
    </p>
    <a
      href="https://flowjoy.online"
      target="_blank"
      rel="noopener"
      class="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[#c2410c] text-white font-bold text-sm hover:bg-[#b03a0b] transition-colors shadow-md"
    >
      Work with FlowJoy →
    </a>
  </section>

  <!-- ── WHO IS THIS FOR ───────────────────────────────────────────────────── -->
  <section class="max-w-3xl mx-auto px-6 pb-16">
    <div class="bg-white rounded-2xl border border-[#e7dfd4] p-8 shadow-sm">
      <p class="text-xs font-bold text-[#c2410c] uppercase tracking-widest mb-3 font-mono">Who we target</p>
      <h2 class="text-2xl font-black mb-4">B2B startup founders at the exact right moment.</h2>
      <p class="text-[#78716c] leading-relaxed mb-6">
        The sweet spot is a founder who just raised a Seed or Series A, is building a real B2B product, and hasn't yet hired a sales person. They need revenue systems — and they need them now. That's the FlowJoy customer.
      </p>
      <div class="grid sm:grid-cols-3 gap-4">
        {#each [
          { icon: '🚀', label: 'YC-backed startups', desc: '2023–2027 cohorts, actively hiring engineers' },
          { icon: '💰', label: 'Seed to Series A', desc: 'Past the idea stage, pre-sales motion' },
          { icon: '🎯', label: 'No GTM hire yet', desc: 'Founder-led sales, ready for a system' },
        ] as card}
          <div class="bg-[#fbf9f5] rounded-xl border border-[#e7dfd4] p-4">
            <div class="text-2xl mb-2">{card.icon}</div>
            <p class="font-bold text-sm mb-1">{card.label}</p>
            <p class="text-xs text-[#78716c]">{card.desc}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <!-- ── HOW IT WORKS ──────────────────────────────────────────────────────── -->
  <section class="max-w-3xl mx-auto px-6 pb-16">
    <p class="text-xs font-bold text-[#c2410c] uppercase tracking-widest mb-3 font-mono">How it works</p>
    <h2 class="text-2xl font-black mb-8">Four steps. Fully automated.</h2>
    <div class="space-y-4">
      {#each [
        {
          step: '01',
          color: 'bg-orange-50 border-orange-200 text-[#c2410c]',
          title: 'Scrape',
          detail: 'Pulls every active YC startup from the public directory. Filters by batch year, team size, and hiring signals — no manual searching.',
          cost: 'Free',
        },
        {
          step: '02',
          color: 'bg-purple-50 border-purple-200 text-[#7e22ce]',
          title: 'Score with JEV',
          detail: 'JEV is a fast AI judge trained to think like a great sales rep. It reads each company\'s profile and decides: is this a FlowJoy prospect? It scores for B2B fit, funding stage, and whether they have a GTM hire already. Competitors get penalized. High-signal startups get flagged.',
          cost: '~$0.04',
        },
        {
          step: '03',
          color: 'bg-emerald-50 border-emerald-200 text-[#059669]',
          title: 'Find verified emails',
          detail: 'For every qualified lead, we automatically find and verify the founder\'s direct email address. No guessing, no bounces. Only confirmed contacts.',
          cost: '~$0.005/lead',
        },
        {
          step: '04',
          color: 'bg-sky-50 border-sky-200 text-[#0284c7]',
          title: 'Ranked list, ready to outreach',
          detail: 'The final output is a clean, ranked list of the best-fit prospects — company name, founder, LinkedIn, verified email, and score. Ready to drop into your outreach tool.',
          cost: 'Instant',
        },
      ] as item}
        <div class="flex gap-5 bg-white rounded-2xl border border-[#e7dfd4] p-6 shadow-sm">
          <div class="flex-shrink-0">
            <span class="inline-flex items-center justify-center w-9 h-9 rounded-xl {item.color} border text-xs font-black">
              {item.step}
            </span>
          </div>
          <div class="flex-1">
            <div class="flex items-center justify-between mb-1.5">
              <p class="font-bold">{item.title}</p>
              <span class="text-xs font-mono font-bold text-[#78716c]">{item.cost}</span>
            </div>
            <p class="text-sm text-[#78716c] leading-relaxed">{item.detail}</p>
          </div>
        </div>
      {/each}
    </div>
  </section>

  <!-- ── ECONOMICS ─────────────────────────────────────────────────────────── -->
  <section class="max-w-3xl mx-auto px-6 pb-16">
    <div class="bg-[#1c1917] rounded-2xl p-8 text-white">
      <p class="text-xs font-bold text-[#f97316] uppercase tracking-widest mb-3 font-mono">The economics</p>
      <h2 class="text-2xl font-black mb-2">20 qualified, verified leads for about 90 cents.</h2>
      <p class="text-[#a8a29e] mb-8 leading-relaxed">
        A single closed deal from FlowJoy is worth thousands. The entire cost of running this pipeline to find that deal is less than a coffee.
      </p>
      <div class="grid sm:grid-cols-3 gap-4 mb-8">
        {#each [
          { label: 'Scraping', value: '$0.00', sub: 'YC public directory' },
          { label: 'AI Scoring', value: '~$0.04', sub: 'per full run (20 leads)' },
          { label: 'Email Finder', value: '~$0.005', sub: 'per verified contact' },
        ] as item}
          <div class="bg-white/10 rounded-xl p-4">
            <p class="text-xs text-[#a8a29e] mb-1">{item.label}</p>
            <p class="text-2xl font-black text-white">{item.value}</p>
            <p class="text-[10px] text-[#78716c] mt-0.5">{item.sub}</p>
          </div>
        {/each}
      </div>
      <div class="bg-[#c2410c]/20 border border-[#c2410c]/40 rounded-xl px-5 py-4 flex items-center justify-between">
        <p class="font-bold">Total per run (20 leads, verified emails)</p>
        <p class="text-2xl font-black text-[#f97316]">~$0.15</p>
      </div>
    </div>
  </section>

  <!-- ── MOBILE / ANYWHERE ─────────────────────────────────────────────────── -->
  <section class="max-w-3xl mx-auto px-6 pb-16">
    <div class="bg-white rounded-2xl border border-[#e7dfd4] p-8 shadow-sm">
      <p class="text-xs font-bold text-[#c2410c] uppercase tracking-widest mb-3 font-mono">Run it from anywhere</p>
      <h2 class="text-2xl font-black mb-4">Not glued to your desk? That's the point.</h2>
      <p class="text-[#78716c] leading-relaxed mb-6">
        Verve is a fully mobile-ready web app. Open it from your phone, pick your filters, tap Start. The pipeline runs in the cloud for 3–5 minutes while you go about your day. Come back to a ready list of prospects — no laptop required.
      </p>
      <div class="grid sm:grid-cols-2 gap-4">
        {#each [
          { icon: '📱', title: 'Works on any device', desc: 'Responsive UI designed for phone-first use. No installs, no setup.' },
          { icon: '☁️', title: 'Runs in the cloud', desc: 'You close the tab. The pipeline keeps running. Results wait for you.' },
          { icon: '🎛️', title: 'You control the filters', desc: 'Choose which YC batches to target, how many leads, and how much to spend on email finding.' },
          { icon: '⚡', title: '3–5 minutes end to end', desc: 'Scrape → score → email → done. Faster than a manual LinkedIn search for one lead.' },
        ] as f}
          <div class="flex gap-3">
            <span class="text-2xl">{f.icon}</span>
            <div>
              <p class="font-bold text-sm mb-0.5">{f.title}</p>
              <p class="text-xs text-[#78716c]">{f.desc}</p>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <!-- ── WHAT'S NEXT ────────────────────────────────────────────────────────── -->
  <section class="max-w-3xl mx-auto px-6 pb-16">
    <p class="text-xs font-bold text-[#c2410c] uppercase tracking-widest mb-3 font-mono">What's next</p>
    <h2 class="text-2xl font-black mb-4">This is just version one.</h2>
    <p class="text-[#78716c] leading-relaxed mb-6">
      The foundation is built. Everything below is a straightforward extension — and all of it is on the roadmap.
    </p>
    <div class="space-y-3">
      {#each [
        {
          soon: true,
          title: 'Scheduled runs',
          desc: 'Set Verve to run every Monday morning. Fresh leads delivered automatically, every week, without touching the app.',
        },
        {
          soon: true,
          title: 'Slack & email notifications',
          desc: 'Get pinged the moment a run completes — with a summary of top leads, spend, and a direct link to the full list.',
        },
        {
          soon: false,
          title: 'CRM sync',
          desc: 'Push qualified leads directly into HubSpot, Notion, or Airtable. One-click outreach sequencing.',
        },
        {
          soon: false,
          title: 'Multi-source scraping',
          desc: 'Expand beyond YC to AngelList, ProductHunt, LinkedIn company search, and accelerator directories.',
        },
      ] as item}
        <div class="flex gap-4 bg-white rounded-xl border border-[#e7dfd4] px-5 py-4">
          <span class="flex-shrink-0 mt-0.5 text-xs font-bold font-mono px-2 py-0.5 rounded-full {item.soon ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-[#fbf9f5] text-[#a8a29e] border border-[#e7dfd4]'}">
            {item.soon ? 'Soon' : 'Roadmap'}
          </span>
          <div>
            <p class="font-bold text-sm mb-0.5">{item.title}</p>
            <p class="text-xs text-[#78716c]">{item.desc}</p>
          </div>
        </div>
      {/each}
    </div>
  </section>

  <!-- ── WHAT THIS PROVES ───────────────────────────────────────────────────── -->
  <section class="max-w-3xl mx-auto px-6 pb-16">
    <div class="bg-orange-50 border border-orange-200 rounded-2xl p-8">
      <p class="text-xs font-bold text-[#c2410c] uppercase tracking-widest mb-3 font-mono">The bigger point</p>
      <h2 class="text-2xl font-black mb-4">This is what FlowJoy builds for clients.</h2>
      <p class="text-[#57534e] leading-relaxed mb-4">
        Verve isn't a product we sell. It's the system we built for ourselves — and it's the same type of system we build for our clients. Automated, opinionated, and focused on one thing: putting the right message in front of the right person at the right moment.
      </p>
      <p class="text-[#57534e] leading-relaxed">
        If you're a B2B founder who wants a revenue system like this — one that runs in the background, costs pennies, and consistently surfaces warm prospects — that's exactly what <strong>FlowJoy</strong> does.
      </p>
    </div>
  </section>

  <!-- ── CTA ───────────────────────────────────────────────────────────────── -->
  <section class="max-w-3xl mx-auto px-6 pb-24 text-center">
    <h2 class="text-3xl font-black mb-3">Ready to build your own pipeline?</h2>
    <p class="text-[#78716c] mb-8">Let's talk about what a system like this looks like for your business.</p>
    <a
      href="https://flowjoy.online"
      target="_blank"
      rel="noopener"
      class="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-[#c2410c] text-white font-bold text-base hover:bg-[#b03a0b] transition-colors shadow-lg"
    >
      flowjoy.online →
    </a>
  </section>

  <!-- Footer -->
  <footer class="border-t border-[#e7dfd4] py-6 text-center text-xs text-[#a8a29e]">
    Built by <a href="https://flowjoy.online" class="text-[#c2410c] font-semibold no-underline hover:underline" target="_blank" rel="noopener">FlowJoy</a> · GTM Engineering Studio
  </footer>
</div>

<script lang="ts">
  // Static page — no data fetching
</script>

