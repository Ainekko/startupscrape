/**
 * api.ts — Single source API client
 * ====================================
 * All backend calls go through here. Auth token management,
 * error handling, and typed endpoints in one place.
 *
 * Usage:
 *   import { api } from '$lib/api';
 *   const runs = await api.pipeline.listRuns();
 *   await api.auth.login({ email, password });
 */

import { config } from './config';
import type {
  TokenResponse,
  UserLoginRequest,
  UserRegisterRequest,
  UserResponse,
  RunSummary,
  Run,
  RunStatus,
  PipelineTriggerRequest,
  Lead,
  PaginatedLeads,
  LeadFilterParams,
  LeadStatusUpdateRequest,
  LeadOutcomeCreateRequest,
  AnalyticsOverview,
} from './types';

// ── Error class ──────────────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

// ── Token storage ────────────────────────────────────────────────────────────

const TOKEN_KEY = 'startupscrape_token';

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

function clearToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_KEY);
  }
}

// ── Base HTTP methods ────────────────────────────────────────────────────────

function buildUrl(
  endpoint: string,
  params?: Record<string, string | number | boolean | undefined>
): string {
  const url = `${config.apiUrl}${endpoint}`;
  if (!params) return url;
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) sp.append(k, String(v));
  }
  const qs = sp.toString();
  return qs ? `${url}?${qs}` : url;
}

async function request<T>(
  endpoint: string,
  options: RequestInit & { params?: Record<string, string | number | boolean | undefined> } = {}
): Promise<T> {
  const { params, ...fetchOptions } = options;
  const url = buildUrl(endpoint, params);

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(fetchOptions.headers as Record<string, string> || {}),
  };

  // Attach bearer token if present
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(url, { ...fetchOptions, headers });

    let data: unknown;
    try { data = await res.json(); } catch { /* empty body */ }

    if (!res.ok) {
      if (res.status === 401) {
        clearToken();
        throw new ApiError('not_authenticated', 401, data);
      }
      const msg =
        (data as any)?.detail ||
        (data as any)?.error ||
        `HTTP ${res.status}`;
      throw new ApiError(msg, res.status, data);
    }

    return data as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      'Unable to reach the server. Is the backend running?',
      0,
      err
    );
  }
}

function get<T>(endpoint: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  return request<T>(endpoint, { method: 'GET', params });
}

function post<T>(endpoint: string, body?: unknown, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  return request<T>(endpoint, {
    method: 'POST',
    body: body !== undefined ? JSON.stringify(body) : undefined,
    params,
  });
}

function patch<T>(endpoint: string, body?: unknown): Promise<T> {
  return request<T>(endpoint, {
    method: 'PATCH',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

// ── API namespaces ───────────────────────────────────────────────────────────

export const api = {
  // ── Auth ─────────────────────────────────────────────────────────────────
  auth: {
    async login(data: UserLoginRequest): Promise<TokenResponse> {
      const resp = await post<TokenResponse>('/api/auth/login', data);
      setToken(resp.access_token);
      return resp;
    },

    async register(data: UserRegisterRequest): Promise<UserResponse> {
      return post<UserResponse>('/api/auth/register', data);
    },

    async me(): Promise<UserResponse> {
      return get<UserResponse>('/api/auth/me');
    },

    logout(): void {
      clearToken();
    },

    isLoggedIn(): boolean {
      return !!getToken();
    },
  },

  // ── Pipeline ─────────────────────────────────────────────────────────────
  pipeline: {
    listRuns(): Promise<RunSummary[]> {
      return get<RunSummary[]>('/api/runs');
    },

    getRun(runId: string): Promise<Run> {
      return get<Run>(`/api/runs/${runId}`);
    },

    startRun(payload?: PipelineTriggerRequest): Promise<{ status: string }> {
      return post<{ status: string }>('/api/run', payload);
    },

    getStatus(): Promise<RunStatus> {
      return get<RunStatus>('/api/status');
    },
  },

  // ── Leads ────────────────────────────────────────────────────────────────
  leads: {
    list(params?: LeadFilterParams): Promise<PaginatedLeads> {
      return get<PaginatedLeads>('/api/leads', params as Record<string, string | number | boolean | undefined>);
    },

    getById(leadId: string): Promise<Lead> {
      return get<Lead>(`/api/leads/${leadId}`);
    },

    updateStatus(leadId: string, data: LeadStatusUpdateRequest): Promise<Lead> {
      return patch<Lead>(`/api/leads/${leadId}/status`, data);
    },

    recordOutcome(leadId: string, data: LeadOutcomeCreateRequest): Promise<Record<string, unknown>> {
      return post<Record<string, unknown>>(`/api/leads/${leadId}/outcome`, data);
    },

    async exportCsv(params?: Partial<LeadFilterParams>): Promise<string> {
      const url = buildUrl('/api/leads/export/csv', params as Record<string, string | number | boolean | undefined>);
      const headers: Record<string, string> = {};
      const token = getToken();
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(url, { headers });
      if (!res.ok) throw new ApiError('CSV export failed', res.status);
      return res.text();
    },
  },

  // ── Analytics ────────────────────────────────────────────────────────────
  analytics: {
    getOverview(): Promise<AnalyticsOverview> {
      return get<AnalyticsOverview>('/api/analytics/overview');
    },
  },

  // ── Health ───────────────────────────────────────────────────────────────
  health(): Promise<{ status: string; version: string; database_connected: boolean }> {
    return get('/health');
  },
};
