"""
LLM Orchestration Engine - Response Models
Pydantic schemas for API responses
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, Literal
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Async job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RoutingDecision(BaseModel):
    """Details about the routing decision"""
    
    selected_model: str = Field(description="Model that was selected")
    provider: str = Field(description="Provider (openai, anthropic, local, etc.)")
    reason: str = Field(description="Why this model was selected")
    alternatives_considered: list[str] = Field(
        default_factory=list,
        description="Other models that were considered"
    )
    routing_time_ms: float = Field(description="Time spent on routing decision")
    
    # Scoring breakdown
    cost_score: float = Field(ge=0, le=1, description="Cost efficiency score")
    latency_score: float = Field(ge=0, le=1, description="Expected latency score")
    quality_score: float = Field(ge=0, le=1, description="Quality score for task")
    availability_score: float = Field(ge=0, le=1, description="Provider availability score")
    final_score: float = Field(ge=0, le=1, description="Combined weighted score")


class UsageMetrics(BaseModel):
    """Token usage and cost metrics"""
    
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    
    # Cost breakdown
    input_cost_usd: float = Field(ge=0)
    output_cost_usd: float = Field(ge=0)
    total_cost_usd: float = Field(ge=0)
    
    # Estimated vs actual
    estimated_cost_usd: Optional[float] = Field(default=None)
    cost_savings_usd: Optional[float] = Field(
        default=None,
        description="Cost saved vs using most expensive model"
    )


class PerformanceMetrics(BaseModel):
    """Performance timing metrics"""
    
    total_time_ms: float = Field(description="Total request time")
    routing_time_ms: float = Field(description="Time for routing decision")
    inference_time_ms: float = Field(description="Model inference time")
    overhead_time_ms: float = Field(description="Network/processing overhead")
    
    # Provider metrics
    provider_latency_ms: Optional[float] = Field(
        default=None,
        description="Raw provider API latency"
    )
    tokens_per_second: Optional[float] = Field(
        default=None,
        description="Generation speed"
    )


class GenerateResponse(BaseModel):
    """Main generation response schema"""
    
    # Core response
    success: bool = Field(description="Whether the request succeeded")
    result: Optional[str] = Field(
        default=None,
        description="Generated text result"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    
    # Request tracking
    request_id: str = Field(description="Unique request identifier")
    timestamp: datetime = Field(description="Response timestamp")
    
    # Routing information
    routing: RoutingDecision = Field(description="Routing decision details")
    
    # Metrics
    usage: UsageMetrics = Field(description="Token and cost metrics")
    performance: PerformanceMetrics = Field(description="Timing metrics")
    
    # Additional metadata
    cached: bool = Field(default=False, description="Whether response was cached")
    retries: int = Field(default=0, description="Number of retry attempts")
    fallback_used: bool = Field(
        default=False,
        description="Whether a fallback model was used"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "result": "This is a summary of the input text...",
                "request_id": "req_abc123",
                "timestamp": "2025-01-15T10:30:00Z",
                "routing": {
                    "selected_model": "gpt-4o-mini",
                    "provider": "openai",
                    "reason": "Best cost-latency balance for summarization",
                    "alternatives_considered": ["claude-3-5-haiku", "gpt-4o"],
                    "routing_time_ms": 5.2,
                    "cost_score": 0.9,
                    "latency_score": 0.85,
                    "quality_score": 0.8,
                    "availability_score": 1.0,
                    "final_score": 0.87
                },
                "usage": {
                    "input_tokens": 150,
                    "output_tokens": 50,
                    "total_tokens": 200,
                    "input_cost_usd": 0.0000225,
                    "output_cost_usd": 0.00003,
                    "total_cost_usd": 0.0000525
                },
                "performance": {
                    "total_time_ms": 850,
                    "routing_time_ms": 5.2,
                    "inference_time_ms": 820,
                    "overhead_time_ms": 24.8
                }
            }
        }


class AsyncJobResponse(BaseModel):
    """Response for async job submission"""
    
    job_id: str = Field(description="Unique job identifier")
    status: JobStatus = Field(description="Current job status")
    created_at: datetime = Field(description="Job creation timestamp")
    estimated_completion_seconds: Optional[int] = Field(
        default=None,
        description="Estimated seconds until completion"
    )
    poll_url: str = Field(description="URL to check job status")


class AsyncJobStatusResponse(BaseModel):
    """Response for async job status check"""
    
    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    
    # Progress (if available)
    progress_percent: Optional[float] = Field(default=None, ge=0, le=100)
    
    # Result (if completed)
    result: Optional[GenerateResponse] = Field(default=None)
    
    # Error (if failed)
    error: Optional[str] = Field(default=None)
    error_code: Optional[str] = Field(default=None)


class HealthResponse(BaseModel):
    """Health check response"""
    
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        description="Overall health status"
    )
    version: str = Field(description="Application version")
    timestamp: datetime
    
    # Provider health
    providers: dict[str, dict[str, Any]] = Field(
        description="Health status of each provider"
    )
    
    # System metrics
    uptime_seconds: float
    requests_processed: int
    error_rate_percent: float


class MetricsResponse(BaseModel):
    """Aggregated metrics response"""
    
    time_range: dict[str, datetime] = Field(
        description="Start and end of metrics period"
    )
    total_requests: int
    successful_requests: int
    failed_requests: int
    
    # Cost metrics
    total_cost_usd: float
    average_cost_per_request_usd: float
    cost_by_provider: dict[str, float]
    cost_by_model: dict[str, float]
    
    # Latency metrics
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    average_latency_ms: float
    
    # Usage metrics
    total_tokens: int
    tokens_by_model: dict[str, int]
    requests_by_task: dict[str, int]
    requests_by_preference: dict[str, int]
    
    # Routing metrics
    model_selection_breakdown: dict[str, int]
    fallback_rate_percent: float
    cache_hit_rate_percent: float


class ErrorResponse(BaseModel):
    """Standard error response"""
    
    success: bool = Field(default=False)
    error: str = Field(description="Error message")
    error_code: str = Field(description="Machine-readable error code")
    request_id: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[dict[str, Any]] = Field(default=None)