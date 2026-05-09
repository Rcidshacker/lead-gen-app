// ─── Lead Types ───

export type LeadStatus = 'new' | 'contacted' | 'interested' | 'rejected' | 'hired';

export type Platform = 'linkedin' | 'indeed' | 'upwork' | 'naukri' | 'glassdoor' | 'ziprecruiter' | 'monster' | 'angelist' | 'wellfound';

export interface Lead {
  id: string;
  source_id: string;
  platform: Platform | string;
  title: string;
  company: string;
  location: string;
  salary: string;
  description: string;
  requirements: string;
  contact_info: Record<string, unknown>;
  url: string;
  raw_data: Record<string, unknown>;
  score: number;
  status: LeadStatus;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface LeadFilters {
  min_score?: number;
  max_score?: number;
  status?: LeadStatus | string;
  platform?: Platform | string;
  search?: string;
  source_id?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface LeadUpdatePayload {
  status?: LeadStatus | string;
  notes?: string;
}

export interface LeadCreatePayload {
  source_id: string;
  platform: string;
  title: string;
  company: string;
  location: string;
  salary?: string;
  description?: string;
  requirements?: string;
  contact_info?: Record<string, unknown>;
  url?: string;
  raw_data?: Record<string, unknown>;
  score?: number;
}
