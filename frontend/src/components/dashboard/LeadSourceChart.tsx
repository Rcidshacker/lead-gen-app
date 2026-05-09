'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  type TooltipProps,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardBody } from '@/components/ui/Card';
import { capitalize } from '@/lib/utils';

// ─── Props ───
interface LeadSourceChartProps {
  data: Array<{ platform: string; count: number }>;
  loading?: boolean;
}

// ─── Custom Tooltip ───
function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-lg px-3 py-2">
      <p className="text-sm font-medium text-slate-900">
        {capitalize(payload[0].payload.platform)}
      </p>
      <p className="text-sm text-slate-600">
        {payload[0].value} leads
      </p>
    </div>
  );
}

// ─── Component ───
export function LeadSourceChart({ data, loading }: LeadSourceChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Leads by Platform</CardTitle>
      </CardHeader>
      <CardBody>
        {loading ? (
          <div className="h-[280px] flex items-center justify-center">
            <div className="skeleton h-4 w-3/4 rounded" />
          </div>
        ) : !data || data.length === 0 ? (
          <div className="h-[280px] flex items-center justify-center">
            <p className="text-sm text-slate-500">No data available yet.</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={data}
              margin={{ top: 4, right: 4, left: -10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis
                dataKey="platform"
                tick={{ fill: '#64748b', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(value: string) => capitalize(value)}
              />
              <YAxis
                tick={{ fill: '#64748b', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f8fafc' }} />
              <Bar
                dataKey="count"
                fill="#6366f1"
                radius={[6, 6, 0, 0]}
                maxBarSize={48}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardBody>
    </Card>
  );
}

export default LeadSourceChart;
