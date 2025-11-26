'use client';

import { Activity, DollarSign, Clock, Zap, TrendingUp, AlertCircle } from 'lucide-react';
import { formatCost, formatLatency, formatNumber } from '@/lib/api';

interface MetricsCardsProps {
  metrics: {
    requests: {
      total: number;
      successful: number;
      failed: number;
    };
    latency_ms: {
      p50: number;
      p95: number;
      average: number;
    };
    costs: {
      total_usd: number;
      average_per_request_usd: number;
    };
    rates: {
      error_rate_percent: number;
    };
  } | null;
  loading: boolean;
}

interface CardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: {
    value: string;
    positive: boolean;
  };
  color: 'blue' | 'green' | 'amber' | 'purple' | 'red';
}

function Card({ title, value, subtitle, icon, trend, color }: CardProps) {
  const colorClasses = {
    blue: 'from-blue-500 to-blue-600 shadow-blue-500/25',
    green: 'from-emerald-500 to-emerald-600 shadow-emerald-500/25',
    amber: 'from-amber-500 to-amber-600 shadow-amber-500/25',
    purple: 'from-purple-500 to-purple-600 shadow-purple-500/25',
    red: 'from-red-500 to-red-600 shadow-red-500/25',
  };

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100 card-hover">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className="text-3xl font-bold text-slate-800 mt-1">{value}</p>
          {subtitle && (
            <p className="text-sm text-slate-400 mt-1">{subtitle}</p>
          )}
          {trend && (
            <div className={`flex items-center gap-1 mt-2 text-sm ${
              trend.positive ? 'text-emerald-600' : 'text-red-600'
            }`}>
              <TrendingUp className={`w-4 h-4 ${!trend.positive && 'rotate-180'}`} />
              <span>{trend.value}</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-xl bg-gradient-to-br ${colorClasses[color]} shadow-lg`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100 animate-pulse">
      <div className="flex items-start justify-between">
        <div className="space-y-3">
          <div className="h-4 w-24 bg-slate-200 rounded" />
          <div className="h-8 w-32 bg-slate-200 rounded" />
          <div className="h-3 w-20 bg-slate-100 rounded" />
        </div>
        <div className="w-12 h-12 bg-slate-200 rounded-xl" />
      </div>
    </div>
  );
}

export default function MetricsCards({ metrics, loading }: MetricsCardsProps) {
  if (loading || !metrics) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <Card
        title="Total Requests"
        value={formatNumber(metrics.requests.total)}
        subtitle={`${metrics.requests.successful} successful`}
        icon={<Activity className="w-6 h-6 text-white" />}
        color="blue"
      />
      <Card
        title="Avg Latency"
        value={formatLatency(metrics.latency_ms.average)}
        subtitle={`P95: ${formatLatency(metrics.latency_ms.p95)}`}
        icon={<Clock className="w-6 h-6 text-white" />}
        color="amber"
      />
      <Card
        title="Total Cost"
        value={formatCost(metrics.costs.total_usd)}
        subtitle={`${formatCost(metrics.costs.average_per_request_usd)}/request`}
        icon={<DollarSign className="w-6 h-6 text-white" />}
        color="green"
      />
      <Card
        title="Error Rate"
        value={`${metrics.rates.error_rate_percent.toFixed(1)}%`}
        subtitle={`${metrics.requests.failed} failed`}
        icon={<AlertCircle className="w-6 h-6 text-white" />}
        color={metrics.rates.error_rate_percent > 5 ? 'red' : 'purple'}
      />
    </div>
  );
}