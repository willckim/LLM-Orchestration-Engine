// API Configuration
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://llm-orchestration-engine.onrender.com';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'dev-key-123';

// Types
export interface GenerateRequest {
  task: 'summarize' | 'sentiment' | 'rewrite' | 'chat' | 'code' | 'analysis';
  model_preference: 'fast' | 'cheap' | 'best' | 'balanced';
  text: string;
  max_tokens?: number;
  temperature?: number;
}

export interface GenerateResponse {
  success: boolean;
  result: string | null;
  error: string | null;
  request_id: string;
  timestamp: string;
  routing: {
    selected_model: string;
    provider: string;
    reason: string;
    alternatives_considered: string[];
    routing_time_ms: number;
    cost_score: number;
    latency_score: number;
    quality_score: number;
    availability_score: number;
    final_score: number;
  };
  usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    input_cost_usd: number;
    output_cost_usd: number;
    total_cost_usd: number;
  };
  performance: {
    total_time_ms: number;
    routing_time_ms: number;
    inference_time_ms: number;
    overhead_time_ms: number;
  };
}

export interface MetricsSummary {
  time_range: {
    start: string;
    end: string;
    hours: number;
  };
  requests: {
    total: number;
    successful: number;
    failed: number;
    cached: number;
    fallbacks: number;
  };
  latency_ms: {
    p50: number;
    p95: number;
    p99: number;
    average: number;
  };
  costs: {
    total_usd: number;
    average_per_request_usd: number;
    by_model: Record<string, number>;
    by_provider: Record<string, number>;
  };
  tokens: {
    total: number;
    by_model: Record<string, number>;
  };
  distribution: {
    by_task: Record<string, number>;
    by_preference: Record<string, number>;
    by_model: Record<string, number>;
  };
  rates: {
    error_rate_percent: number;
    cache_hit_rate_percent: number;
    fallback_rate_percent: number;
  };
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  timestamp: string;
  environment: string;
  providers: Record<string, { status: string; recent_requests: number; error_rate: number }>;
  uptime_seconds: number;
  requests_processed: number;
  error_rate_percent: number;
  available_providers: string[];
}

export interface ModelInfo {
  model: string;
  provider: string;
  tasks: string[];
  max_tokens: number;
  avg_latency_ms: number;
  quality_score: number;
  pricing: {
    input_per_1k_tokens: number;
    output_per_1k_tokens: number;
  };
}

export interface RequestLog {
  request_id: string;
  model: string;
  provider: string;
  task: string;
  preference: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  total_time_ms: number;
  success: boolean;
  error: string | null;
  timestamp: string;
}

// API Functions
async function fetchAPI<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

// Health & Status
export async function getHealth(): Promise<HealthResponse> {
  return fetchAPI<HealthResponse>('/health/detailed');
}

export async function getBasicHealth(): Promise<{ status: string; timestamp: string }> {
  return fetchAPI('/health');
}

// Generation
export async function generate(request: GenerateRequest): Promise<GenerateResponse> {
  return fetchAPI<GenerateResponse>('/api/v1/generate', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// Metrics
export async function getMetricsSummary(hours: number = 24): Promise<MetricsSummary> {
  return fetchAPI<MetricsSummary>(`/api/v1/metrics/summary?hours=${hours}`);
}

export async function getRealtimeStats(): Promise<{
  last_minute: { requests: number; errors: number; avg_latency_ms: number };
  last_hour: { requests: number; errors: number; avg_latency_ms: number; cost_usd: number };
  uptime_seconds: number;
  total_requests: number;
  provider_health: Record<string, any>;
}> {
  return fetchAPI('/api/v1/metrics/realtime');
}

export async function getRequestLogs(limit: number = 50): Promise<{ logs: RequestLog[]; total: number }> {
  return fetchAPI(`/api/v1/metrics/logs?limit=${limit}`);
}

// Models
export async function getModels(): Promise<{ models: ModelInfo[]; total: number }> {
  return fetchAPI('/api/v1/models');
}

// Cost Estimation
export async function estimateCost(request: GenerateRequest): Promise<{
  selected_model: string;
  estimated_cost_usd: number;
  routing_decision: any;
  cost_comparison: any[];
}> {
  return fetchAPI('/api/v1/estimate', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// Clear all metrics and logs
export async function clearMetrics(): Promise<{ success: boolean; message: string }> {
  return fetchAPI('/api/v1/metrics/clear', {
    method: 'DELETE',
  });
}

// Utility: Format cost
export function formatCost(cost: number): string {
  if (cost < 0.0001) {
    return '<$0.0001';
  }
  if (cost < 0.01) {
    return `$${cost.toFixed(4)}`;
  }
  return `$${cost.toFixed(2)}`;
}

// Utility: Format latency
export function formatLatency(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  return `${(ms / 1000).toFixed(2)}s`;
}

// Utility: Format number with K/M suffix
export function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
}

// Utility: Get provider color
export function getProviderColor(provider: string): string {
  const colors: Record<string, string> = {
    openai: '#10a37f',
    anthropic: '#d4a574',
    azure: '#0078d4',
    bedrock: '#ff9900',
    mock: '#6b7280',
    local: '#8b5cf6',
  };
  return colors[provider.toLowerCase()] || '#6b7280';
}

// Utility: Get model color for charts
export function getModelColor(model: string, index: number): string {
  const colors = [
    '#0ea5e9', // sky-500
    '#8b5cf6', // violet-500
    '#10b981', // emerald-500
    '#f59e0b', // amber-500
    '#ef4444', // red-500
    '#ec4899', // pink-500
    '#6366f1', // indigo-500
    '#14b8a6', // teal-500
  ];
  return colors[index % colors.length];
}