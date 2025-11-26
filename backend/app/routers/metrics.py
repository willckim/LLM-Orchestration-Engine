"""
LLM Orchestration Engine - Metrics Router
"""

from datetime import datetime, timedelta
from typing import Optional, Literal

from fastapi import APIRouter, Depends, Query, Header, HTTPException

from app.config import get_settings
from app.services import get_metrics_collector, get_cost_calculator
from app.db.local_storage import get_local_storage


router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    settings = get_settings()
    if settings.environment == "development" and not x_api_key:
        return "dev-anonymous"
    if not x_api_key or x_api_key not in settings.valid_api_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@router.get("/summary", summary="Metrics Summary")
async def get_metrics_summary(
    hours: int = Query(default=24, ge=1, le=168),
    api_key: str = Depends(verify_api_key),
):
    metrics = get_metrics_collector()
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


@router.get("/logs", summary="Request Logs")
async def get_request_logs(
    limit: int = Query(default=50, ge=1, le=500),
    api_key: str = Depends(verify_api_key),
):
    storage = get_local_storage()
    logs = storage.get_logs(limit=limit)
    return {"logs": logs, "total": len(logs)}


@router.get("/realtime", summary="Real-time Stats")
async def get_realtime_stats(api_key: str = Depends(verify_api_key)):
    metrics = get_metrics_collector()
    
    one_min_ago = datetime.utcnow() - timedelta(minutes=1)
    recent = metrics.aggregate(start_time=one_min_ago)
    
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