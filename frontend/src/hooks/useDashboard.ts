'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import type { DashboardStats } from '@/types/dashboard';

// ─── Query Keys ───
export const dashboardKeys = {
  all: ['dashboard'] as const,
  stats: () => [...dashboardKeys.all, 'stats'] as const,
};

// ─── Fetch Dashboard Stats ───
export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: dashboardKeys.stats(),
    queryFn: () => apiClient.get<DashboardStats>('/dashboard/stats'),
    staleTime: 2 * 60 * 1000, // 2 minutes — dashboard stats update frequently
  });
}
