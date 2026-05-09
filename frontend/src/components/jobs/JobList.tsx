'use client';

import React from 'react';
import { RotateCcw } from 'lucide-react';
import { cn, formatRelativeTime } from '@/lib/utils';
import { JobStatusBadge } from './JobStatusBadge';
import { Button } from '@/components/ui/Button';

// ─── Props ───
interface JobListProps {
  jobs: Array<{
    id: string;
    source_id: string;
    source_name?: string;
    status: string;
    started_at?: string;
    completed_at?: string;
    pages_scraped: number;
    leads_found: number;
    leads_new: number;
    error_message?: string;
    created_at: string;
  }>;
  onRetry?: (id: string) => void;
  retryingId?: string;
  loading?: boolean;
}

// ─── Component ───
export function JobList({ jobs, onRetry, retryingId, loading }: JobListProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 p-4 bg-white rounded-xl border border-slate-200">
            <div className="skeleton h-5 w-5 rounded-full shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="skeleton h-4 w-1/3 rounded" />
              <div className="skeleton h-3 w-2/3 rounded" />
            </div>
            <div className="skeleton h-8 w-20 rounded-lg" />
          </div>
        ))}
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-slate-500">No scraping jobs found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {jobs.map((job) => (
        <div
          key={job.id}
          className={cn(
            'flex items-center gap-4 p-4 bg-white rounded-xl border border-slate-200',
            'hover:border-slate-300 hover:shadow-sm transition-all duration-150'
          )}
        >
          {/* Status */}
          <JobStatusBadge status={job.status} />

          {/* Info */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-900 truncate">
              {job.source_name || `Source ${job.source_id.slice(0, 8)}`}
            </p>
            <div className="flex items-center gap-3 mt-0.5">
              {job.started_at && (
                <span className="text-xs text-slate-500">
                  Started {formatRelativeTime(job.started_at)}
                </span>
              )}
              <span className="text-xs text-slate-400">
                {job.pages_scraped} pages
              </span>
              <span className="text-xs text-slate-400">
                {job.leads_found} leads
              </span>
              {job.leads_new > 0 && (
                <span className="text-xs text-emerald-600 font-medium">
                  +{job.leads_new} new
                </span>
              )}
            </div>
            {job.error_message && (
              <p className="text-xs text-red-600 mt-1 truncate max-w-[400px]">
                {job.error_message}
              </p>
            )}
          </div>

          {/* Actions */}
          {(job.status === 'failed' || job.status === 'cancelled') && (
            <Button
              variant="outline"
              size="sm"
              leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
              loading={retryingId === job.id}
              onClick={() => onRetry?.(job.id)}
            >
              Retry
            </Button>
          )}

          {job.status === 'completed' && (
            <span className="text-xs text-slate-400">
              {job.completed_at ? formatRelativeTime(job.completed_at) : ''}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

export default JobList;
