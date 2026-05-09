// ─── Scraping Job Types ───

export type ScrapingJobStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type ScrapingJobType = 'full' | 'incremental';

export interface ScrapingJob {
  id: string;
  source_id: string;
  source_name?: string;
  status: ScrapingJobStatus;
  job_type: ScrapingJobType;
  started_at?: string;
  completed_at?: string;
  pages_scraped: number;
  leads_found: number;
  leads_new: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface ScrapingJobCreatePayload {
  source_id: string;
  job_type?: ScrapingJobType;
}

export interface ScrapingJobListResponse {
  items: ScrapingJob[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// ─── Status Helpers ───

export function getJobStatusColor(status: ScrapingJobStatus): {
  text: string;
  bg: string;
} {
  const colors: Record<ScrapingJobStatus, { text: string; bg: string }> = {
    pending: { text: 'text-slate-700', bg: 'bg-slate-100' },
    running: { text: 'text-blue-700', bg: 'bg-blue-50' },
    completed: { text: 'text-emerald-700', bg: 'bg-emerald-50' },
    failed: { text: 'text-red-700', bg: 'bg-red-50' },
    cancelled: { text: 'text-amber-700', bg: 'bg-amber-50' },
  };
  return colors[status];
}
