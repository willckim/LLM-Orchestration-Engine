"""
LLM Orchestration Engine - Base Provider
Abstract base class for all LLM providers
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from dataclasses import dataclass
from datetime import datetime
import time


@dataclass
class ProviderResponse:
    """Standardized response from any provider"""
    
    success: bool
    content: Optional[str]
    error: Optional[str]
    
    # Token usage
    input_tokens: int
    output_tokens: int
    
    # Timing
    latency_ms: float
    
    # Provider metadata
    model_used: str
    provider: str
    raw_response: Optional[dict] = None
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class ProviderHealth:
    """Provider health status"""
    
    available: bool
    latency_ms: Optional[float]
    error: Optional[str]
    last_checked: datetime
    success_rate: float  # 0-1


class BaseProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, name: str):
        self.name = name
        self._health_cache: Optional[ProviderHealth] = None
        self._health_cache_ttl = 60  # seconds
        self._last_health_check = 0.0
        
        # Metrics tracking
        self._request_count = 0
        self._error_count = 0
        self._total_latency_ms = 0.0
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> ProviderResponse:
        """Generate a response from the model"""
        pass
    
    @abstractmethod
    async def check_health(self) -> ProviderHealth:
        """Check if the provider is available"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> list[str]:
        """Return list of available models for this provider"""
        pass
    
    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        pass
    
    async def get_health(self, force_refresh: bool = False) -> ProviderHealth:
        """Get cached health or refresh if stale"""
        now = time.time()
        
        if (
            force_refresh 
            or self._health_cache is None 
            or (now - self._last_health_check) > self._health_cache_ttl
        ):
            self._health_cache = await self.check_health()
            self._last_health_check = now
        
        return self._health_cache
    
    def record_request(self, success: bool, latency_ms: float):
        """Record request metrics"""
        self._request_count += 1
        self._total_latency_ms += latency_ms
        if not success:
            self._error_count += 1
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self._request_count == 0:
            return 1.0
        return (self._request_count - self._error_count) / self._request_count
    
    @property
    def average_latency_ms(self) -> float:
        """Calculate average latency"""
        if self._request_count == 0:
            return 0.0
        return self._total_latency_ms / self._request_count
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(name={self.name})>"