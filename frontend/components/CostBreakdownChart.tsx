'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { getModelColor, formatCost } from '@/lib/api';

interface CostBreakdownChartProps {
  data: Record<string, number>;
  loading: boolean;
}

export default function CostBreakdownChart({ data, loading }: CostBreakdownChartProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <div className="h-5 w-40 bg-slate-200 rounded animate-pulse mb-6" />
        <div className="h-64 flex items-end justify-around gap-4 p-4">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="bg-slate-100 rounded-t animate-pulse"
              style={{ width: '20%', height: `${30 + Math.random() * 60}%` }}
            />
          ))}
        </div>
      </div>
    );
  }

  const chartData = Object.entries(data)
    .map(([name, value], index) => ({
      name: name.split('/').pop() || name,
      fullName: name,
      cost: value,
      fill: getModelColor(name, index),
    }))
    .sort((a, b) => b.cost - a.cost);

  if (chartData.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Cost by Model</h3>
        <div className="h-64 flex items-center justify-center text-slate-400">
          No cost data available yet
        </div>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white px-4 py-3 rounded-xl shadow-lg border border-slate-100">
          <p className="font-medium text-slate-800">{data.fullName}</p>
          <p className="text-sm text-slate-500">
            Cost: {formatCost(data.cost)}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
      <h3 className="text-lg font-semibold text-slate-800 mb-4">Cost by Model</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
            <XAxis
              type="number"
              tickFormatter={(value) => formatCost(value)}
              tick={{ fontSize: 12, fill: '#64748b' }}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 12, fill: '#64748b' }}
              width={80}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar
              dataKey="cost"
              radius={[0, 4, 4, 0]}
              fill="#0ea5e9"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// Need to import Cell
import { Cell } from 'recharts';