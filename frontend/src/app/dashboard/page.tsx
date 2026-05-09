'use client';

import React from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { useDashboardStats } from '@/hooks/useDashboard';
import { StatsGrid } from '@/components/dashboard/StatsGrid';
import { RecentLeads } from '@/components/dashboard/RecentLeads';
import { ScrapeActivity } from '@/components/dashboard/ScrapeActivity';
import { LeadSourceChart } from '@/components/dashboard/LeadSourceChart';
import { useLeads } from '@/hooks/useLeads';
import { useJobs } from '@/hooks/useJobs';

// ─── Dashboard Page ───
export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();

  // Fetch recent leads (page 1, no filters, show latest)
  const { data: leadsData, isLoading: leadsLoading } = useLeads({}, 1);

  // Fetch recent jobs for activity feed
  const { data: jobsData, isLoading: jobsLoading } = useJobs(1);

  const recentLeads = leadsData?.items?.slice(0, 5) || [];
  const recentJobs = jobsData?.items || [];

  return (
    <AppShell title="Dashboard">
      {/* Stats Grid */}
      <StatsGrid
        totalLeads={stats?.total_leads ?? 0}
        newLeads={stats?.new_leads ?? 0}
        avgScore={stats?.avg_score ?? 0}
        activeSources={stats?.active_sources ?? 0}
      />

      {/* Charts & Activity Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Lead Source Chart — takes 2 cols */}
        <div className="lg:col-span-2">
          <LeadSourceChart
            data={stats?.leads_by_platform || []}
            loading={statsLoading}
          />
        </div>

        {/* Scrape Activity — takes 1 col */}
        <div>
          <ScrapeActivity
            jobs={recentJobs}
            loading={jobsLoading}
          />
        </div>
      </div>

      {/* Recent Leads Table */}
      <div className="mt-6">
        <RecentLeads
          leads={recentLeads}
          loading={leadsLoading}
        />
      </div>
    </AppShell>
  );
}
