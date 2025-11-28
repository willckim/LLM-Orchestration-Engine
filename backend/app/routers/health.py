"""
LLM Orchestration Engine - Health Router
Health checks and status endpoints
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter

from app.config import get_settings
from app.services import get_metrics_collector
from app.services.providers import get_litellm_provider, get_mock_provider


router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Health Check",
    description="Basic health check endpoint"
)
async def health_check():
    """Simple health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/health/detailed",
    summary="Detailed Health Check",
    description="Detailed health check including provider status"
)
async def detailed_health_check():
    """Detailed health check with provider status"""
    settings = get_settings()
    metrics = get_metrics_collector()
    
    # Check provider health
    providers_health = metrics.get_provider_health()
    
    # Determine overall status
    if not providers_health:
        overall_status = "healthy"  # No requests yet
    else:
        unhealthy_count = sum(
            1 for p in providers_health.values() 
            if p.get("status") == "unhealthy"
        )
        degraded_count = sum(
            1 for p in providers_health.values() 
            if p.get("status") == "degraded"
        )
        
        if unhealthy_count > len(providers_health) / 2:
            overall_status = "unhealthy"
        elif unhealthy_count > 0 or degraded_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
    
    # Get aggregate error rate
    agg = metrics.aggregate()
    
    return {
        "status": overall_status,
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.environment,
        "providers": providers_health,
        "uptime_seconds": metrics.uptime_seconds,
        "requests_processed": metrics.total_requests_processed,
        "error_rate_percent": agg.error_rate_percent,
        "available_providers": settings.available_providers,
    }


@router.get(
    "/ready",
    summary="Readiness Check",
    description="Kubernetes-style readiness probe"
)
async def readiness_check():
    """Readiness probe for Kubernetes"""
    settings = get_settings()
    
    # Check if at least one provider is available
    providers = settings.available_providers
    
    if not providers or providers == ["mock"]:
        # Only mock available - still ready but limited
        return {
            "ready": True,
            "mode": "mock-only",
            "message": "Running in mock mode. Configure API keys for production.",
        }
    
    return {
        "ready": True,
        "mode": "production",
        "providers": providers,
    }


@router.get(
    "/live",
    summary="Liveness Check",
    description="Kubernetes-style liveness probe"
)
async def liveness_check():
    """Liveness probe for Kubernetes"""
    return {"alive": True}


@router.get(
    "/providers",
    summary="Check Configured Providers",
    description="Debug endpoint to verify which AI providers have API keys configured"
)
async def check_providers():
    """Debug endpoint to check which providers are configured"""
    settings = get_settings()
    
    return {
        "configured_providers": {
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key),
            "gemini": bool(settings.gemini_api_key),
            "azure": bool(settings.azure_openai_api_key and settings.azure_openai_endpoint),
            "bedrock": bool(settings.aws_access_key_id and settings.aws_secret_access_key),
        },
        "available_providers": settings.available_providers,
        "environment": settings.environment,
        "local_models_enabled": settings.enable_local_models,
        # Show first 8 chars of keys (for debugging, never show full keys)
        "key_prefixes": {
            "openai": settings.openai_api_key[:8] + "..." if settings.openai_api_key else None,
            "anthropic": settings.anthropic_api_key[:8] + "..." if settings.anthropic_api_key else None,
            "gemini": settings.gemini_api_key[:8] + "..." if settings.gemini_api_key else None,
        }
    }