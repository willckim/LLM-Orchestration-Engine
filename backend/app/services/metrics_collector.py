"""
LLM Orchestration Engine - Metrics Collector
Collects, stores, and exposes metrics for observability
"""

import time
import statistics
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json


@dataclass
class RequestMetric:
    """Single request metric"""
    timestamp: datetime
    request_id: str
    model: str
    provider: str
    task: str
    preference: str
    
    # Performance
    total_time_ms: float
    routing_time_ms: float
    inference_time_ms: float
    
    # Usage
    input_tokens: int
    output_tokens: int
    cost_usd: float
    
    # Status
    success: bool
    cached: bool
    fallback_used: bool
    error: Optional[str] = None
    
    # Client info
    user_agent: Optional[str] = None


@dataclass
class AggregatedMetrics:
    """Aggregated metrics over a time period"""
    start_time: datetime
    end_time: datetime
    
    # Request counts
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cached_requests: int = 0
    fallback_requests: int = 0
    
    # Latency (ms)
    latencies: list = field(default_factory=list)
    
    # Costs
    total_cost_usd: float = 0.0
    cost_by_model: dict = field(default_factory=dict)
    cost_by_provider: dict = field(default_factory=dict)
    
    # Usage
    total_tokens: int = 0
    tokens_by_model: dict = field(default_factory=dict)
    
    # Breakdowns
    requests_by_task: dict = field(default_factory=dict)
    requests_by_preference: dict = field(default_factory=dict)
    requests_by_model: dict = field(default_factory=dict)
    
    @property
    def p50_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        return statistics.median(self.latencies)
    
    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        return statistics.quantiles(self.latencies, n=20)[18] if len(self.latencies) >= 20 else max(self.latencies)
    
    @property
    def p99_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        return statistics.quantiles(self.latencies, n=100)[98] if len(self.latencies) >= 100 else max(self.latencies)
    
    @property
    def average_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        return statistics.mean(self.latencies)
    
    @property
    def error_rate_percent(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100
    
    @property
    def cache_hit_rate_percent(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.cached_requests / self.total_requests) * 100
    
    @property
    def fallback_rate_percent(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.fallback_requests / self.total_requests) * 100
    
    @property
    def average_cost_per_request_usd(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_cost_usd / self.total_requests


class MetricsCollector:
    """
    Collects and aggregates metrics for observability
    In production, this would integrate with CloudWatch/DynamoDB
    """
    
    def __init__(self, retention_hours: int = 24 * 7):
        self.retention_hours = retention_hours
        self._metrics: list[RequestMetric] = []
        self._start_time = datetime.utcnow()
        self._request_count = 0
    
    def record(self, metric: RequestMetric):
        """Record a new metric"""
        self._metrics.append(metric)
        self._request_count += 1
        
        # Cleanup old metrics
        self._cleanup_old_metrics()
    
    def clear(self):
        """Clear all metrics"""
        self._metrics = []
        self._request_count = 0
        self._start_time = datetime.utcnow()
    
    def _cleanup_old_metrics(self):
        """Remove metrics older than retention period"""
        cutoff = datetime.utcnow() - timedelta(hours=self.retention_hours)
        self._metrics = [m for m in self._metrics if m.timestamp > cutoff]
    
    def get_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        model: Optional[str] = None,
        task: Optional[str] = None,
    ) -> list[RequestMetric]:
        """Get filtered metrics"""
        metrics = self._metrics
        
        if start_time:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        if end_time:
            metrics = [m for m in metrics if m.timestamp <= end_time]
        if model:
            metrics = [m for m in metrics if m.model == model]
        if task:
            metrics = [m for m in metrics if m.task == task]
        
        return metrics
    
    def aggregate(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> AggregatedMetrics:
        """Aggregate metrics over a time period"""
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(hours=1)
        if end_time is None:
            end_time = datetime.utcnow()
        
        metrics = self.get_metrics(start_time=start_time, end_time=end_time)
        
        agg = AggregatedMetrics(start_time=start_time, end_time=end_time)
        
        for m in metrics:
            agg.total_requests += 1
            
            if m.success:
                agg.successful_requests += 1
            else:
                agg.failed_requests += 1
            
            if m.cached:
                agg.cached_requests += 1
            
            if m.fallback_used:
                agg.fallback_requests += 1
            
            agg.latencies.append(m.total_time_ms)
            agg.total_cost_usd += m.cost_usd
            agg.total_tokens += m.input_tokens + m.output_tokens
            
            # By model
            if m.model not in agg.cost_by_model:
                agg.cost_by_model[m.model] = 0.0
                agg.tokens_by_model[m.model] = 0
                agg.requests_by_model[m.model] = 0
            agg.cost_by_model[m.model] += m.cost_usd
            agg.tokens_by_model[m.model] += m.input_tokens + m.output_tokens
            agg.requests_by_model[m.model] += 1
            
            # By provider
            if m.provider not in agg.cost_by_provider:
                agg.cost_by_provider[m.provider] = 0.0
            agg.cost_by_provider[m.provider] += m.cost_usd
            
            # By task
            if m.task not in agg.requests_by_task:
                agg.requests_by_task[m.task] = 0
            agg.requests_by_task[m.task] += 1
            
            # By preference
            if m.preference not in agg.requests_by_preference:
                agg.requests_by_preference[m.preference] = 0
            agg.requests_by_preference[m.preference] += 1
        
        return agg
    
    def get_model_performance(self, model: str) -> dict:
        """Get performance metrics for a specific model"""
        metrics = [m for m in self._metrics if m.model == model]
        
        if not metrics:
            return {"model": model, "error": "No data available"}
        
        latencies = [m.total_time_ms for m in metrics]
        successes = sum(1 for m in metrics if m.success)
        
        return {
            "model": model,
            "total_requests": len(metrics),
            "success_rate": successes / len(metrics),
            "avg_latency_ms": statistics.mean(latencies),
            "p95_latency_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
            "total_cost_usd": sum(m.cost_usd for m in metrics),
            "avg_tokens": statistics.mean(m.input_tokens + m.output_tokens for m in metrics),
        }
    
    def get_provider_health(self) -> dict[str, dict]:
        """Get health status for each provider"""
        # Group by provider
        by_provider = defaultdict(list)
        for m in self._metrics:
            by_provider[m.provider].append(m)
        
        health = {}
        for provider, metrics in by_provider.items():
            recent = [m for m in metrics if m.timestamp > datetime.utcnow() - timedelta(minutes=5)]
            
            if not recent:
                health[provider] = {
                    "status": "unknown",
                    "recent_requests": 0,
                    "error_rate": 0.0,
                }
            else:
                errors = sum(1 for m in recent if not m.success)
                error_rate = errors / len(recent)
                
                health[provider] = {
                    "status": "healthy" if error_rate < 0.1 else "degraded" if error_rate < 0.5 else "unhealthy",
                    "recent_requests": len(recent),
                    "error_rate": error_rate,
                    "avg_latency_ms": statistics.mean(m.total_time_ms for m in recent),
                }
        
        return health
    
    @property
    def uptime_seconds(self) -> float:
        """Get service uptime"""
        return (datetime.utcnow() - self._start_time).total_seconds()
    
    @property
    def total_requests_processed(self) -> int:
        """Get total requests processed"""
        return self._request_count
    
    def to_cloudwatch_format(self) -> list[dict]:
        """Export metrics in CloudWatch-compatible format"""
        agg = self.aggregate()
        
        metrics = [
            {
                "MetricName": "RequestCount",
                "Value": agg.total_requests,
                "Unit": "Count",
            },
            {
                "MetricName": "SuccessRate",
                "Value": (agg.successful_requests / agg.total_requests * 100) if agg.total_requests > 0 else 0,
                "Unit": "Percent",
            },
            {
                "MetricName": "P50Latency",
                "Value": agg.p50_latency_ms,
                "Unit": "Milliseconds",
            },
            {
                "MetricName": "P99Latency",
                "Value": agg.p99_latency_ms,
                "Unit": "Milliseconds",
            },
            {
                "MetricName": "TotalCost",
                "Value": agg.total_cost_usd,
                "Unit": "None",  # USD
            },
        ]
        
        return metrics


# Singleton
_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create metrics collector instance"""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector