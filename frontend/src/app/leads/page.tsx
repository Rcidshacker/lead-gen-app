'use client';

import React, { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { useLeads } from '@/hooks/useLeads';
import { LeadFiltersBar } from '@/components/leads/LeadFilters';
import { LeadTable } from '@/components/leads/LeadTable';
import { Button } from '@/components/ui/Button';
import type { LeadFilters } from '@/types/lead';

// ─── Leads Page ───
function LeadsContent() {
  const searchParams = useSearchParams();

  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<LeadFilters>({
    search: searchParams.get('search') || undefined,
    platform: searchParams.get('platform') || undefined,
    status: searchParams.get('status') || undefined,
    min_score: searchParams.get('min_score') ? Number(searchParams.get('min_score')) : undefined,
    sort_by: 'created_at',
    sort_order: 'desc',
  });
  const [sortKey, setSortKey] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const { data, isLoading } = useLeads({ ...filters, sort_by: sortKey, sort_order: sortOrder }, page);

  const leads = data?.items || [];

  const handleFilterChange = (newFilters: LeadFilters) => {
    setFilters(newFilters);
    setPage(1); // Reset to page 1 when filters change
  };

  const handleSort = (key: string, order: 'asc' | 'desc') => {
    setSortKey(key);
    setSortOrder(order);
  };

  return (
    <AppShell title="Leads">
      {/* Filters */}
      <div className="mb-6">
        <LeadFiltersBar filters={filters} onFilterChange={handleFilterChange} />
      </div>

      {/* Results count */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-slate-500">
          {isLoading ? (
            'Loading leads...'
          ) : data ? (
            <>
              Showing {leads.length} of {data.total} leads
            </>
          ) : (
            'No leads found'
          )}
        </p>
      </div>

      {/* Table */}
      <LeadTable
        leads={leads}
        loading={isLoading}
        sortKey={sortKey}
        sortOrder={sortOrder}
        onSort={handleSort}
      />

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>

          {/* Page numbers */}
          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(data.total_pages, 5) }, (_, i) => {
              // Show pages around current
              let pageNum: number;
              if (data.total_pages <= 5) {
                pageNum = i + 1;
              } else if (page <= 3) {
                pageNum = i + 1;
              } else if (page >= data.total_pages - 2) {
                pageNum = data.total_pages - 4 + i;
              } else {
                pageNum = page - 2 + i;
              }

              return (
                <Button
                  key={pageNum}
                  variant={page === pageNum ? 'primary' : 'ghost'}
                  size="sm"
                  onClick={() => setPage(pageNum)}
                  className="w-9"
                >
                  {pageNum}
                </Button>
              );
            })}
          </div>

          <span className="text-sm text-slate-500 px-2">
            of {data.total_pages}
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

export default function LeadsPage() {
  return (
    <React.Suspense fallback={<div className="flex h-screen items-center justify-center text-slate-500">Loading leads data...</div>}>
      <LeadsContent />
    </React.Suspense>
  );
}
