'use client';

import React from 'react';
import { ExternalLink, Play, Trash2, Clock } from 'lucide-react';
import { cn, formatRelativeTime, truncate, capitalize } from '@/lib/utils';
import { Badge, StatusBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import type { JobSource } from '@/types/source';

// ─── Props ───
interface SourceCardProps {
  source: JobSource;
  onScrape?: (id: string) => void;
  onDelete?: (id: string) => void;
  scraping?: boolean;
}

// ─── Platform Colors ───
const platformColors: Record<string, string> = {
  linkedin: 'bg-blue-100 text-blue-700',
  indeed: 'bg-violet-100 text-violet-700',
  upwork: 'bg-green-100 text-green-700',
  naukri: 'bg-sky-100 text-sky-700',
  glassdoor: 'bg-orange-100 text-orange-700',
  ziprecruiter: 'bg-teal-100 text-teal-700',
  monster: 'bg-rose-100 text-rose-700',
  angelist: 'bg-indigo-100 text-indigo-700',
  wellfound: 'bg-amber-100 text-amber-700',
  custom: 'bg-slate-100 text-slate-700',
};

// ─── Component ───
export function SourceCard({ source, onScrape, onDelete, scraping }: SourceCardProps) {
  const platformColor = platformColors[source.platform] || platformColors.custom;

  return (
    <Card hover className="flex flex-col">
      {/* Header: Platform + Status */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <Badge className={cn('text-xs', platformColor)}>
          {capitalize(source.platform)}
        </Badge>
        <StatusBadge status={source.status} />
      </div>

      {/* Name */}
      <h3 className="text-base font-semibold text-slate-900 mb-1 line-clamp-1">
        {source.name}
      </h3>

      {/* URL */}
      {source.url && (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs text-slate-500 hover:text-primary-600 transition-colors mb-3"
          onClick={(e) => e.stopPropagation()}
        >
          <ExternalLink className="h-3 w-3 shrink-0" />
          <span className="truncate">{truncate(source.url, 50)}</span>
        </a>
      )}

      {/* Stats */}
      <div className="flex items-center gap-4 mt-auto pt-3 border-t border-slate-100 mb-3">
        <div className="flex flex-col">
          <span className="text-lg font-bold text-slate-900">{source.total_leads}</span>
          <span className="text-xs text-slate-500">Leads</span>
        </div>
        {source.last_scraped_at && (
          <div className="flex items-center gap-1.5 text-xs text-slate-500 ml-auto">
            <Clock className="h-3.5 w-3.5" />
            <span>{formatRelativeTime(source.last_scraped_at)}</span>
          </div>
        )}
      </div>

      {/* Error message */}
      {source.last_error && (
        <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2 mb-3 line-clamp-2">
          {truncate(source.last_error, 100)}
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button
          variant="primary"
          size="sm"
          leftIcon={<Play className="h-3.5 w-3.5" />}
          loading={scraping}
          onClick={() => onScrape?.(source.id)}
          className="flex-1"
        >
          Scrape
        </Button>
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<Trash2 className="h-3.5 w-3.5" />}
          onClick={() => onDelete?.(source.id)}
          className="text-slate-400 hover:text-red-600"
        >
          Delete
        </Button>
      </div>
    </Card>
  );
}

export default SourceCard;
