/**
 * types.ts — Frontend Type Definitions
 * ======================================
 * Aligned with backend Pydantic schemas (backend/app/models.py).
 */

// ── Enums ────────────────────────────────────────────────────────────────────

export type UserRole = 'admin' | 'user' | 'viewer';

export type OutreachStatus =
  | 'new'
  | 'contacted'
  | 'replied'
  | 'meeting'
  | 'converted'
  | 'disqualified';

export type RunStatusValue = 'idle' | 'running' | 'done' | 'error';

// ── Auth ─────────────────────────────────────────────────────────────────────

export interface UserRegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface UserLoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: number;
  email: string;
  role: UserRole;
}

export interface UserResponse {
  id: number;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

// ── Pipeline Runs ────────────────────────────────────────────────────────────

export interface RunSummary {
  run_id: string;
  started_at: string;
  finished_at: string | null;
  status: string; // 'running' | 'complete' | 'error'
  funnel: {
    scraped?: number;
    enriched?: number;
    qualified?: number;
  };
  spend: {
    total_usd?: number;
  };
  lead_count: number;
}

export interface PipelineTriggerRequest {
  max_leads?: number;
  max_treg_cost?: number;
}

export interface RunStatus {
  status: RunStatusValue;
  run_id?: string;
  error?: string;
}

// ── Leads ────────────────────────────────────────────────────────────────────

export interface Founder {
  name: string;
  title?: string;
  linkedin_url?: string;
  twitter_url?: string;
}

export interface EmailResult {
  email?: string;
  verified?: boolean;
  cost_usd?: number;
}

export interface Lead {
  id: string;
  run_id?: string;
  company_name: string;
  website?: string;
  one_liner?: string;
  batch?: string;
  industry?: string;
  team_size?: string;
  tags?: string;
  yc_url?: string;
  waas_url?: string;
  linkedin_url?: string;

  // Founder / Contact
  founder_name?: string;
  founder_title?: string;
  founder_linkedin?: string;
  founders: Founder[];

  // Email & Verification
  email?: string;
  email_status?: string;
  email_result?: EmailResult;

  // Scoring & GTM Intel
  tier1_score: number;
  final_score: number;
  is_competitor: boolean;
  is_vertical_product: boolean;
  signals: string[];
  jev_probs?: Record<string, Record<string, number>>;
  jev_judge?: string;

  // Outreach tracking
  outreach_status: OutreachStatus;
  notes?: string;

  created_at?: string;
  updated_at?: string;
}

export interface Run extends RunSummary {
  leads: Lead[];
}

// ── Lead Filters ─────────────────────────────────────────────────────────────

export interface LeadFilterParams {
  query?: string;
  batch?: string;
  industry?: string;
  min_score?: number;
  max_score?: number;
  has_email?: boolean;
  outreach_status?: string;
  run_id?: string;
  sort_by?: string;
  limit?: number;
  offset?: number;
}

export interface LeadStatusUpdateRequest {
  outreach_status: string;
  notes?: string;
}

export interface LeadOutcomeCreateRequest {
  channel?: string;
  status: string;
  notes?: string;
}

// ── Analytics ────────────────────────────────────────────────────────────────

export interface AnalyticsOverview {
  total_leads: number;
  total_runs: number;
  avg_score: number;
  leads_with_email: number;
  status_breakdown: Record<string, number>;
  top_batches: Array<Record<string, unknown>>;
}

// ── Paginated Response ───────────────────────────────────────────────────────

export interface PaginatedLeads {
  items: Lead[];
  total: number;
  limit: number;
  offset: number;
}
