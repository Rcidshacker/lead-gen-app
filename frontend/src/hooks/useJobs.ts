'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import type {
  ScrapingJob,
  ScrapingJobListResponse,
} from '@/types/job';

// ─── Query Keys ───
export const jobKeys = {
  all: ['jobs'] as const,
  lists: () => [...jobKeys.all, 'list'] as const,
  list: (page: number, status?: string) =>
    [...jobKeys.lists(), { page, status }] as const,
  details: () => [...jobKeys.all, 'detail'] as const,
  detail: (id: string) => [...jobKeys.details(), id] as const,
};

// ─── Fetch Jobs (paginated, filterable by status) ───
export function useJobs(page: number = 1, status?: string) {
  return useQuery<ScrapingJobListResponse>({
    queryKey: jobKeys.list(page, status),
    queryFn: () =>
      apiClient.get<ScrapingJobListResponse>('/jobs', {
        page,
        per_page: 20,
        ...(status && status !== 'all' ? { status } : {}),
      }),
    placeholderData: (prev) => prev,
  });
}

// ─── Fetch Single Job ───
export function useJob(id: string) {
  return useQuery<ScrapingJob>({
    queryKey: jobKeys.detail(id),
    queryFn: () => apiClient.get<ScrapingJob>(`/jobs/${id}`),
    enabled: !!id,
  });
}

// ─── Retry Job ───
export function useRetryJob(id: string) {
  const queryClient = useQueryClient();

  return useMutation<ScrapingJob, Error, void>({
    mutationFn: () => apiClient.post<ScrapingJob>(`/jobs/${id}/retry`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
    },
  });
}
