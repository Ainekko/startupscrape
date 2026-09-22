/**
 * Application Configuration
 * ==========================
 * Central config for API endpoints.
 *
 * Environment Variables (set in .env):
 *   VITE_API_URL  — full base URL of the backend (no trailing slash)
 *
 * Dev default: http://127.0.0.1:8000
 * Prod:        set VITE_API_URL in Vercel environment settings
 */

export const config = {
  /** Base URL of the FastAPI backend */
  apiUrl: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
} as const;
