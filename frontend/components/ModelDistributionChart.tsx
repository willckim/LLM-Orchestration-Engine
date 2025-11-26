'use client';

import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { getModelColor } from '@/lib/api';

interface ModelDistributionChartProps {
  data: Record<string, number>;
  loading: boolean;
}

export default function ModelDistributionChart({ data, loading }: ModelDistributionChartProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <div className="h-5 w-40 bg-slate-200 rounded animate-pulse mb-6" />
        <div className="h-64 flex items-center justify-center">
          <div className="w-48 h-48 rounded-full bg-slate-100 animate-pulse" />
        </div>
      </div>
    );
  }

  const chartData = Object.entries(data).map(([name, value], index) => ({
    name: name.split('/').pop() || name, // Simplify model names
    fullName: name,
    value,
    color: getModelColor(name, index),
  }));

  if (chartData.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Model Distribution</h3>
        <div className="h-64 flex items-center justify-center text-slate-400">
          No data available yet
        </div>
      </div>
    );
  }

  const total = chartData.reduce((sum, item) => sum + item.value, 0);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const percentage = ((data.value / total) * 100).toFixed(1);
      return (
        <div className="bg-white px-4 py-3 rounded-xl shadow-lg border border-slate-100">
          <p className="font-medium text-slate-800">{data.fullName}</p>
          <p className="text-sm text-slate-500">
            {data.value} requests ({percentage}%)
          </p>
        </div>
      );
    }
    return null;
  };

  const CustomLegend = ({ payload }: any) => (
    <div className="flex flex-wrap justify-center gap-4 mt-4">
      {payload.map((entry: any, index: number) => (
        <div key={index} className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-sm text-slate-600">{entry.value}</span>
        </div>
      ))}
    </div>
  );

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
      <h3 className="text-lg font-semibold text-slate-800 mb-4">Model Distribution</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={90}
              paddingAngle={2}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend content={<CustomLegend />} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}