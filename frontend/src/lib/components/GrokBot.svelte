<!-- GrokBot.svelte — Exact Grok Bot character from user provided banner -->
<script>
  export let size = 32;
  export let theme = 'white'; // 'white' | 'dark' | 'orange' | 'purple'

  $: circleFill =
    theme === 'dark'   ? '#1c1917' :
    theme === 'purple' ? '#7e22ce' :
    theme === 'orange' ? '#ea580c' :
                         '#ffffff';

  $: eyeFill =
    theme === 'dark'   ? '#ffffff' :
    theme === 'purple' ? '#ffffff' :
    theme === 'orange' ? '#ffffff' :
                         '#1c1917';

  $: borderColor =
    theme === 'white' ? '#d8d0c5' : 'transparent';
</script>

<div class="inline-flex items-center justify-center flex-shrink-0" style="width: {size}px; height: {size}px;">
  <svg
    width={size}
    height={size}
    viewBox="0 0 100 100"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- Circular Head -->
    <circle
      cx="50"
      cy="50"
      r="48"
      fill={circleFill}
      stroke={borderColor}
      stroke-width={theme === 'white' ? '2.5' : '0'}
    />

    <!-- Two tilted pill eyes matching the Meet Grok Bot image -->
    <!-- Left pill: slanted / -->
    <rect
      x="-6.5"
      y="-16"
      width="13"
      height="32"
      rx="6.5"
      fill={eyeFill}
      transform="translate(38, 62) rotate(24)"
    />

    <!-- Right pill: slanted / parallel, slightly lower right -->
    <rect
      x="-6.5"
      y="-16"
      width="13"
      height="32"
      rx="6.5"
      fill={eyeFill}
      transform="translate(56, 66) rotate(24)"
    />
  </svg>
</div>
