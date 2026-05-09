'use client';

import React from 'react';
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Inbox,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── Types ───
export interface Column<T> {
  key: string;
  label: string;
  sortable?: boolean;
  className?: string;
  render?: (value: unknown, row: T, index: number) => React.ReactNode;
}

export interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  onSort?: (key: string, order: 'asc' | 'desc') => void;
  sortKey?: string;
  sortOrder?: 'asc' | 'desc';
  loading?: boolean;
  emptyMessage?: string;
  emptyIcon?: React.ReactNode;
  onRowClick?: (row: T) => void;
  rowClassName?: (row: T, index: number) => string;
  className?: string;
  compact?: boolean;
}

// ─── Skeleton Row ───
function SkeletonRow({ cols, compact }: { cols: number; compact?: boolean }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className={cn('px-4', compact ? 'py-2.5' : 'py-4')}>
          <div className="skeleton h-4 w-full rounded" />
        </td>
      ))}
    </tr>
  );
}

// ─── Table Component ───
export function DataTable<T>({
  columns,
  data,
  onSort,
  sortKey,
  sortOrder,
  loading = false,
  emptyMessage = 'No data found',
  emptyIcon,
  onRowClick,
  rowClassName,
  className,
  compact = false,
}: TableProps<T>) {
  const handleSort = (key: string) => {
    if (!onSort || !columns.find((c) => c.key === key)?.sortable) return;
    const newOrder = sortKey === key && sortOrder === 'asc' ? 'desc' : 'asc';
    onSort(key, newOrder);
  };

  const renderSortIcon = (key: string) => {
    if (sortKey !== key) {
      return <ArrowUpDown className="h-3.5 w-3.5 text-slate-300" />;
    }
    return sortOrder === 'asc' ? (
      <ArrowUp className="h-3.5 w-3.5 text-primary-600" />
    ) : (
      <ArrowDown className="h-3.5 w-3.5 text-primary-600" />
    );
  };

  return (
    <div className={cn('w-full overflow-x-auto rounded-xl border border-slate-200', className)}>
      <table className="w-full text-sm">
        {/* Head */}
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50">
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  'px-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider',
                  compact ? 'py-2.5' : 'py-3.5',
                  col.sortable && 'cursor-pointer select-none hover:text-slate-700 transition-colors',
                  col.className
                )}
                onClick={() => col.sortable && handleSort(col.key)}
              >
                <div className="flex items-center gap-1.5">
                  {col.label}
                  {col.sortable && renderSortIcon(col.key)}
                </div>
              </th>
            ))}
          </tr>
        </thead>

        {/* Body */}
        <tbody className="divide-y divide-slate-100">
          {loading ? (
            // Loading skeleton
            Array.from({ length: 5 }).map((_, i) => (
              <SkeletonRow key={i} cols={columns.length} compact={compact} />
            ))
          ) : data.length === 0 ? (
            // Empty state
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-16 text-center"
              >
                <div className="flex flex-col items-center gap-3">
                  <div className="p-3 rounded-full bg-slate-100">
                    {emptyIcon || <Inbox className="h-6 w-6 text-slate-400" />}
                  </div>
                  <p className="text-sm text-slate-500">{emptyMessage}</p>
                </div>
              </td>
            </tr>
          ) : (
            // Data rows
            data.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className={cn(
                  'transition-colors duration-100',
                  onRowClick && 'cursor-pointer hover:bg-slate-50',
                  rowClassName?.(row, rowIndex)
                )}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn(
                      'px-4 text-slate-700',
                      compact ? 'py-2.5' : 'py-4',
                      col.className
                    )}
                  >
                    {col.render
                      ? col.render((row as Record<string, unknown>)[col.key], row, rowIndex)
                      : ((row as Record<string, unknown>)[col.key] as React.ReactNode) ?? '—'}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default DataTable;
