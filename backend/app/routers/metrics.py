"""
LLM Orchestration Engine - Metrics Router
Observability and analytics endpoints
"""

from datetime import datetime, timedelta
from typing import Optional, Literal

from fastapi import APIRouter, Depends, Query, Header, HTTPException

from app.config import get_settings
from app.services import get_metrics_collector, get_cost_calculator
from app.db.local_storage import get_local_storage


router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key from header"""
    settings = get_settings()
    
    if settings.environment == "development" and not x_api_key:
        return "dev-anonymous"
    
    if not x_api_key or x_api_key not in settings.valid_api_keys:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    return x_api_key


@router.get(
    "/summary",
    summary="Metrics Summary",
    description="Get aggregated metrics summary for dashboard"
)
async def get_metrics_summary(
    hours: int = Query(default=24, ge=1, le=168, description="Hours to aggregate"),
    api_key: str = Depends(verify_api_key),
):
    """Get aggregated metrics for the specified time period"""
    metrics = get_metrics_collector()
    cost_calc = get_cost_calculator()
    
    start_time = datetime.utcnow() - timedelta(hours=hours)
    agg = metrics.aggregate(start_time=start_time)
    
    return {
        "time_range": {
            "start": agg.start_time.isoformat(),
            "end": agg.end_time.isoformat(),
            "hours": hours,
        },
        "requests": {
            "total": agg.total_requests,
            "successful": agg.successful_requests,
            "failed": agg.failed_requests,
            "cached": agg.cached_requests,
            "fallbacks": agg.fallback_requests,
        },
        "latency_ms": {
            "p50": round(agg.p50_latency_ms, 2),
            "p95": round(agg.p95_latency_ms, 2),
            "p99": round(agg.p99_latency_ms, 2),
            "average": round(agg.average_latency_ms, 2),
        },
        "costs": {
            "total_usd": round(agg.total_cost_usd, 6),
            "average_per_request_usd": round(agg.average_cost_per_request_usd, 6),
            "by_model": {k: round(v, 6) for k, v in agg.cost_by_model.items()},
            "by_provider": {k: round(v, 6) for k, v in agg.cost_by_provider.items()},
        },
        "tokens": {
            "total": agg.total_tokens,
            "by_model": agg.tokens_by_model,
        },
        "distribution": {
            "by_task": agg.requests_by_task,
            "by_preference": agg.requests_by_preference,
            "by_model": agg.requests_by_model,
        },
        "rates": {
            "error_rate_percent": round(agg.error_rate_percent, 2),
            "cache_hit_rate_percent": round(agg.cache_hit_rate_percent, 2),
            "fallback_rate_percent": round(agg.fallback_rate_percent, 2),
        },
    }


@router.get(
    "/models/{model}",
    summary="Model Performance",
    description="Get performance metrics for a specific model"
)
async def get_model_metrics(
    model: str,
    api_key: str = Depends(verify_api_key),
):
    """Get detailed metrics for a specific model"""
    metrics = get_metrics_collector()
    return metrics.get_model_performance(model)


@router.get(
    "/providers",
    summary="Provider Health",
    description="Get health status of all providers"
)
async def get_provider_health(
    api_key: str = Depends(verify_api_key),
):
    """Get health status for all providers"""
    metrics = get_metrics_collector()
    return {
        "providers": metrics.get_provider_health(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/costs",
    summary="Cost Analysis",
    description="Get detailed cost breakdown"
)
async def get_cost_analysis(
    api_key: str = Depends(verify_api_key),
):
    """Get cost analysis and comparison"""
    cost_calc = get_cost_calculator()
    metrics = get_metrics_collector()
    
    summary = cost_calc.get_cost_summary()
    agg = metrics.aggregate()
    
    return {
        "total_cost_usd": round(summary["total_cost_usd"], 6),
        "cost_by_model": {k: round(v, 6) for k, v in summary["cost_by_model"].items()},
        "cost_by_provider": {k: round(v, 6) for k, v in summary["cost_by_provider"].items()},
        "average_cost_per_request": round(agg.average_cost_per_request_usd, 6),
        "tokens_processed": agg.total_tokens,
        "cost_per_1k_tokens": round(
            (summary["total_cost_usd"] / agg.total_tokens * 1000) if agg.total_tokens > 0 else 0, 
            6
        ),
    }


@router.get(
    "/logs",
    summary="Request Logs",
    description="Get recent request logs"
)
async def get_request_logs(
    limit: int = Query(default=50, ge=1, le=500),
    model: Optional[str] = Query(default=None),
    success_only: bool = Query(default=False),
    api_key: str = Depends(verify_api_key),
):
    """Get recent request logs"""
    storage = get_local_storage()
    logs = storage.get_logs(limit=limit, model=model)
    
    if success_only:
        logs = [l for l in logs if l.get("success", False)]
    
    return {
        "logs": logs,
        "total": len(logs),
    }


@router.get(
    "/realtime",
    summary="Real-time Stats",
    description="Get real-time statistics for dashboard"
)
async def get_realtime_stats(
    api_key: str = Depends(verify_api_key),
):
    """Get real-time stats for live dashboard"""
    metrics = get_metrics_collector()
    
    # Last minute stats
    one_min_ago = datetime.utcnow() - timedelta(minutes=1)
    recent = metrics.aggregate(start_time=one_min_ago)
    
    # Last hour stats
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    hourly = metrics.aggregate(start_time=one_hour_ago)
    
    return {
        "last_minute": {
            "requests": recent.total_requests,
            "errors": recent.failed_requests,
            "avg_latency_ms": round(recent.average_latency_ms, 2),
        },
        "last_hour": {
            "requests": hourly.total_requests,
            "errors": hourly.failed_requests,
            "avg_latency_ms": round(hourly.average_latency_ms, 2),
            "cost_usd": round(hourly.total_cost_usd, 6),
        },
        "uptime_seconds": metrics.uptime_seconds,
        "total_requests": metrics.total_requests_processed,
        "provider_health": metrics.get_provider_health(),
    }


@router.get(
    "/export",
    summary="Export Metrics",
    description="Export metrics in various formats"
)
async def export_metrics(
    format: Literal["json", "cloudwatch"] = Query(default="json"),
    hours: int = Query(default=24, ge=1, le=168),
    api_key: str = Depends(verify_api_key),
):
    """Export metrics for external systems"""
    metrics = get_metrics_collector()
    
    if format == "cloudwatch":
        return {
            "Namespace": "LLMOrchestration",
            "MetricData": metrics.to_cloudwatch_format(),
        }
    
    # Default JSON format
    start_time = datetime.utcnow() - timedelta(hours=hours)
    return {
        "exported_at": datetime.utcnow().isoformat(),
        "metrics": metrics.aggregate(start_time=start_time).__dict__,
    }


@router.delete(
    "/clear",
    summary="Clear All Metrics",
    description="Clear all metrics, logs, and request history"
)
async def clear_metrics(
    api_key: str = Depends(verify_api_key),
):
    """Clear all stored metrics and logs"""
    from app.services import get_router
    
    # Clear metrics collector
    metrics = get_metrics_collector()
    metrics.clear()
    
    # Clear cost calculator
    cost_calc = get_cost_calculator()
    cost_calc._total_cost_usd = 0.0
    cost_calc._cost_by_model = {}
    cost_calc._cost_by_provider = {}
    
    # Clear router's internal metrics
    router_service = get_router()
    router_service._model_metrics = {}
    router_service._provider_health = {}
    
    # Clear local storage
    storage = get_local_storage()
    storage.clear()
    
    return {
        "success": True,
        "message": "All metrics and logs cleared",
        "timestamp": datetime.utcnow().isoformat(),
    }