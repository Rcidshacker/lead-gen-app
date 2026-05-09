'use client';

import React from 'react';
import { cn, capitalize } from '@/lib/utils';

// ─── Props ───
interface JobStatusBadgeProps {
  status: string;
  className?: string;
}

// ─── Styles ───
const styles: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  running: 'bg-blue-100 text-blue-700',
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
  cancelled: 'bg-amber-100 text-amber-700',
};

// ─── Component ───
export function JobStatusBadge({ status, className }: JobStatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap',
        styles[status] || styles.pending,
        status === 'running' && 'animate-pulse',
        className
      )}
    >
      {/* Status dot */}
      <span
        className={cn(
          'h-1.5 w-1.5 rounded-full bg-current'
        )}
      />
      {capitalize(status)}
    </span>
  );
}

export default JobStatusBadge;
