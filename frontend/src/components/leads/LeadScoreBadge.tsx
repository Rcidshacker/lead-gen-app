'use client';

import React from 'react';
import { cn, getScoreColor } from '@/lib/utils';

// ─── Props ───
interface LeadScoreBadgeProps {
  score: number;
  size?: 'sm' | 'md';
  className?: string;
}

// ─── Component ───
export function LeadScoreBadge({ score, size = 'sm', className }: LeadScoreBadgeProps) {
  const colors = getScoreColor(score);

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-xs min-w-[36px] text-center',
    md: 'px-3 py-1 text-sm min-w-[44px] text-center font-semibold',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded-full font-medium whitespace-nowrap',
        colors.bg,
        colors.text,
        sizeStyles[size],
        className
      )}
    >
      {score}
    </span>
  );
}

export default LeadScoreBadge;
