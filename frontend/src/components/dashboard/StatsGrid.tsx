'use client';

import React from 'react';
import {
  Users,
  TrendingUp,
  Target,
  Globe,
  TrendingDown,
  type LucideIcon,
} from 'lucide-react';
import { cn, formatNumber, formatCompactNumber } from '@/lib/utils';
import { Card, CardBody } from '@/components/ui/Card';

// ─── Stat Card Props ───
interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: number | string;
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
  format?: 'number' | 'compact' | 'none';
  iconBg?: string;
  iconColor?: string;
}

// ─── Stat Card ───
function StatCard({
  icon: Icon,
  label,
  value,
  trend,
  format = 'number',
  iconBg = 'bg-primary-50',
  iconColor = 'text-primary-600',
}: StatCardProps) {
  const displayValue =
    typeof value === 'string'
      ? value
      : format === 'compact'
        ? formatCompactNumber(value)
        : format === 'number'
          ? formatNumber(value)
          : String(value);

  return (
    <Card>
      <CardBody className="flex items-start gap-4">
        {/* Icon */}
        <div
          className={cn(
            'flex items-center justify-center w-12 h-12 rounded-xl shrink-0',
            iconBg
          )}
        >
          <Icon className={cn('h-6 w-6', iconColor)} />
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-slate-500 mb-1">{label}</p>
          <div className="flex items-end gap-2">
            <p className="text-2xl font-bold text-slate-900 tracking-tight">
              {displayValue}
            </p>
            {trend && (
              <span
                className={cn(
                  'inline-flex items-center gap-0.5 text-xs font-medium mb-1',
                  trend.direction === 'up' ? 'text-emerald-600' : 'text-red-500'
                )}
              >
                {trend.direction === 'up' ? (
                  <TrendingUp className="h-3 w-3" />
                ) : (
                  <TrendingDown className="h-3 w-3" />
                )}
                {Math.abs(trend.value)}%
              </span>
            )}
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

// ─── Stats Grid Props ───
interface StatsGridProps {
  totalLeads: number;
  newLeads: number;
  avgScore: number;
  activeSources: number;
  totalLeadsTrend?: number;
  newLeadsTrend?: number;
  avgScoreTrend?: number;
  activeSourcesTrend?: number;
}

// ─── Stats Grid Component ───
export function StatsGrid({
  totalLeads,
  newLeads,
  avgScore,
  activeSources,
  totalLeadsTrend,
  newLeadsTrend,
  avgScoreTrend,
  activeSourcesTrend,
}: StatsGridProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        icon={Users}
        label="Total Leads"
        value={totalLeads}
        trend={
          totalLeadsTrend !== undefined
            ? { value: totalLeadsTrend, direction: totalLeadsTrend >= 0 ? 'up' : 'down' }
            : undefined
        }
        iconBg="bg-blue-50"
        iconColor="text-blue-600"
      />
      <StatCard
        icon={TrendingUp}
        label="New Today"
        value={newLeads}
        trend={
          newLeadsTrend !== undefined
            ? { value: newLeadsTrend, direction: newLeadsTrend >= 0 ? 'up' : 'down' }
            : undefined
        }
        iconBg="bg-emerald-50"
        iconColor="text-emerald-600"
      />
      <StatCard
        icon={Target}
        label="Avg Score"
        value={avgScore.toFixed(1)}
        format="none"
        trend={
          avgScoreTrend !== undefined
            ? { value: avgScoreTrend, direction: avgScoreTrend >= 0 ? 'up' : 'down' }
            : undefined
        }
        iconBg="bg-violet-50"
        iconColor="text-violet-600"
      />
      <StatCard
        icon={Globe}
        label="Active Sources"
        value={activeSources}
        trend={
          activeSourcesTrend !== undefined
            ? { value: activeSourcesTrend, direction: activeSourcesTrend >= 0 ? 'up' : 'down' }
            : undefined
        }
        iconBg="bg-amber-50"
        iconColor="text-amber-600"
      />
    </div>
  );
}

export default StatsGrid;
