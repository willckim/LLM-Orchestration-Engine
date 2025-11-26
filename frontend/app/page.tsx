'use client';

import { useState, useEffect, useCallback } from 'react';
import Header from '@/components/Header';
import MetricsCards from '@/components/MetricsCards';
import ModelDistributionChart from '@/components/ModelDistributionChart';
import CostBreakdownChart from '@/components/CostBreakdownChart';
import RequestsTable from '@/components/RequestsTable';
import TryItDemo from '@/components/TryItDemo';
import ProviderStatus from '@/components/ProviderStatus';
import { 
  getMetricsSummary, 
  getRequestLogs, 
  getRealtimeStats,
  MetricsSummary, 
  RequestLog 
} from '@/lib/api';
import { RefreshCw, ExternalLink } from 'lucide-react';

export default function Dashboard() {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [logs, setLogs] = useState<RequestLog[]>([]);
  const [providerHealth, setProviderHealth] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [metricsData, logsData, realtimeData] = await Promise.all([
        getMetricsSummary(24).catch(() => null),
        getRequestLogs(20).catch(() => ({ logs: [] })),
        getRealtimeStats().catch(() => ({ provider_health: {} })),
      ]);

      if (metricsData) setMetrics(metricsData);
      setLogs(logsData.logs || []);
      setProviderHealth(realtimeData.provider_health || {});
      setLastUpdated(new Date());
    } catch (err) {
      setError('Unable to connect to API. Make sure the backend is running.');
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRefresh = () => {
    setLoading(true);
    fetchData();
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h2 className="text-2xl font-bold text-slate-800">Dashboard</h2>
            <p className="text-slate-500 mt-1">
              Real-time monitoring and analytics
            </p>
          </div>
          <div className="flex items-center gap-4">
            {lastUpdated && (
              <span className="text-sm text-slate-400">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50 transition-all shadow-sm"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-xl text-sm font-medium hover:bg-primary-600 transition-all shadow-sm"
            >
              <ExternalLink className="w-4 h-4" />
              API Docs
            </a>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-8 p-4 bg-amber-50 border border-amber-200 rounded-xl">
            <div className="flex items-start gap-3">
              <div className="p-1 bg-amber-100 rounded-lg">
                <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div>
                <h4 className="font-medium text-amber-800">Connection Issue</h4>
                <p className="text-sm text-amber-700 mt-1">{error}</p>
                <p className="text-sm text-amber-600 mt-2">
                  Run <code className="px-2 py-0.5 bg-amber-100 rounded">make dev</code> in the backend directory to start the API server.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Metrics Cards */}
        <section className="mb-8">
          <MetricsCards metrics={metrics} loading={loading} />
        </section>

        {/* Charts Row */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <ModelDistributionChart 
            data={metrics?.distribution?.by_model || {}} 
            loading={loading} 
          />
          <CostBreakdownChart 
            data={metrics?.costs?.by_model || {}} 
            loading={loading} 
          />
        </section>

        {/* Demo + Provider Status Row */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-2">
            <TryItDemo onRequestComplete={fetchData} />
          </div>
          <div>
            <ProviderStatus providers={providerHealth} loading={loading} />
          </div>
        </section>

        {/* Requests Table */}
        <section className="mb-8">
          <RequestsTable logs={logs} loading={loading} />
        </section>

        {/* Footer */}
        <footer className="text-center py-8 border-t border-slate-200">
          <p className="text-sm text-slate-400">
            LLM Orchestration Engine • Built with FastAPI + Next.js • 
            <a 
              href="https://github.com/yourusername/llm-orchestration-engine" 
              className="text-primary-500 hover:text-primary-600 ml-1"
              target="_blank"
              rel="noopener noreferrer"
            >
              View on GitHub
            </a>
          </p>
        </footer>
      </main>
    </div>
  );
}