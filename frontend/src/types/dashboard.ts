// ─── Dashboard Types ───

export interface DashboardStats {
  total_leads: number;
  new_leads: number;
  contacted_leads: number;
  interested_leads: number;
  hired_leads: number;
  active_sources: number;
  total_sources: number;
  avg_score: number;
  leads_by_platform: PlatformBreakdown[];
  leads_by_status: StatusBreakdown[];
  leads_over_time: TimeSeriesPoint[];
  top_sources: TopSource[];
}

export interface PlatformBreakdown {
  platform: string;
  count: number;
  percentage: number;
}

export interface StatusBreakdown {
  status: string;
  count: number;
  percentage: number;
}

export interface TimeSeriesPoint {
  date: string;
  count: number;
}

export interface TopSource {
  source_id: string;
  source_name: string;
  platform: string;
  leads_count: number;
  avg_score: number;
}

export interface DashboardFilters {
  date_from?: string;
  date_to?: string;
  platform?: string;
}
