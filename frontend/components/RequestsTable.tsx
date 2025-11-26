'use client';

import { CheckCircle, XCircle, Clock, Coins } from 'lucide-react';
import { formatCost, formatLatency, getProviderColor, RequestLog } from '@/lib/api';

interface RequestsTableProps {
  logs: RequestLog[];
  loading: boolean;
}

export default function RequestsTable({ logs, loading }: RequestsTableProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-6 border-b border-slate-100">
          <div className="h-6 w-40 bg-slate-200 rounded animate-pulse" />
        </div>
        <div className="p-4 space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center gap-4 p-3">
              <div className="w-8 h-8 bg-slate-100 rounded-full animate-pulse" />
              <div className="flex-1 space-y-2">
                <div className="h-4 w-32 bg-slate-200 rounded animate-pulse" />
                <div className="h-3 w-24 bg-slate-100 rounded animate-pulse" />
              </div>
              <div className="h-4 w-16 bg-slate-100 rounded animate-pulse" />
              <div className="h-4 w-16 bg-slate-100 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-6 border-b border-slate-100">
          <h3 className="text-lg font-semibold text-slate-800">Recent Requests</h3>
        </div>
        <div className="p-12 text-center text-slate-400">
          <Clock className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No requests yet. Try the demo below!</p>
        </div>
      </div>
    );
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      <div className="p-6 border-b border-slate-100 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-800">Recent Requests</h3>
        <span className="text-sm text-slate-400">{logs.length} requests</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50">
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                Model
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                Task
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                Latency
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                Cost
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                Tokens
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                Time
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {logs.map((log, index) => (
              <tr
                key={log.request_id || index}
                className="hover:bg-slate-50 transition-colors animate-fade-in"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  {log.success ? (
                    <CheckCircle className="w-5 h-5 text-emerald-500" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-500" />
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: getProviderColor(log.provider) }}
                    />
                    <span className="text-sm font-medium text-slate-700">
                      {log.model?.split('/').pop() || log.model}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 capitalize">
                    {log.task}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-1 text-sm text-slate-600">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    {formatLatency(log.total_time_ms)}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-1 text-sm text-slate-600">
                    <Coins className="w-3.5 h-3.5 text-slate-400" />
                    {formatCost(log.cost_usd)}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                  {log.input_tokens + log.output_tokens}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                  {formatTime(log.timestamp)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}