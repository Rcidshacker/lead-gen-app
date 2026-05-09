'use client';

import React from 'react';
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { cn, formatRelativeTime, truncate } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardBody } from '@/components/ui/Card';
import type { ScrapingJob } from '@/types/job';

// ─── Props ───
interface ScrapeActivityProps {
  jobs: ScrapingJob[];
  loading?: boolean;
}

// ─── Status Icons ───
const statusIcons: Record<string, React.ElementType> = {
  completed: CheckCircle2,
  failed: XCircle,
  running: Loader2,
  pending: Clock,
  cancelled: AlertCircle,
};

const statusColors: Record<string, string> = {
  completed: 'text-emerald-500',
  failed: 'text-red-500',
  running: 'text-blue-500',
  pending: 'text-slate-400',
  cancelled: 'text-amber-500',
};

// ─── Component ───
export function ScrapeActivity({ jobs, loading }: ScrapeActivityProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Scraping Activity</CardTitle>
      </CardHeader>
      <CardBody>
        {loading ? (
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="skeleton h-5 w-5 rounded-full shrink-0 mt-0.5" />
                <div className="flex-1 space-y-1.5">
                  <div className="skeleton h-4 w-3/4 rounded" />
                  <div className="skeleton h-3 w-1/2 rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-8">
            <Clock className="h-8 w-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500">No scraping activity yet.</p>
            <p className="text-xs text-slate-400 mt-1">
              Activity will appear once sources are scraped.
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {jobs.slice(0, 10).map((job) => {
              const Icon = statusIcons[job.status] || Clock;
              const color = statusColors[job.status] || 'text-slate-400';

              return (
                <div
                  key={job.id}
                  className="flex items-start gap-3 py-2.5 px-2 -mx-2 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  <Icon
                    className={cn(
                      'h-5 w-5 shrink-0 mt-0.5',
                      color,
                      job.status === 'running' && 'animate-spin'
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium text-slate-900 truncate">
                        {job.source_name || `Source ${truncate(job.source_id, 8)}`}
                      </p>
                      <span className="text-xs text-slate-400 shrink-0">
                        {formatRelativeTime(job.created_at)}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="text-xs text-slate-500 capitalize">
                        {job.status}
                      </span>
                      {job.leads_found > 0 && (
                        <span className="text-xs text-emerald-600 font-medium">
                          {job.leads_found} leads found
                        </span>
                      )}
                      {job.error_message && (
                        <span className="text-xs text-red-500 truncate max-w-[200px]">
                          {truncate(job.error_message, 40)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

export default ScrapeActivity;
