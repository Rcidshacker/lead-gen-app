'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { formatDate, capitalize } from '@/lib/utils';
import { StatusBadge } from '@/components/ui/Badge';
import { LeadScoreBadge } from '@/components/leads/LeadScoreBadge';
import { Card, CardHeader, CardTitle, CardBody } from '@/components/ui/Card';
import type { Lead } from '@/types/lead';

// ─── Props ───
interface RecentLeadsProps {
  leads: Lead[];
  loading?: boolean;
}

// ─── Component ───
export function RecentLeads({ leads, loading }: RecentLeadsProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Recent Leads</CardTitle>
          <Link
            href="/leads"
            className="text-sm font-medium text-primary-600 hover:text-primary-700 flex items-center gap-1 transition-colors"
          >
            View All
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </CardHeader>
      <CardBody>
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="skeleton h-4 w-4 rounded-full" />
                <div className="skeleton h-4 flex-1 rounded" />
                <div className="skeleton h-4 w-12 rounded" />
                <div className="skeleton h-4 w-16 rounded" />
              </div>
            ))}
          </div>
        ) : leads.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-8">
            No leads yet. Start by adding a source.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider pb-3 pr-4">
                    Lead
                  </th>
                  <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider pb-3 pr-4">
                    Score
                  </th>
                  <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider pb-3 pr-4">
                    Status
                  </th>
                  <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wider pb-3">
                    Date
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {leads.map((lead) => (
                  <tr key={lead.id} className="group">
                    <td className="py-3 pr-4">
                      <Link
                        href={`/leads/${lead.id}`}
                        className="group-hover:text-primary-600 transition-colors"
                      >
                        <p className="font-medium text-slate-900 truncate max-w-[200px]">
                          {lead.title}
                        </p>
                        <p className="text-xs text-slate-500 mt-0.5 truncate max-w-[200px]">
                          {lead.company}
                        </p>
                      </Link>
                    </td>
                    <td className="py-3 pr-4">
                      <LeadScoreBadge score={lead.score} />
                    </td>
                    <td className="py-3 pr-4">
                      <StatusBadge status={lead.status} />
                    </td>
                    <td className="py-3 text-right">
                      <span className="text-xs text-slate-400">
                        {formatDate(lead.created_at)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

export default RecentLeads;
