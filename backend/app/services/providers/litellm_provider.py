"""
LLM Orchestration Engine - LiteLLM Provider
Unified provider using LiteLLM for OpenAI, Anthropic, Azure, and Bedrock
"""

import time
import asyncio
from typing import Optional
from datetime import datetime

from .base import BaseProvider, ProviderResponse, ProviderHealth
from app.config import get_settings

# LiteLLM will be imported at runtime to handle missing dependency gracefully
try:
    import litellm
    from litellm import acompletion, token_counter
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False


class LiteLLMProvider(BaseProvider):
    """
    Unified LLM provider using LiteLLM
    Supports: OpenAI, Anthropic, Azure OpenAI, AWS Bedrock
    """
    
    # Model mappings for different providers
    MODEL_MAPPINGS = {
        # OpenAI models
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
        "gpt-4-turbo": "gpt-4-turbo",
        "gpt-3.5-turbo": "gpt-3.5-turbo",
        
        # Anthropic models
        "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku": "claude-3-5-haiku-20241022",
        "claude-3-opus": "claude-3-opus-20240229",
        "claude-3-5-sonnet-20241022": "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022": "claude-3-5-haiku-20241022",
        
        # Azure OpenAI (prefix with azure/)
        "azure/gpt-4o": "azure/gpt-4o",
        "azure/gpt-4o-mini": "azure/gpt-4o-mini",
        
        # AWS Bedrock (prefix with bedrock/)
        "bedrock/claude-3-sonnet": "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
        "bedrock/claude-3-haiku": "bedrock/anthropic.claude-3-haiku-20240307-v1:0",
        "bedrock/llama3-70b": "bedrock/meta.llama3-70b-instruct-v1:0",
    }
    
    def __init__(self):
        super().__init__(name="litellm")
        self.settings = get_settings()
        self._configure_litellm()
    
    def _configure_litellm(self):
        """Configure LiteLLM with API keys"""
        if not LITELLM_AVAILABLE:
            return
        
        # Disable LiteLLM's verbose logging
        litellm.set_verbose = False
        
        # Set API keys from settings
        if self.settings.openai_api_key:
            litellm.openai_key = self.settings.openai_api_key
        
        if self.settings.anthropic_api_key:
            litellm.anthropic_key = self.settings.anthropic_api_key
        
        # Azure configuration
        if self.settings.azure_openai_api_key:
            litellm.azure_key = self.settings.azure_openai_api_key
            if self.settings.azure_openai_endpoint:
                litellm.azure_api_base = self.settings.azure_openai_endpoint
                litellm.azure_api_version = self.settings.azure_openai_api_version
    
    def _resolve_model(self, model: str) -> str:
        """Resolve model alias to actual model name"""
        return self.MODEL_MAPPINGS.get(model, model)
    
    def _detect_provider(self, model: str) -> str:
        """Detect which provider a model belongs to"""
        model_lower = model.lower()
        
        if model_lower.startswith("azure/"):
            return "azure"
        elif model_lower.startswith("bedrock/"):
            return "bedrock"
        elif "claude" in model_lower:
            return "anthropic"
        elif "gpt" in model_lower or "o1" in model_lower:
            return "openai"
        else:
            return "unknown"
    
    async def generate(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> ProviderResponse:
        """Generate response using LiteLLM"""
        
        if not LITELLM_AVAILABLE:
            return ProviderResponse(
                success=False,
                content=None,
                error="LiteLLM not installed. Run: pip install litellm",
                input_tokens=0,
                output_tokens=0,
                latency_ms=0,
                model_used=model,
                provider="litellm"
            )
        
        resolved_model = self._resolve_model(model)
        provider = self._detect_provider(resolved_model)
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        start_time = time.perf_counter()
        
        try:
            response = await acompletion(
                model=resolved_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Extract usage
            usage = response.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            # Extract content
            content = response["choices"][0]["message"]["content"]
            
            self.record_request(success=True, latency_ms=latency_ms)
            
            return ProviderResponse(
                success=True,
                content=content,
                error=None,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                model_used=resolved_model,
                provider=provider,
                raw_response=dict(response)
            )
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.record_request(success=False, latency_ms=latency_ms)
            
            return ProviderResponse(
                success=False,
                content=None,
                error=str(e),
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                model_used=resolved_model,
                provider=provider
            )
    
    async def check_health(self) -> ProviderHealth:
        """Check provider health with a minimal request"""
        
        if not LITELLM_AVAILABLE:
            return ProviderHealth(
                available=False,
                latency_ms=None,
                error="LiteLLM not installed",
                last_checked=datetime.utcnow(),
                success_rate=0.0
            )
        
        # Try a minimal request to check connectivity
        start_time = time.perf_counter()
        
        try:
            # Use cheapest model for health check
            test_model = "gpt-4o-mini"
            if self.settings.anthropic_api_key and not self.settings.openai_api_key:
                test_model = "claude-3-5-haiku-20241022"
            
            response = await acompletion(
                model=test_model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            return ProviderHealth(
                available=True,
                latency_ms=latency_ms,
                error=None,
                last_checked=datetime.utcnow(),
                success_rate=self.success_rate
            )
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            return ProviderHealth(
                available=False,
                latency_ms=latency_ms,
                error=str(e),
                last_checked=datetime.utcnow(),
                success_rate=self.success_rate
            )
    
    def get_available_models(self) -> list[str]:
        """Return models available based on configured API keys"""
        available = []
        
        if self.settings.openai_api_key:
            available.extend([
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
            ])
        
        if self.settings.anthropic_api_key:
            available.extend([
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229",
            ])
        
        if self.settings.azure_openai_api_key:
            available.extend([
                "azure/gpt-4o",
                "azure/gpt-4o-mini",
            ])
        
        # Note: Bedrock requires IAM credentials, checked differently
        
        return available
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using LiteLLM's counter"""
        if not LITELLM_AVAILABLE:
            # Rough estimate: 4 chars per token
            return len(text) // 4
        
        try:
            return token_counter(model="gpt-4o", text=text)
        except Exception:
            # Fallback to rough estimate
            return len(text) // 4


# Singleton instance
_litellm_provider: Optional[LiteLLMProvider] = None


def get_litellm_provider() -> LiteLLMProvider:
    """Get or create LiteLLM provider instance"""
    global _litellm_provider
    if _litellm_provider is None:
        _litellm_provider = LiteLLMProvider()
    return _litellm_provider