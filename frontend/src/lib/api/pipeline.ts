/**
 * Pipeline API Module
 * ====================
 * All backend calls for runs and lead data.
 */

import { api } from './base';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface RunSummary {
  run_id:      string;
  started_at:  string;
  finished_at: string;
  status:      string;
  funnel:      { scraped?: number; enriched?: number; qualified?: number };
  spend:       { total_usd?: number };
  lead_count:  number;
}

export interface Founder {
  name:         string;
  title?:       string;
  linkedin_url?: string;
  twitter_url?: string;
}

export interface EmailResult {
  email?:    string;
  verified?: boolean;
  cost_usd?: number;
}

export interface Lead {
  id:                 string;
  company_name:       string;
  website?:           string;
  one_liner?:         string;
  batch?:             string;
  industry?:          string;
  yc_url?:            string;
  linkedin_url?:      string;
  founder_name?:      string;
  founder_title?:     string;
  founder_linkedin?:  string;
  founders:           Founder[];
  is_competitor:      boolean;
  is_vertical_product:boolean;
  signals:            string[];
  tier1_score:        number;
  jev_probs?:         Record<string, Record<string, number>>;
  jev_judge?:         string;
  email_result?:      EmailResult;
}

export interface Run extends RunSummary {
  leads: Lead[];
}

export interface RunStatus {
  status:  'idle' | 'running' | 'done' | 'error';
  run_id?: string;
  error?:  string;
}

// ── API ───────────────────────────────────────────────────────────────────────

export const pipelineApi = {
  /** List all completed runs (summary only, no leads). */
  listRuns(): Promise<RunSummary[]> {
    return api.get<RunSummary[]>('/api/runs');
  },

  /** Load a full run including all leads. */
  getRun(runId: string): Promise<Run> {
    return api.get<Run>(`/api/runs/${runId}`);
  },

  /** Trigger a new pipeline run in the background. */
  startRun(): Promise<{ status: string }> {
    return api.post<{ status: string }>('/api/run');
  },

  /** Poll the current active run status. */
  getStatus(): Promise<RunStatus> {
    return api.get<RunStatus>('/api/status');
  },
};
