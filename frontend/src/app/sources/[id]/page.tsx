'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Play,
  ExternalLink,
  MapPin,
  Clock,
  FileText,
} from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { useSource, useTriggerScrape } from '@/hooks/useSources';
import { useLeads } from '@/hooks/useLeads';
import { Button } from '@/components/ui/Button';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { LeadTable } from '@/components/leads/LeadTable';
import { Card, CardHeader, CardTitle, CardBody } from '@/components/ui/Card';
import { cn, formatRelativeTime, formatDate, capitalize, truncate } from '@/lib/utils';

// ─── Source Detail Page ───
export default function SourceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [page, setPage] = useState(1);

  const { data: source, isLoading } = useSource(id);
  const { data: leadsData, isLoading: leadsLoading } = useLeads({ source_id: id }, page);
  const triggerScrape = useTriggerScrape(id);

  const handleScrape = () => {
    triggerScrape.mutate();
  };

  if (isLoading) {
    return (
      <AppShell title="Source Details">
        <div className="animate-pulse space-y-6">
          <div className="skeleton h-8 w-48 rounded" />
          <div className="skeleton h-40 w-full rounded-xl" />
          <div className="skeleton h-60 w-full rounded-xl" />
        </div>
      </AppShell>
    );
  }

  if (!source) {
    return (
      <AppShell title="Source Not Found">
        <div className="text-center py-16">
          <h2 className="text-lg font-semibold text-slate-900 mb-2">Source not found</h2>
          <p className="text-sm text-slate-500 mb-4">The source you&apos;re looking for doesn&apos;t exist.</p>
          <Button variant="outline" onClick={() => router.push('/sources')}>
            Back to Sources
          </Button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title={source.name}>
      {/* Back + Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <button
          onClick={() => router.push('/sources')}
          className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Sources
        </button>
        <Button
          leftIcon={<Play className="h-4 w-4" />}
          onClick={handleScrape}
          loading={triggerScrape.isPending}
        >
          Scrape Now
        </Button>
      </div>

      {/* Source Info Card */}
      <Card padding="lg" className="mb-6">
        <CardBody className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-xl font-bold text-slate-900">{source.name}</h2>
                <StatusBadge status={source.status} />
              </div>
              <div className="flex flex-wrap items-center gap-4 text-sm text-slate-500">
                <Badge variant="default" size="md">
                  {capitalize(source.platform)}
                </Badge>
                {source.url && (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-primary-600 hover:text-primary-700 transition-colors"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    {truncate(source.url, 60)}
                  </a>
                )}
              </div>
            </div>
          </div>

          {/* Stats Row */}
          <div className="flex items-center gap-6 pt-4 border-t border-slate-100">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-slate-400" />
              <span className="text-sm text-slate-600">
                <span className="font-semibold text-slate-900">{source.total_leads}</span> leads
              </span>
            </div>
            {source.last_scraped_at && (
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-slate-400" />
                <span className="text-sm text-slate-600">
                  Last scraped <span className="font-medium">{formatRelativeTime(source.last_scraped_at)}</span>
                </span>
              </div>
            )}
            <div className="text-sm text-slate-500">
              Created {formatDate(source.created_at)}
            </div>
          </div>

          {/* Error */}
          {source.last_error && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 mt-2">
              <p className="text-sm text-red-700 font-medium">Last Error</p>
              <p className="text-sm text-red-600 mt-1">{source.last_error}</p>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Configuration */}
      <Card padding="lg" className="mb-6">
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-slate-500 mb-1">Schedule</p>
              <p className="font-medium text-slate-900 capitalize">
                {source.schedule?.frequency || 'Manual'}
                {source.schedule?.enabled === false && ' (Disabled)'}
              </p>
            </div>
            <div>
              <p className="text-slate-500 mb-1">Max Pages</p>
              <p className="font-medium text-slate-900">{source.config?.max_pages || '—'}</p>
            </div>
            <div>
              <p className="text-slate-500 mb-1">Keywords</p>
              <p className="font-medium text-slate-900">
                {source.config?.keywords?.length
                  ? source.config.keywords.join(', ')
                  : '—'}
              </p>
            </div>
            <div>
              <p className="text-slate-500 mb-1">Locations</p>
              <p className="font-medium text-slate-900">
                {source.config?.locations?.length
                  ? source.config.locations.join(', ')
                  : '—'}
              </p>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Leads from this source */}
      <Card padding="none" className="mb-6">
        <CardHeader className="px-6 pt-6">
          <CardTitle>Leads from this Source</CardTitle>
        </CardHeader>
        <div className="px-6 pb-6">
          <LeadTable
            leads={leadsData?.items || []}
            loading={leadsLoading}
          />
        </div>

        {/* Pagination */}
        {leadsData && leadsData.total_pages > 1 && (
          <div className="flex items-center justify-center gap-2 pb-6">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <span className="text-sm text-slate-500 px-3">
              Page {page} of {leadsData.total_pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= leadsData.total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        )}
      </Card>
    </AppShell>
  );
}
