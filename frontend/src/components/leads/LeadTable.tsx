'use client';

import { useRouter } from 'next/navigation';
import { Eye } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { DataTable, type Column } from '@/components/ui/Table';
import { formatDate, capitalize } from '@/lib/utils';
import { StatusBadge } from '@/components/ui/Badge';
import { LeadScoreBadge } from './LeadScoreBadge';
import type { Lead } from '@/types/lead';

// ─── Props ───
interface LeadTableProps {
  leads: Lead[];
  loading?: boolean;
  sortKey?: string;
  sortOrder?: 'asc' | 'desc';
  onSort?: (key: string, order: 'asc' | 'desc') => void;
}

// ─── Component ───
export function LeadTable({
  leads,
  loading,
  sortKey,
  sortOrder,
  onSort,
}: LeadTableProps) {
  const router = useRouter();

  const columns: Column<Lead>[] = [
    {
      key: 'title',
      label: 'Title',
      sortable: true,
      className: 'max-w-[280px]',
      render: (_value, row) => (
        <div className="flex flex-col">
          <span className="font-semibold text-slate-900 truncate">
            {row.title}
          </span>
          {row.company && (
            <span className="text-xs text-slate-500 mt-0.5">{row.company}</span>
          )}
        </div>
      ),
    },
    {
      key: 'company',
      label: 'Company',
      sortable: true,
      render: (value) => (
        <span className="text-slate-700">{(value as string) || '—'}</span>
      ),
    },
    {
      key: 'location',
      label: 'Location',
      sortable: true,
      className: 'max-w-[160px]',
      render: (value) => (
        <span className="text-slate-500 text-xs truncate">
          {(value as string) || '—'}
        </span>
      ),
    },
    {
      key: 'score',
      label: 'Score',
      sortable: true,
      className: 'w-[80px]',
      render: (value) => <LeadScoreBadge score={value as number} />,
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      className: 'w-[120px]',
      render: (value) => <StatusBadge status={value as string} />,
    },
    {
      key: 'created_at',
      label: 'Date',
      sortable: true,
      className: 'w-[120px]',
      render: (value) => (
        <span className="text-xs text-slate-500">
          {formatDate(value as string)}
        </span>
      ),
    },
    {
      key: 'actions',
      label: '',
      className: 'w-[60px] text-right',
      render: (_value, row) => (
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<Eye className="h-4 w-4" />}
          onClick={(e: React.MouseEvent) => {
            e.stopPropagation();
            router.push(`/leads/${row.id}`);
          }}
        >
          View
        </Button>
      ),
    },
  ];

  return (
    <DataTable<Lead>
      columns={columns}
      data={leads}
      loading={loading}
      sortKey={sortKey}
      sortOrder={sortOrder}
      onSort={onSort}
      onRowClick={(row) => router.push(`/leads/${row.id}`)}
      emptyMessage="No leads found. Try adjusting your filters."
    />
  );
}

export default LeadTable;
