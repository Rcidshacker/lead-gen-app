'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import type {
  Lead,
  LeadFilters,
  LeadListResponse,
  LeadUpdatePayload,
} from '@/types/lead';

// ─── Query Keys ───
export const leadKeys = {
  all: ['leads'] as const,
  lists: () => [...leadKeys.all, 'list'] as const,
  list: (filters: LeadFilters, page: number) =>
    [...leadKeys.lists(), { filters, page }] as const,
  details: () => [...leadKeys.all, 'detail'] as const,
  detail: (id: string) => [...leadKeys.details(), id] as const,
};

// ─── Fetch Leads (with pagination & filters) ───
export function useLeads(filters: LeadFilters = {}, page: number = 1) {
  return useQuery<LeadListResponse>({
    queryKey: leadKeys.list(filters, page),
    queryFn: () =>
      apiClient.get<LeadListResponse>('/leads', {
        ...filters,
        page,
        per_page: 20,
      }),
    placeholderData: (prev) => prev,
  });
}

// ─── Fetch Single Lead ───
export function useLead(id: string) {
  return useQuery<Lead>({
    queryKey: leadKeys.detail(id),
    queryFn: () => apiClient.get<Lead>(`/leads/${id}`),
    enabled: !!id,
  });
}

// ─── Update Lead (status, notes) ───
export function useUpdateLead() {
  const queryClient = useQueryClient();

  return useMutation<Lead, Error, { id: string; data: LeadUpdatePayload }>({
    mutationFn: ({ id, data }) =>
      apiClient.patch<Lead>(`/leads/${id}`, data),
    onSuccess: (_data, variables) => {
      // Invalidate the specific lead detail
      queryClient.invalidateQueries({
        queryKey: leadKeys.detail(variables.id),
      });
      // Invalidate all lead lists (for refreshed status/score counts)
      queryClient.invalidateQueries({
        queryKey: leadKeys.lists(),
      });
    },
  });
}
