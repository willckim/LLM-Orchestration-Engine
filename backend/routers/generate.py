"""
LLM Orchestration Engine - Generate Router
Main API endpoint for LLM generation requests
"""

import time
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse

from app.config import get_settings, MODEL_PRICING
from app.models import (
    GenerateRequest,
    GenerateResponse,
    RoutingDecision,
    UsageMetrics,
    PerformanceMetrics,
    ErrorResponse,
)
from app.services import (
    get_router,
    get_cost_calculator,
    get_metrics_collector,
    RequestMetric,
)
from app.db.local_storage import get_local_storage


router = APIRouter(prefix="/api/v1", tags=["generation"])


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key from header"""
    settings = get_settings()
    
    # In development, allow requests without API key
    if settings.environment == "development" and not x_api_key:
        return "dev-anonymous"
    
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header."
        )
    
    if x_api_key not in settings.valid_api_keys:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return x_api_key


@router.post(
    "/generate",
    response_model=GenerateResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Generate LLM Response",
    description="""
    Main endpoint for LLM generation. Automatically routes to the optimal model
    based on task type and preferences.
    
    **Task Types:**
    - `summarize`: Summarize input text
    - `sentiment`: Analyze sentiment (returns JSON)
    - `rewrite`: Rewrite/edit text
    - `tools`: Tool-calling tasks
    - `chat`: General conversation
    - `code`: Code generation/analysis
    - `analysis`: Data/content analysis
    
    **Preferences:**
    - `fast`: Prioritize low latency
    - `cheap`: Prioritize low cost
    - `best`: Prioritize quality
    - `balanced`: Balance all factors
    """
)
async def generate(
    request: GenerateRequest,
    http_request: Request,
    api_key: str = Depends(verify_api_key),
):
    """
    Generate a response using the optimal LLM model.
    
    The routing engine automatically selects the best model based on:
    - Task type requirements
    - User preference (fast/cheap/best/balanced)
    - Model availability and health
    - Historical performance metrics
    """
    start_time = time.perf_counter()
    request_id = request.request_id or f"req_{uuid.uuid4().hex[:12]}"
    
    # Get services
    model_router = get_router()
    cost_calculator = get_cost_calculator()
    metrics_collector = get_metrics_collector()
    storage = get_local_storage()
    
    try:
        # Step 1: Select optimal model
        selected_model, routing_decision = await model_router.select_model(request)
        routing_time = time.perf_counter()
        
        # Step 2: Execute request
        provider_response = await model_router.execute_request(
            request=request,
            model=selected_model,
            routing_decision=routing_decision,
        )
        
        inference_time = time.perf_counter()
        
        # Step 3: Calculate costs
        cost_breakdown = cost_calculator.calculate_cost(
            model=provider_response.model_used,
            input_tokens=provider_response.input_tokens,
            output_tokens=provider_response.output_tokens,
        )
        
        # Record cost
        cost_calculator.record_cost(
            model=provider_response.model_used,
            provider=provider_response.provider,
            cost_usd=cost_breakdown.total_cost_usd,
        )
        
        # Step 4: Build response
        total_time_ms = (time.perf_counter() - start_time) * 1000
        routing_time_ms = (routing_time - start_time) * 1000
        inference_time_ms = (inference_time - routing_time) * 1000
        
        # Update routing decision with actual model if different
        if provider_response.model_used != selected_model:
            routing_decision.selected_model = provider_response.model_used
            routing_decision.reason += f" (fallback from {selected_model})"
        
        usage = UsageMetrics(
            input_tokens=provider_response.input_tokens,
            output_tokens=provider_response.output_tokens,
            total_tokens=provider_response.total_tokens,
            input_cost_usd=cost_breakdown.input_cost_usd,
            output_cost_usd=cost_breakdown.output_cost_usd,
            total_cost_usd=cost_breakdown.total_cost_usd,
            estimated_cost_usd=cost_calculator.estimate_cost(selected_model, request.text),
            cost_savings_usd=cost_breakdown.estimated_savings_usd,
        )
        
        performance = PerformanceMetrics(
            total_time_ms=total_time_ms,
            routing_time_ms=routing_time_ms,
            inference_time_ms=inference_time_ms,
            overhead_time_ms=total_time_ms - routing_time_ms - inference_time_ms,
            provider_latency_ms=provider_response.latency_ms,
            tokens_per_second=(
                provider_response.output_tokens / (inference_time_ms / 1000)
                if inference_time_ms > 0 else None
            ),
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
            fallback_used=provider_response.model_used != selected_model,
        )
        
        # Step 5: Record metrics
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
            error=provider_response.error,
            user_agent=request.user_agent or http_request.headers.get("user-agent"),
        )
        metrics_collector.record(metric)
        
        # Store log
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
            "error": provider_response.error,
        })
        
        # Update router metrics for learning
        model_router.update_metrics(
            model=provider_response.model_used,
            success=provider_response.success,
            latency_ms=provider_response.latency_ms,
            cost_usd=cost_breakdown.total_cost_usd,
        )
        
        return response
        
    except Exception as e:
        # Log error
        storage.put_log({
            "request_id": request_id,
            "error": str(e),
            "task": request.task.value,
            "success": False,
        })
        
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {str(e)}"
        )


@router.get(
    "/models",
    summary="List Available Models",
    description="Returns list of available models with their capabilities and pricing"
)
async def list_models(api_key: str = Depends(verify_api_key)):
    """List all available models with details"""
    model_router = get_router()
    available_models = model_router.get_available_models()
    
    models = []
    for model in available_models:
        pricing = MODEL_PRICING.get(model, {})
        from app.config import MODEL_CAPABILITIES
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
    
    return {
        "models": models,
        "total": len(models),
    }


@router.post(
    "/estimate",
    summary="Estimate Request Cost",
    description="Estimate cost for a request without executing it"
)
async def estimate_cost(
    request: GenerateRequest,
    api_key: str = Depends(verify_api_key),
):
    """Estimate cost and model selection without executing"""
    model_router = get_router()
    cost_calculator = get_cost_calculator()
    
    # Get model selection
    selected_model, routing_decision = await model_router.select_model(request)
    
    # Estimate cost
    estimated_cost = cost_calculator.estimate_cost(selected_model, request.text)
    
    # Compare with alternatives
    comparisons = cost_calculator.compare_models(
        models=[selected_model] + routing_decision.alternatives_considered[:3],
        input_tokens=len(request.text.split()) * 2,  # Rough estimate
        output_tokens=500,  # Assume moderate output
    )
    
    return {
        "selected_model": selected_model,
        "estimated_cost_usd": estimated_cost,
        "routing_decision": routing_decision,
        "cost_comparison": comparisons,
    }