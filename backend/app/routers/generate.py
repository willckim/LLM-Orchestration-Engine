"""
LLM Orchestration Engine - Generate Router
Main API endpoint for LLM generation requests
"""

import time
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header, Request

from app.config import get_settings, MODEL_PRICING, MODEL_CAPABILITIES
from app.models import (
    GenerateRequest,
    GenerateResponse,
    RoutingDecision,
    UsageMetrics,
    PerformanceMetrics,
)
from app.services import get_router, get_cost_calculator, get_metrics_collector, RequestMetric
from app.db.local_storage import get_local_storage


router = APIRouter(prefix="/api/v1", tags=["generation"])


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key from header"""
    settings = get_settings()
    
    if settings.environment == "development" and not x_api_key:
        return "dev-anonymous"
    
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    if x_api_key not in settings.valid_api_keys:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return x_api_key


@router.post("/generate", response_model=GenerateResponse, summary="Generate LLM Response")
async def generate(
    request: GenerateRequest,
    http_request: Request,
    api_key: str = Depends(verify_api_key),
):
    """Generate a response using the optimal LLM model."""
    start_time = time.perf_counter()
    request_id = request.request_id or f"req_{uuid.uuid4().hex[:12]}"
    
    model_router = get_router()
    cost_calculator = get_cost_calculator()
    metrics_collector = get_metrics_collector()
    storage = get_local_storage()
    
    try:
        selected_model, routing_decision = await model_router.select_model(request)
        routing_time = time.perf_counter()
        
        provider_response = await model_router.execute_request(
            request=request,
            model=selected_model,
            routing_decision=routing_decision,
        )
        
        inference_time = time.perf_counter()

        # --- BUG FIX START ---
        # Update routing decision if the actual model used differs from the initial selection
        # This handles cases where fallbacks occurred inside execute_request
        fallback_occurred = provider_response.model_used != selected_model
        if fallback_occurred:
            # We assume RoutingDecision has a 'model' field. 
            # If it's a Pydantic model, we use model_copy or direct assignment depending on config
            if hasattr(routing_decision, "model"):
                # specific to Pydantic v1/v2 compatibility, simplified assignment here
                routing_decision.model = provider_response.model_used
                if hasattr(routing_decision, "reasoning"):
                    routing_decision.reasoning += f" (Fallback triggered. Used: {provider_response.model_used})"
        # --- BUG FIX END ---
        
        cost_breakdown = cost_calculator.calculate_cost(
            model=provider_response.model_used,
            input_tokens=provider_response.input_tokens,
            output_tokens=provider_response.output_tokens,
        )
        
        total_time_ms = (time.perf_counter() - start_time) * 1000
        routing_time_ms = (routing_time - start_time) * 1000
        inference_time_ms = (inference_time - routing_time) * 1000
        
        usage = UsageMetrics(
            input_tokens=provider_response.input_tokens,
            output_tokens=provider_response.output_tokens,
            total_tokens=provider_response.total_tokens,
            input_cost_usd=cost_breakdown.input_cost_usd,
            output_cost_usd=cost_breakdown.output_cost_usd,
            total_cost_usd=cost_breakdown.total_cost_usd,
        )
        
        performance = PerformanceMetrics(
            total_time_ms=total_time_ms,
            routing_time_ms=routing_time_ms,
            inference_time_ms=inference_time_ms,
            overhead_time_ms=total_time_ms - routing_time_ms - inference_time_ms,
            provider_latency_ms=provider_response.latency_ms,
        )
        
        response = GenerateResponse(
            success=provider_response.success,
            result=provider_response.content,
            error=provider_response.error,
            request_id=request_id,
            timestamp=datetime.utcnow(),
            routing=routing_decision,
            usage=usage,
            performance=performance,
            cached=False,
            retries=0,
            fallback_used=fallback_occurred,
        )
        
        # Record metrics
        metric = RequestMetric(
            timestamp=datetime.utcnow(),
            request_id=request_id,
            model=provider_response.model_used,
            provider=provider_response.provider,
            task=request.task.value,
            preference=request.model_preference.value,
            total_time_ms=total_time_ms,
            routing_time_ms=routing_time_ms,
            inference_time_ms=inference_time_ms,
            input_tokens=provider_response.input_tokens,
            output_tokens=provider_response.output_tokens,
            cost_usd=cost_breakdown.total_cost_usd,
            success=provider_response.success,
            cached=False,
            fallback_used=response.fallback_used,
        )
        metrics_collector.record(metric)
        
        storage.put_log({
            "request_id": request_id,
            "model": provider_response.model_used,
            "provider": provider_response.provider,
            "task": request.task.value,
            "preference": request.model_preference.value,
            "input_tokens": provider_response.input_tokens,
            "output_tokens": provider_response.output_tokens,
            "cost_usd": cost_breakdown.total_cost_usd,
            "total_time_ms": total_time_ms,
            "success": provider_response.success,
        })
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/models", summary="List Available Models")
async def list_models(api_key: str = Depends(verify_api_key)):
    """List all available models with details"""
    model_router = get_router()
    available_models = model_router.get_available_models()
    
    models = []
    for model in available_models:
        pricing = MODEL_PRICING.get(model, {})
        capabilities = MODEL_CAPABILITIES.get(model, {})
        
        models.append({
            "model": model,
            "provider": capabilities.get("provider", "unknown"),
            "tasks": capabilities.get("tasks", []),
            "max_tokens": capabilities.get("max_tokens", 4096),
            "avg_latency_ms": capabilities.get("avg_latency_ms", 1000),
            "quality_score": capabilities.get("quality_score", 0.5),
            "pricing": {
                "input_per_1k_tokens": pricing.get("input", 0),
                "output_per_1k_tokens": pricing.get("output", 0),
            }
        })
    
    return {"models": models, "total": len(models)}


@router.post("/estimate", summary="Estimate Request Cost")
async def estimate_cost(
    request: GenerateRequest,
    api_key: str = Depends(verify_api_key),
):
    """Estimate cost without executing"""
    model_router = get_router()
    cost_calculator = get_cost_calculator()
    
    selected_model, routing_decision = await model_router.select_model(request)
    estimated_cost = cost_calculator.estimate_cost(selected_model, request.text)
    
    return {
        "selected_model": selected_model,
        "estimated_cost_usd": estimated_cost,
        "routing_decision": routing_decision,
    }