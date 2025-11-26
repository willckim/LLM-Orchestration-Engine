"""
LLM Orchestration Engine - Health Router
Health checks and status endpoints
"""

from datetime import datetime
from fastapi import APIRouter
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health Check")
async def health_check():
    """Simple health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/detailed", summary="Detailed Health Check")
async def detailed_health_check():
    """Detailed health check with provider status"""
    settings = get_settings()
    
    return {
        "status": "healthy",
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.environment,
        "providers": {},
        "uptime_seconds": 0,
        "requests_processed": 0,
        "error_rate_percent": 0,
        "available_providers": settings.available_providers,
    }


@router.get("/ready", summary="Readiness Check")
async def readiness_check():
    """Readiness probe for Kubernetes"""
    settings = get_settings()
    providers = settings.available_providers
    
    return {
        "ready": True,
        "mode": "production" if len(providers) > 1 else "mock-only",
        "providers": providers,
    }


@router.get("/live", summary="Liveness Check")
async def liveness_check():
    """Liveness probe for Kubernetes"""
    return {"alive": True}