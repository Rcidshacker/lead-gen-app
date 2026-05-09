'use client';

import React from 'react';
import { Search, RotateCcw } from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import type { LeadFilters } from '@/types/lead';

// ─── Props ───
interface LeadFiltersBarProps {
  filters: LeadFilters;
  onFilterChange: (filters: LeadFilters) => void;
}

// ─── Platform Options ───
const platformOptions = [
  { value: '', label: 'All Platforms' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'indeed', label: 'Indeed' },
  { value: 'upwork', label: 'UpWork' },
  { value: 'naukri', label: 'Naukri' },
  { value: 'glassdoor', label: 'Glassdoor' },
  { value: 'ziprecruiter', label: 'ZipRecruiter' },
  { value: 'monster', label: 'Monster' },
  { value: 'angelist', label: 'AngelList' },
  { value: 'wellfound', label: 'Wellfound' },
];

// ─── Status Options ───
const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'new', label: 'New' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'interested', label: 'Interested' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'hired', label: 'Hired' },
];

// ─── Component ───
export function LeadFiltersBar({ filters, onFilterChange }: LeadFiltersBarProps) {
  const handleChange = (key: keyof LeadFilters, value: string | number | undefined) => {
    onFilterChange({
      ...filters,
      [key]: value === '' || value === undefined ? undefined : value,
    });
  };

  const handleReset = () => {
    onFilterChange({});
  };

  const hasActiveFilters =
    filters.search || filters.platform || filters.status || filters.min_score;

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-end gap-3">
      {/* Search */}
      <div className="w-full sm:w-64">
        <Input
          placeholder="Search leads..."
          value={filters.search || ''}
          onChange={(e) => handleChange('search', e.target.value)}
          leftIcon={<Search className="h-4 w-4" />}
        />
      </div>

      {/* Platform */}
      <div className="w-full sm:w-44">
        <Select
          options={platformOptions}
          value={filters.platform || ''}
          onChange={(value) => handleChange('platform', value)}
          placeholder="All Platforms"
        />
      </div>

      {/* Status */}
      <div className="w-full sm:w-40">
        <Select
          options={statusOptions}
          value={filters.status || ''}
          onChange={(value) => handleChange('status', value)}
          placeholder="All Statuses"
        />
      </div>

      {/* Min Score */}
      <div className="w-full sm:w-28">
        <Input
          type="number"
          placeholder="Min score"
          value={filters.min_score !== undefined ? String(filters.min_score) : ''}
          onChange={(e) =>
            handleChange('min_score', e.target.value ? Number(e.target.value) : undefined)
          }
          min={0}
          max={100}
        />
      </div>

      {/* Reset */}
      {hasActiveFilters && (
        <Button
          variant="ghost"
          size="sm"
          leftIcon={<RotateCcw className="h-4 w-4" />}
          onClick={handleReset}
        >
          Reset
        </Button>
      )}
    </div>
  );
}

export default LeadFiltersBar;
