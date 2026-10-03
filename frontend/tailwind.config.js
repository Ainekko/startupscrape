/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        // Warm cream palette matching the case study illustration
        surface: {
          0: '#fbf9f5',     // page bg
          1: '#f7f4ef',     // card bg muted
          2: '#ffffff',     // card bg active
          3: '#ede8e1',     // subtle bg / tab bar
          4: '#e5ddd0',     // borders / dividers
        },
        accent: {
          DEFAULT: '#c2410c', // orange-700: primary brand
          dim: '#ea580c',     // orange-600
          muted: '#fed7aa',   // orange-200
        },
        // Pipeline step colors
        pipeline: {
          source: '#f97316',  // orange: step 1 sourcing
          score: '#9333ea',   // purple: step 2 JEV
          enrich: '#2563eb',  // blue: step 3 Treg.to
        },
        lead: {
          high: '#059669',    // emerald-600
          mid: '#d97706',     // amber-600
          low: '#dc2626',     // red-600
        },
        border: '#e5ddd0',
        'text-primary': '#1c1917',    // stone-900
        'text-secondary': '#57534e',  // stone-600
        'text-muted': '#78716c',      // stone-500
        'text-faint': '#a8a29e',      // stone-400
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        'card-hover': '0 4px 16px rgba(0,0,0,0.08)',
        'card-active': '0 4px 12px rgba(0,0,0,0.10)',
        'xs': '0 1px 2px rgba(0,0,0,0.05)',
        '2xs': '0 0 1px rgba(0,0,0,0.05)',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Mono', 'monospace'],
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
        '3xl': '1.75rem',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.35s ease-out',
        'fade-slide-in': 'fadeSlideIn 0.45s cubic-bezier(0.16, 1, 0.3, 1) both',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: 0 },
          '100%': { opacity: 1 },
        },
        slideUp: {
          '0%': { opacity: 0, transform: 'translateY(8px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
        fadeSlideIn: {
          '0%': { opacity: 0, transform: 'translateY(8px) scale(0.98)' },
          '100%': { opacity: 1, transform: 'translateY(0) scale(1)' },
        },
      },
    },
  },
  plugins: [],
}
