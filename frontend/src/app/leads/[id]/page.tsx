'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  ExternalLink,
  MapPin,
  Building2,
  DollarSign,
  Calendar,
  Globe,
  Save,
} from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { useLead, useUpdateLead } from '@/hooks/useLeads';
import { Button } from '@/components/ui/Button';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { LeadScoreBadge } from '@/components/leads/LeadScoreBadge';
import { Card, CardHeader, CardTitle, CardBody } from '@/components/ui/Card';
import { cn, formatDate, capitalize, getScoreLabel } from '@/lib/utils';
import type { LeadStatus, LeadUpdatePayload } from '@/types/lead';

// ─── Status flow options ───
const statusOptions: LeadStatus[] = ['new', 'contacted', 'interested', 'rejected', 'hired'];

const statusLabels: Record<LeadStatus, string> = {
  new: 'Mark as Contacted',
  contacted: 'Mark as Interested',
  interested: 'Mark as Hired',
  rejected: 'Mark as New',
  hired: 'Mark as New',
};

// ─── Lead Detail Page ───
export default function LeadDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: lead, isLoading } = useLead(id);
  const updateLead = useUpdateLead();

  const [notes, setNotes] = useState('');
  const [localStatus, setLocalStatus] = useState<LeadStatus | null>(null);

  // Sync notes from lead data
  React.useEffect(() => {
    if (lead && notes === '') {
      setNotes(lead.notes || '');
    }
  }, [lead, notes]);

  if (isLoading) {
    return (
      <AppShell title="Lead Details">
        <div className="animate-pulse space-y-6">
          <div className="skeleton h-8 w-32 rounded" />
          <div className="skeleton h-48 w-full rounded-xl" />
          <div className="skeleton h-64 w-full rounded-xl" />
        </div>
      </AppShell>
    );
  }

  if (!lead) {
    return (
      <AppShell title="Lead Not Found">
        <div className="text-center py-16">
          <h2 className="text-lg font-semibold text-slate-900 mb-2">Lead not found</h2>
          <p className="text-sm text-slate-500 mb-4">The lead you&apos;re looking for doesn&apos;t exist.</p>
          <Button variant="outline" onClick={() => router.push('/leads')}>
            Back to Leads
          </Button>
        </div>
      </AppShell>
    );
  }

  const currentStatus = (localStatus || lead.status) as LeadStatus;

  const handleStatusChange = async (newStatus: LeadStatus) => {
    try {
      await updateLead.mutateAsync({ id: lead.id, data: { status: newStatus } });
      setLocalStatus(newStatus);
    } catch {
      // Error handled by mutation
    }
  };

  const handleSaveNotes = async () => {
    try {
      await updateLead.mutateAsync({ id: lead.id, data: { notes } });
    } catch {
      // Error handled by mutation
    }
  };

  // Find the next logical status action
  const nextStatusIndex = statusOptions.indexOf(currentStatus);
  const nextStatus = nextStatusIndex >= 0 && nextStatusIndex < statusOptions.length - 1
    ? statusOptions[nextStatusIndex + 1]
    : null;

  return (
    <AppShell title="Lead Details">
      {/* Back */}
      <button
        onClick={() => router.push('/leads')}
        className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition-colors mb-6"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Leads
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ─── Main Content (2 cols) ─── */}
        <div className="lg:col-span-2 space-y-6">
          {/* Header Card */}
          <Card padding="lg">
            <CardBody className="space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <h2 className="text-xl font-bold text-slate-900 mb-2">{lead.title}</h2>

                  <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
                    {lead.company && (
                      <div className="flex items-center gap-1.5">
                        <Building2 className="h-4 w-4 text-slate-400" />
                        <span className="font-medium">{lead.company}</span>
                      </div>
                    )}
                    {lead.location && (
                      <div className="flex items-center gap-1.5">
                        <MapPin className="h-4 w-4 text-slate-400" />
                        <span>{lead.location}</span>
                      </div>
                    )}
                    {lead.salary && (
                      <div className="flex items-center gap-1.5">
                        <DollarSign className="h-4 w-4 text-slate-400" />
                        <span>{lead.salary}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Score */}
                <div className="text-center shrink-0">
                  <LeadScoreBadge score={lead.score} size="md" />
                  <p className="text-xs text-slate-500 mt-1">{getScoreLabel(lead.score)}</p>
                </div>
              </div>

              {/* Meta row */}
              <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-slate-100">
                <Badge variant="default" size="md">
                  <Globe className="h-3 w-3 mr-1" />
                  {capitalize(String(lead.platform))}
                </Badge>
                <StatusBadge status={currentStatus} size="md" />
                <div className="flex items-center gap-1.5 text-xs text-slate-500">
                  <Calendar className="h-3.5 w-3.5" />
                  {formatDate(lead.created_at)}
                </div>
              </div>

              {/* Actions */}
              <div className="flex flex-wrap items-center gap-2 pt-2">
                {statusOptions.map((status) => {
                  if (status === currentStatus) return null;
                  return (
                    <Button
                      key={status}
                      variant="outline"
                      size="sm"
                      onClick={() => handleStatusChange(status)}
                      disabled={updateLead.isPending}
                    >
                      {capitalize(status)}
                    </Button>
                  );
                })}
                {nextStatus && (
                  <Button
                    size="sm"
                    onClick={() => handleStatusChange(nextStatus)}
                    loading={updateLead.isPending}
                  >
                    {statusLabels[nextStatus]}
                  </Button>
                )}
              </div>
            </CardBody>
          </Card>

          {/* Description */}
          {lead.description && (
            <Card padding="lg">
              <CardHeader>
                <CardTitle>Description</CardTitle>
              </CardHeader>
              <CardBody>
                <div className="prose prose-sm prose-slate max-w-none">
                  <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                    {lead.description}
                  </p>
                </div>
              </CardBody>
            </Card>
          )}

          {/* Requirements */}
          {lead.requirements && (
            <Card padding="lg">
              <CardHeader>
                <CardTitle>Requirements</CardTitle>
              </CardHeader>
              <CardBody>
                <div className="prose prose-sm prose-slate max-w-none">
                  <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                    {lead.requirements}
                  </p>
                </div>
              </CardBody>
            </Card>
          )}

          {/* Contact Info */}
          {lead.contact_info && Object.keys(lead.contact_info).length > 0 && (
            <Card padding="lg">
              <CardHeader>
                <CardTitle>Contact Information</CardTitle>
              </CardHeader>
              <CardBody>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {Object.entries(lead.contact_info).map(([key, value]) => (
                    <div key={key} className="flex flex-col">
                      <span className="text-xs font-medium text-slate-500 capitalize mb-0.5">
                        {key.replace(/_/g, ' ')}
                      </span>
                      <span className="text-sm text-slate-900">
                        {String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </CardBody>
            </Card>
          )}
        </div>

        {/* ─── Sidebar (1 col) ─── */}
        <div className="space-y-6">
          {/* Notes */}
          <Card padding="lg">
            <CardHeader>
              <CardTitle>Notes</CardTitle>
            </CardHeader>
            <CardBody>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add notes about this lead..."
                rows={6}
                className={cn(
                  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900',
                  'placeholder:text-slate-400 transition-colors duration-150',
                  'focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-500',
                  'resize-y'
                )}
              />
              <Button
                size="sm"
                leftIcon={<Save className="h-3.5 w-3.5" />}
                onClick={handleSaveNotes}
                loading={updateLead.isPending}
                className="mt-3"
                fullWidth
              >
                Save Notes
              </Button>
            </CardBody>
          </Card>

          {/* Quick Info */}
          <Card padding="lg">
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardBody className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Source ID</span>
                <span className="text-slate-900 font-mono text-xs">
                  {lead.source_id.slice(0, 8)}...
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Created</span>
                <span className="text-slate-900">{formatDate(lead.created_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Updated</span>
                <span className="text-slate-900">{formatDate(lead.updated_at)}</span>
              </div>
            </CardBody>
          </Card>

          {/* View Original */}
          {lead.url && (
            <a
              href={lead.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block"
            >
              <Card hover padding="lg">
                <CardBody className="flex items-center justify-center gap-2 text-primary-600 font-medium text-sm">
                  <ExternalLink className="h-4 w-4" />
                  View Original Job Post
                </CardBody>
              </Card>
            </a>
          )}
        </div>
      </div>
    </AppShell>
  );
}
