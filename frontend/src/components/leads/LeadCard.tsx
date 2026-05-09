'use client';

import Link from 'next/link';
import { MapPin, Building2 } from 'lucide-react';
import { cn, formatDate, truncate, capitalize } from '@/lib/utils';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { LeadScoreBadge } from './LeadScoreBadge';
import type { Lead } from '@/types/lead';

// ─── Props ───
interface LeadCardProps {
  lead: Lead;
}

// ─── Component ───
export function LeadCard({ lead }: LeadCardProps) {
  return (
    <Link href={`/leads/${lead.id}`} className="block group">
      <div
        className={cn(
          'bg-white rounded-xl border border-slate-200 p-5',
          'transition-all duration-200',
          'group-hover:shadow-md group-hover:border-slate-300 group-hover:-translate-y-0.5',
          'group-active:translate-y-0'
        )}
      >
        {/* Top row: Title + Score */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <h3 className="text-sm font-semibold text-slate-900 leading-snug group-hover:text-primary-600 transition-colors line-clamp-2">
            {lead.title}
          </h3>
          <LeadScoreBadge score={lead.score} />
        </div>

        {/* Company */}
        <div className="flex items-center gap-1.5 text-slate-600 mb-1">
          <Building2 className="h-3.5 w-3.5 shrink-0 text-slate-400" />
          <span className="text-sm truncate">{lead.company}</span>
        </div>

        {/* Location */}
        {lead.location && (
          <div className="flex items-center gap-1.5 text-slate-500 mb-3">
            <MapPin className="h-3.5 w-3.5 shrink-0 text-slate-400" />
            <span className="text-sm truncate">{lead.location}</span>
          </div>
        )}

        {/* Bottom row: Platform + Status + Date */}
        <div className="flex items-center justify-between gap-2 pt-3 border-t border-slate-100">
          <Badge size="sm" variant="default">
            {capitalize(String(lead.platform))}
          </Badge>
          <div className="flex items-center gap-2">
            <StatusBadge status={lead.status} />
            <span className="text-xs text-slate-400">
              {formatDate(lead.created_at)}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}

export default LeadCard;
