"""
LLM Orchestration Engine - Request Models
Pydantic schemas for API requests
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, Any
from enum import Enum
from datetime import datetime


class TaskType(str, Enum):
    """Supported task types"""
    SUMMARIZE = "summarize"
    SENTIMENT = "sentiment"
    REWRITE = "rewrite"
    TOOLS = "tools"
    CHAT = "chat"
    CODE = "code"
    ANALYSIS = "analysis"
    CUSTOM = "custom"


class ModelPreference(str, Enum):
    """Model selection preferences"""
    FAST = "fast"        # Prioritize latency
    CHEAP = "cheap"      # Prioritize cost
    BEST = "best"        # Prioritize quality
    BALANCED = "balanced"  # Balance all factors


class GenerateRequest(BaseModel):
    """Main generation request schema"""
    
    task: TaskType = Field(
        default=TaskType.CHAT,
        description="Type of task to perform"
    )
    model_preference: ModelPreference = Field(
        default=ModelPreference.BALANCED,
        description="Model selection strategy"
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        description="Input text to process"
    )
    
    # Optional overrides
    model_override: Optional[str] = Field(
        default=None,
        description="Force a specific model (bypasses routing)"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=32000,
        description="Maximum tokens in response"
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )
    system_prompt: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Custom system prompt"
    )
    
    # Routing hints
    max_cost_usd: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Maximum acceptable cost in USD"
    )
    max_latency_ms: Optional[int] = Field(
        default=None,
        ge=100,
        description="Maximum acceptable latency in milliseconds"
    )
    
    # Request metadata
    request_id: Optional[str] = Field(
        default=None,
        description="Client-provided request ID for tracking"
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="Client user agent (e.g., 'chrome-extension', 'mobile-app')"
    )
    
    @field_validator('text')
    @classmethod
    def validate_text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "task": "summarize",
                "model_preference": "balanced",
                "text": "The quick brown fox jumps over the lazy dog. This is a sample text that needs to be summarized.",
                "max_tokens": 100,
                "temperature": 0.7
            }
        }


class BatchGenerateRequest(BaseModel):
    """Batch processing request for multiple items"""
    
    items: list[GenerateRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of generation requests"
    )
    async_mode: bool = Field(
        default=True,
        description="Process asynchronously via Step Functions"
    )
    callback_url: Optional[str] = Field(
        default=None,
        description="Webhook URL for completion notification"
    )


class AsyncJobRequest(BaseModel):
    """Request to start an async job"""
    
    request: GenerateRequest
    priority: Literal["low", "normal", "high"] = Field(
        default="normal",
        description="Job priority level"
    )
    ttl_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Hours to retain results"
    )


class MetricsQueryRequest(BaseModel):
    """Request for metrics data"""
    
    start_time: Optional[datetime] = Field(
        default=None,
        description="Start of time range"
    )
    end_time: Optional[datetime] = Field(
        default=None,
        description="End of time range"
    )
    group_by: Literal["model", "task", "provider", "hour", "day"] = Field(
        default="model",
        description="Grouping dimension"
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum results to return"
    )