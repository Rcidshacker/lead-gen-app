'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import type {
  JobSource,
  SourceListResponse,
  SourceCreatePayload,
  SourceUpdatePayload,
} from '@/types/source';

// ─── Query Keys ───
export const sourceKeys = {
  all: ['sources'] as const,
  lists: () => [...sourceKeys.all, 'list'] as const,
  list: (page: number) => [...sourceKeys.lists(), { page }] as const,
  details: () => [...sourceKeys.all, 'detail'] as const,
  detail: (id: string) => [...sourceKeys.details(), id] as const,
};

// ─── Fetch Sources (paginated) ───
export function useSources(page: number = 1) {
  return useQuery<SourceListResponse>({
    queryKey: sourceKeys.list(page),
    queryFn: () =>
      apiClient.get<SourceListResponse>('/sources', {
        page,
        per_page: 20,
      }),
    placeholderData: (prev) => prev,
  });
}

// ─── Fetch Single Source ───
export function useSource(id: string) {
  return useQuery<JobSource>({
    queryKey: sourceKeys.detail(id),
    queryFn: () => apiClient.get<JobSource>(`/sources/${id}`),
    enabled: !!id,
  });
}

// ─── Create Source ───
export function useCreateSource() {
  const queryClient = useQueryClient();

  return useMutation<JobSource, Error, SourceCreatePayload>({
    mutationFn: (data) => apiClient.post<JobSource>('/sources', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
    },
  });
}

// ─── Update Source ───
export function useUpdateSource(id: string) {
  const queryClient = useQueryClient();

  return useMutation<JobSource, Error, SourceUpdatePayload>({
    mutationFn: (data) =>
      apiClient.put<JobSource>(`/sources/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
    },
  });
}

// ─── Delete Source ───
export function useDeleteSource(id: string) {
  const queryClient = useQueryClient();

  return useMutation<void, Error, void>({
    mutationFn: () => apiClient.delete<void>(`/sources/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
    },
  });
}

// ─── Trigger Scrape ───
export function useTriggerScrape(id: string) {
  const queryClient = useQueryClient();

  return useMutation<{ job_id: string }, Error, void>({
    mutationFn: () => apiClient.post<{ job_id: string }>(`/sources/${id}/scrape`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.detail(id) });
    },
  });
}
