'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import type { PlatformType } from '@/types/source';

// ─── Props ───
interface SourceFormProps {
  onSubmit: (data: SourceFormData) => void;
  loading?: boolean;
  onCancel?: () => void;
  initialValues?: Partial<SourceFormData>;
}

// ─── Form Data ───
export interface SourceFormData {
  name: string;
  platform: PlatformType;
  url: string;
  schedule: string;
  max_pages: number;
}

// ─── Options ───
const platformOptions = [
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'indeed', label: 'Indeed' },
  { value: 'upwork', label: 'UpWork' },
  { value: 'naukri', label: 'Naukri' },
  { value: 'glassdoor', label: 'Glassdoor' },
  { value: 'ziprecruiter', label: 'ZipRecruiter' },
  { value: 'monster', label: 'Monster' },
  { value: 'custom', label: 'Custom' },
];

const scheduleOptions = [
  { value: 'manual', label: 'Manual' },
  { value: 'hourly', label: 'Hourly' },
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
];

// ─── Component ───
export function SourceForm({
  onSubmit,
  loading = false,
  onCancel,
  initialValues,
}: SourceFormProps) {
  const [form, setForm] = useState<SourceFormData>({
    name: initialValues?.name || '',
    platform: initialValues?.platform || 'linkedin',
    url: initialValues?.url || '',
    schedule: initialValues?.schedule || 'manual',
    max_pages: initialValues?.max_pages || 10,
  });

  const [errors, setErrors] = useState<Partial<Record<keyof SourceFormData, string>>>({});

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof SourceFormData, string>> = {};
    if (!form.name.trim()) newErrors.name = 'Name is required';
    if (!form.url.trim()) newErrors.url = 'URL is required';
    if (form.url && !form.url.startsWith('http')) newErrors.url = 'URL must start with http:// or https://';
    if (form.max_pages < 1) newErrors.max_pages = 'Must be at least 1';
    if (form.max_pages > 100) newErrors.max_pages = 'Max 100 pages';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      onSubmit(form);
    }
  };

  const updateField = <K extends keyof SourceFormData>(key: K, value: SourceFormData[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (errors[key]) {
      setErrors((prev) => ({ ...prev, [key]: undefined }));
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Name */}
      <Input
        label="Source Name"
        placeholder="e.g., Senior React Jobs - LinkedIn"
        value={form.name}
        onChange={(e) => updateField('name', e.target.value)}
        error={errors.name}
        required
      />

      {/* Platform */}
      <Select
        label="Platform"
        options={platformOptions}
        value={form.platform}
        onChange={(value) => updateField('platform', value as PlatformType)}
        placeholder="Select platform"
        required
      />

      {/* URL */}
      <Input
        label="URL"
        placeholder="https://www.linkedin.com/jobs/search/..."
        value={form.url}
        onChange={(e) => updateField('url', e.target.value)}
        error={errors.url}
        required
      />

      {/* Schedule */}
      <Select
        label="Schedule"
        options={scheduleOptions}
        value={form.schedule}
        onChange={(value) => updateField('schedule', value)}
        helperText="How often to scrape this source"
      />

      {/* Max Pages */}
      <Input
        label="Max Pages"
        type="number"
        placeholder="10"
        value={String(form.max_pages)}
        onChange={(e) => updateField('max_pages', Number(e.target.value))}
        error={errors.max_pages}
        min={1}
        max={100}
        helperText="Maximum number of pages to scrape per run"
      />

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 pt-2">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
            Cancel
          </Button>
        )}
        <Button type="submit" loading={loading}>
          {initialValues ? 'Update Source' : 'Create Source'}
        </Button>
      </div>
    </form>
  );
}

export default SourceForm;
