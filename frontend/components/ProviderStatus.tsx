'use client';

import { Server, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { getProviderColor } from '@/lib/api';

interface ProviderHealth {
  status: string;
  recent_requests: number;
  error_rate: number;
  avg_latency_ms?: number;
}

interface ProviderStatusProps {
  providers: Record<string, ProviderHealth>;
  loading: boolean;
}

export default function ProviderStatus({ providers, loading }: ProviderStatusProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <div className="h-5 w-40 bg-slate-200 rounded animate-pulse mb-4" />
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl animate-pulse">
              <div className="w-10 h-10 bg-slate-200 rounded-lg" />
              <div className="flex-1">
                <div className="h-4 w-20 bg-slate-200 rounded mb-1" />
                <div className="h-3 w-32 bg-slate-100 rounded" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const providerList = Object.entries(providers);

  if (providerList.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Provider Status</h3>
        <div className="text-center py-8 text-slate-400">
          <Server className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No provider data available</p>
        </div>
      </div>
    );
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-emerald-500" />;
      case 'degraded':
        return <AlertTriangle className="w-5 h-5 text-amber-500" />;
      case 'unhealthy':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Server className="w-5 h-5 text-slate-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const classes = {
      healthy: 'bg-emerald-100 text-emerald-700',
      degraded: 'bg-amber-100 text-amber-700',
      unhealthy: 'bg-red-100 text-red-700',
      unknown: 'bg-slate-100 text-slate-600',
    };
    return classes[status as keyof typeof classes] || classes.unknown;
  };

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
      <h3 className="text-lg font-semibold text-slate-800 mb-4">Provider Status</h3>
      <div className="space-y-3">
        {providerList.map(([name, health]) => (
          <div
            key={name}
            className="flex items-center gap-4 p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors"
          >
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: `${getProviderColor(name)}20` }}
            >
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: getProviderColor(name) }}
              />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-slate-800 capitalize">{name}</span>
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getStatusBadge(health.status)}`}>
                  {health.status}
                </span>
              </div>
              <div className="flex items-center gap-4 mt-1 text-sm text-slate-500">
                <span>{health.recent_requests} recent requests</span>
                {health.error_rate !== undefined && (
                  <span>{(health.error_rate * 100).toFixed(1)}% errors</span>
                )}
                {health.avg_latency_ms !== undefined && (
                  <span>{Math.round(health.avg_latency_ms)}ms avg</span>
                )}
              </div>
            </div>
            {getStatusIcon(health.status)}
          </div>
        ))}
      </div>
    </div>
  );
}