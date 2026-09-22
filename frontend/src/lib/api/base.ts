/**
 * Base API Client
 * ===============
 * Reusable typed HTTP client — same pattern as chloe-saas.
 */

import { config } from '../config';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  params?: Record<string, string | number | boolean>;
}

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.status = status;
    this.data   = data;
  }
}

// ── Client ────────────────────────────────────────────────────────────────────

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private buildUrl(
    endpoint: string,
    params?: Record<string, string | number | boolean>
  ): string {
    const url = `${this.baseUrl}${endpoint}`;
    if (!params || !Object.keys(params).length) return url;
    const sp = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) sp.append(k, String(v));
    return `${url}?${sp}`;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit & { params?: Record<string, string | number | boolean> } = {}
  ): Promise<T> {
    const { params, ...fetchOptions } = options;
    const url = this.buildUrl(endpoint, params);

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...fetchOptions.headers,
    };

    console.log(`[api] ${fetchOptions.method ?? 'GET'} ${url}`);

    try {
      const res = await fetch(url, { ...fetchOptions, headers });

      let data: unknown;
      try { data = await res.json(); } catch { /* empty body */ }

      if (!res.ok) {
        const msg =
          (data as any)?.detail ||
          (data as any)?.error  ||
          `HTTP ${res.status}`;
        throw new ApiError(msg, res.status, data);
      }

      return data as T;
    } catch (err) {
      if (err instanceof ApiError) throw err;
      // Network-level failure
      throw new ApiError(
        'Unable to reach the server. Is the backend running?',
        0,
        err
      );
    }
  }

  get<T>(endpoint: string, options: ApiRequestOptions = {}): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  post<T>(endpoint: string, body?: unknown, options: ApiRequestOptions = {}): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }
}

// ── Singleton ─────────────────────────────────────────────────────────────────

export const api = new ApiClient(config.apiUrl);
