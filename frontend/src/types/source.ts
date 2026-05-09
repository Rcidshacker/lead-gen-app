// ─── Source Types ───

export type PlatformType = 'linkedin' | 'indeed' | 'upwork' | 'naukri' | 'glassdoor' | 'ziprecruiter' | 'monster' | 'angelist' | 'wellfound';

export type SourceStatus = 'active' | 'paused' | 'error';

export interface ScrapeConfig {
  keywords: string[];
  locations: string[];
  max_pages: number;
  filters?: Record<string, unknown>;
  exclude_keywords?: string[];
}

export interface ScrapeSchedule {
  frequency: 'daily' | 'weekly' | 'biweekly' | 'monthly';
  day_of_week?: number; // 0-6 for weekly/biweekly
  time_of_day?: string; // HH:MM format
  enabled: boolean;
}

export interface JobSource {
  id: string;
  user_id: string;
  name: string;
  platform: PlatformType;
  url: string;
  status: SourceStatus;
  config: ScrapeConfig;
  schedule: ScrapeSchedule;
  last_scraped_at?: string;
  last_error?: string;
  total_leads: number;
  created_at: string;
  updated_at: string;
}

export interface SourceCreatePayload {
  name: string;
  platform: PlatformType;
  url: string;
  config: ScrapeConfig;
  schedule?: ScrapeSchedule;
}

export interface SourceUpdatePayload {
  name?: string;
  status?: SourceStatus;
  url?: string;
  config?: Partial<ScrapeConfig>;
  schedule?: Partial<ScrapeSchedule>;
}

export interface SourceListResponse {
  items: JobSource[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}
