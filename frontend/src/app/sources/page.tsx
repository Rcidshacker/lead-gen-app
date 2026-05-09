'use client';

import React, { useState, useMemo } from 'react';
import { Plus, Search, Zap } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { useSources, useCreateSource, useDeleteSource, useTriggerScrape } from '@/hooks/useSources';
import { SourceCard } from '@/components/sources/SourceCard';
import { SourceForm, type SourceFormData } from '@/components/sources/SourceForm';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { capitalize } from '@/lib/utils';

// ─── Sources Page ───
export default function SourcesPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [scrapingId, setScrapingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data, isLoading } = useSources(page);
  const createSource = useCreateSource();

  const sources = data?.items || [];

  // Filter sources by search
  const filteredSources = useMemo(() => {
    if (!search.trim()) return sources;
    const q = search.toLowerCase();
    return sources.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.platform.toLowerCase().includes(q) ||
        s.url.toLowerCase().includes(q)
    );
  }, [sources, search]);

  // Handlers
  const handleCreate = async (formData: SourceFormData) => {
    try {
      await createSource.mutateAsync({
        name: formData.name,
        platform: formData.platform,
        url: formData.url,
        config: {
          keywords: [],
          locations: [],
          max_pages: formData.max_pages,
        },
        schedule: {
          frequency: formData.schedule === 'hourly' ? 'daily' : formData.schedule === 'manual' ? 'daily' : (formData.schedule as 'daily' | 'weekly' | 'biweekly' | 'monthly'),
          enabled: formData.schedule !== 'manual',
        },
      });
      setShowCreateModal(false);
    } catch {
      // Error handled by mutation
    }
  };

  const handleScrape = async (id: string) => {
    setScrapingId(id);
    const { useTriggerScrape: useTrigger } = await import('@/hooks/useSources');
    // Use inline mutation instead to avoid hooks rules
    try {
      const { apiClient } = await import('@/lib/api');
      await apiClient.post(`/sources/${id}/scrape`);
    } catch {
      // ignore
    } finally {
      setScrapingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this source? This cannot be undone.')) return;
    setDeletingId(id);
    try {
      const { apiClient } = await import('@/lib/api');
      await apiClient.delete(`/sources/${id}`);
      // Refresh
      window.location.reload();
    } catch {
      setDeletingId(null);
    }
  };

  return (
    <AppShell title="Sources">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <p className="text-sm text-slate-500">
            Manage your job scraping sources and configurations.
          </p>
        </div>
        <Button
          leftIcon={<Plus className="h-4 w-4" />}
          onClick={() => setShowCreateModal(true)}
        >
          Add Source
        </Button>
      </div>

      {/* Search */}
      <div className="mb-6 max-w-sm">
        <Input
          placeholder="Search sources..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          leftIcon={<Search className="h-4 w-4" />}
        />
      </div>

      {/* Source Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-200 p-6 animate-pulse">
              <div className="flex justify-between mb-4">
                <div className="skeleton h-6 w-20 rounded-full" />
                <div className="skeleton h-6 w-16 rounded-full" />
              </div>
              <div className="skeleton h-5 w-3/4 rounded mb-2" />
              <div className="skeleton h-4 w-full rounded mb-4" />
              <div className="skeleton h-8 w-24 rounded" />
            </div>
          ))}
        </div>
      ) : filteredSources.length === 0 ? (
        <div className="text-center py-16">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
            <Zap className="h-8 w-8 text-slate-300" />
          </div>
          <h3 className="text-lg font-semibold text-slate-900 mb-2">No sources yet</h3>
          <p className="text-sm text-slate-500 mb-6 max-w-sm mx-auto">
            Add your first job source to start finding leads across platforms.
          </p>
          <Button
            leftIcon={<Plus className="h-4 w-4" />}
            onClick={() => setShowCreateModal(true)}
          >
            Add Source
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredSources.map((source) => (
            <SourceCard
              key={source.id}
              source={source}
              onScrape={handleScrape}
              onDelete={handleDelete}
              scraping={scrapingId === source.id}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-8">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <span className="text-sm text-slate-500 px-3">
            Page {page} of {data.total_pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= data.total_pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}

      {/* Create Source Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Add New Source"
        description="Configure a new job scraping source."
        footer={undefined}
        size="lg"
      >
        <SourceForm
          onSubmit={handleCreate}
          loading={createSource.isPending}
          onCancel={() => setShowCreateModal(false)}
        />
        {createSource.isError && (
          <p className="mt-3 text-sm text-red-600">
            Failed to create source. Please try again.
          </p>
        )}
      </Modal>
    </AppShell>
  );
}
