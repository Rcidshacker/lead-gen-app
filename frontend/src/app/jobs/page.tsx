'use client';

import React, { useState } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { useJobs, useRetryJob } from '@/hooks/useJobs';
import { JobList } from '@/components/jobs/JobList';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

// ─── Status Tabs ───
const statusTabs = [
  { value: '', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'running', label: 'Running' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
];

// ─── Jobs Page ───
export default function JobsPage() {
  const [page, setPage] = useState(1);
  const [activeTab, setActiveTab] = useState('');
  const [retryingId, setRetryingId] = useState<string | null>(null);

  const { data, isLoading } = useJobs(page, activeTab);
  const jobs = data?.items || [];

  const handleRetry = async (id: string) => {
    setRetryingId(id);
    try {
      const { apiClient } = await import('@/lib/api');
      await apiClient.post(`/jobs/${id}/retry`);
    } catch {
      // ignore
    } finally {
      setRetryingId(null);
    }
  };

  return (
    <AppShell title="Scraping Jobs">
      {/* Description */}
      <p className="text-sm text-slate-500 mb-6">
        Monitor and manage your scraping jobs. Track progress, view results, and retry failed jobs.
      </p>

      {/* Status Tabs */}
      <div className="flex items-center gap-1 mb-6 border-b border-slate-200 overflow-x-auto">
        {statusTabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => {
              setActiveTab(tab.value);
              setPage(1);
            }}
            className={cn(
              'px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors relative',
              activeTab === tab.value
                ? 'text-primary-600'
                : 'text-slate-500 hover:text-slate-700'
            )}
          >
            {tab.label}
            {activeTab === tab.value && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-600 rounded-t" />
            )}
          </button>
        ))}
      </div>

      {/* Job List */}
      <JobList
        jobs={jobs}
        onRetry={handleRetry}
        retryingId={retryingId || undefined}
        loading={isLoading}
      />

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-8">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <span className="text-sm text-slate-500 px-3">
            Page {page} of {data.total_pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= data.total_pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </AppShell>
  );
}
