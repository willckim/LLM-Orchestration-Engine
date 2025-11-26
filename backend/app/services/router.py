"""
LLM Orchestration Engine - Intelligent Model Router
The brain of the system: selects optimal model based on task, preferences, and metrics
"""

import time
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from app.config import (
    get_settings,
    MODEL_PRICING,
    MODEL_CAPABILITIES,
)
from app.models import (
    TaskType,
    ModelPreference,
    GenerateRequest,
    RoutingDecision,
)
from app.services.providers import (
    get_litellm_provider,
    get_mock_provider,
    ProviderResponse,
)


@dataclass
class ModelScore:
    """Scoring breakdown for a model"""
    model: str
    provider: str
    cost_score: float
    latency_score: float
    quality_score: float
    availability_score: float
    final_score: float
    reason: str


class ModelRouter:
    """
    Intelligent model router that selects the optimal model based on:
    - Task type requirements
    - User preferences (fast/cheap/best/balanced)
    - Model capabilities and pricing
    - Provider availability and historical performance
    - Dynamic metrics from past requests
    """
    
    # Weight configurations for different preferences
    PREFERENCE_WEIGHTS = {
        ModelPreference.FAST: {
            "cost": 0.1,
            "latency": 0.6,
            "quality": 0.2,
            "availability": 0.1,
        },
        ModelPreference.CHEAP: {
            "cost": 0.6,
            "latency": 0.1,
            "quality": 0.2,
            "availability": 0.1,
        },
        ModelPreference.BEST: {
            "cost": 0.1,
            "latency": 0.1,
            "quality": 0.6,
            "availability": 0.2,
        },
        ModelPreference.BALANCED: {
            "cost": 0.25,
            "latency": 0.25,
            "quality": 0.35,
            "availability": 0.15,
        },
    }
    
    # Task-specific model preferences
    TASK_MODEL_PREFERENCES = {
        TaskType.SENTIMENT: ["local/sentiment", "gpt-4o-mini", "claude-3-5-haiku-20241022"],
        TaskType.SUMMARIZE: ["gpt-4o-mini", "claude-3-5-haiku-20241022", "gpt-4o"],
        TaskType.REWRITE: ["gpt-4o", "claude-3-5-sonnet-20241022", "gpt-4o-mini"],
        TaskType.TOOLS: ["gpt-4o", "claude-3-5-sonnet-20241022"],
        TaskType.CODE: ["claude-3-5-sonnet-20241022", "gpt-4o", "gpt-4o-mini"],
        TaskType.ANALYSIS: ["claude-3-5-sonnet-20241022", "gpt-4o", "claude-3-opus-20240229"],
        TaskType.CHAT: ["gpt-4o-mini", "claude-3-5-haiku-20241022", "gpt-4o"],
        TaskType.CUSTOM: ["gpt-4o", "claude-3-5-sonnet-20241022"],
    }
    
    def __init__(self):
        self.settings = get_settings()
        self.litellm_provider = get_litellm_provider()
        self.mock_provider = get_mock_provider()
        
        # Dynamic metrics storage (in production, this would be from DynamoDB)
        self._model_metrics: dict[str, dict] = {}
        self._provider_health: dict[str, float] = {}  # availability scores
    
    def get_available_models(self) -> list[str]:
        """Get list of currently available models"""
        available = []
        
        # Get models from LiteLLM provider
        available.extend(self.litellm_provider.get_available_models())
        
        # Local models (if enabled)
        if self.settings.enable_local_models:
            available.extend(["local/sentiment", "local/classifier"])
        
        # Mock always available for testing
        available.append("mock/default")
        
        return list(set(available))
    
    def _calculate_cost_score(self, model: str, estimated_tokens: int) -> float:
        """
        Calculate cost efficiency score (0-1, higher is better/cheaper)
        """
        pricing = MODEL_PRICING.get(model)
        if not pricing:
            return 0.5  # Unknown pricing, neutral score
        
        # Estimate cost
        input_cost = (estimated_tokens * 0.7) * pricing["input"] / 1000  # Assume 70% input
        output_cost = (estimated_tokens * 0.3) * pricing["output"] / 1000  # Assume 30% output
        total_cost = input_cost + output_cost
        
        # Score: cheaper = higher score
        # Use log scale to handle wide cost range
        if total_cost == 0:
            return 1.0  # Free is best
        
        # Normalize against most expensive model
        max_cost = 0.001  # Reference cost for scoring
        score = 1.0 - min(total_cost / max_cost, 1.0)
        
        return max(0.0, min(1.0, score))
    
    def _calculate_latency_score(self, model: str) -> float:
        """
        Calculate latency score (0-1, higher is better/faster)
        """
        capabilities = MODEL_CAPABILITIES.get(model)
        if not capabilities:
            return 0.5  # Unknown latency, neutral score
        
        avg_latency = capabilities.get("avg_latency_ms", 1000)
        
        # Score: faster = higher score
        # Under 500ms = 1.0, over 3000ms = 0.0
        if avg_latency <= self.settings.latency_threshold_fast_ms:
            return 1.0
        elif avg_latency >= 3000:
            return 0.0
        else:
            return 1.0 - (avg_latency - 500) / 2500
    
    def _calculate_quality_score(self, model: str, task: TaskType) -> float:
        """
        Calculate quality score for specific task (0-1, higher is better)
        """
        capabilities = MODEL_CAPABILITIES.get(model)
        if not capabilities:
            return 0.5
        
        # Check if model supports the task
        supported_tasks = capabilities.get("tasks", [])
        if task.value not in supported_tasks:
            return 0.1  # Penalize models that don't support the task
        
        # Base quality score
        base_quality = capabilities.get("quality_score", 0.5)
        
        # Boost score if model is preferred for this task
        preferred_models = self.TASK_MODEL_PREFERENCES.get(task, [])
        if model in preferred_models:
            position = preferred_models.index(model)
            boost = (len(preferred_models) - position) / len(preferred_models) * 0.1
            base_quality = min(1.0, base_quality + boost)
        
        return base_quality
    
    def _calculate_availability_score(self, model: str) -> float:
        """
        Calculate availability score based on provider health
        """
        capabilities = MODEL_CAPABILITIES.get(model)
        if not capabilities:
            return 0.5
        
        provider = capabilities.get("provider", "unknown")
        
        # Check if provider is configured
        available_providers = self.settings.available_providers
        if provider not in available_providers:
            return 0.0  # Not available
        
        # Get historical availability (from dynamic metrics)
        if provider in self._provider_health:
            return self._provider_health[provider]
        
        # Default to high availability for configured providers
        return 0.95
    
    def score_model(
        self,
        model: str,
        request: GenerateRequest,
        estimated_tokens: int,
    ) -> ModelScore:
        """
        Calculate comprehensive score for a model
        """
        cost_score = self._calculate_cost_score(model, estimated_tokens)
        latency_score = self._calculate_latency_score(model)
        quality_score = self._calculate_quality_score(model, request.task)
        availability_score = self._calculate_availability_score(model)
        
        # Get weights for user preference
        weights = self.PREFERENCE_WEIGHTS[request.model_preference]
        
        # Calculate weighted final score
        final_score = (
            weights["cost"] * cost_score +
            weights["latency"] * latency_score +
            weights["quality"] * quality_score +
            weights["availability"] * availability_score
        )
        
        # Apply user constraints
        if request.max_cost_usd is not None:
            pricing = MODEL_PRICING.get(model, {})
            est_cost = (estimated_tokens * (pricing.get("input", 0) + pricing.get("output", 0))) / 1000
            if est_cost > request.max_cost_usd:
                final_score *= 0.1  # Heavy penalty for exceeding cost
        
        if request.max_latency_ms is not None:
            capabilities = MODEL_CAPABILITIES.get(model, {})
            avg_latency = capabilities.get("avg_latency_ms", 1000)
            if avg_latency > request.max_latency_ms:
                final_score *= 0.5  # Penalty for exceeding latency
        
        # Generate reason
        reason = self._generate_reason(
            model, request, cost_score, latency_score, quality_score
        )
        
        capabilities = MODEL_CAPABILITIES.get(model, {})
        provider = capabilities.get("provider", "unknown")
        
        return ModelScore(
            model=model,
            provider=provider,
            cost_score=cost_score,
            latency_score=latency_score,
            quality_score=quality_score,
            availability_score=availability_score,
            final_score=final_score,
            reason=reason,
        )
    
    def _generate_reason(
        self,
        model: str,
        request: GenerateRequest,
        cost_score: float,
        latency_score: float,
        quality_score: float,
    ) -> str:
        """Generate human-readable routing reason"""
        preference = request.model_preference.value
        task = request.task.value
        
        # Find the dominant factor
        scores = [
            ("cost efficiency", cost_score),
            ("low latency", latency_score),
            ("quality", quality_score),
        ]
        best_factor = max(scores, key=lambda x: x[1])
        
        if preference == "fast":
            return f"Selected for {task} with focus on speed. Model offers {best_factor[0]} (score: {best_factor[1]:.2f})"
        elif preference == "cheap":
            return f"Selected for {task} with focus on cost. Model offers {best_factor[0]} (score: {best_factor[1]:.2f})"
        elif preference == "best":
            return f"Selected for {task} with focus on quality. Model offers {best_factor[0]} (score: {best_factor[1]:.2f})"
        else:
            return f"Selected for {task} with balanced optimization across cost, speed, and quality"
    
    async def select_model(
        self,
        request: GenerateRequest,
    ) -> tuple[str, RoutingDecision]:
        """
        Select the optimal model for a request
        Returns: (selected_model, routing_decision)
        """
        start_time = time.perf_counter()
        
        # If model override specified, use it
        if request.model_override:
            routing_time_ms = (time.perf_counter() - start_time) * 1000
            return request.model_override, RoutingDecision(
                selected_model=request.model_override,
                provider=MODEL_CAPABILITIES.get(request.model_override, {}).get("provider", "unknown"),
                reason="Model override specified by user",
                alternatives_considered=[],
                routing_time_ms=routing_time_ms,
                cost_score=0.5,
                latency_score=0.5,
                quality_score=0.5,
                availability_score=1.0,
                final_score=0.5,
            )
        
        # Estimate tokens for scoring
        estimated_tokens = len(request.text.split()) * 1.3  # Rough estimate
        
        # Get available models
        available_models = self.get_available_models()
        
        # Score each model
        model_scores: list[ModelScore] = []
        for model in available_models:
            score = self.score_model(model, request, int(estimated_tokens))
            if score.availability_score > 0:  # Only consider available models
                model_scores.append(score)
        
        # Sort by final score (descending)
        model_scores.sort(key=lambda x: x.final_score, reverse=True)
        
        # Select best model
        if not model_scores:
            # Fallback to mock if nothing available
            best = ModelScore(
                model="mock/default",
                provider="mock",
                cost_score=1.0,
                latency_score=1.0,
                quality_score=0.5,
                availability_score=1.0,
                final_score=0.7,
                reason="Fallback to mock - no models available",
            )
        else:
            best = model_scores[0]
        
        routing_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Build routing decision
        routing_decision = RoutingDecision(
            selected_model=best.model,
            provider=best.provider,
            reason=best.reason,
            alternatives_considered=[s.model for s in model_scores[1:5]],  # Top 4 alternatives
            routing_time_ms=routing_time_ms,
            cost_score=best.cost_score,
            latency_score=best.latency_score,
            quality_score=best.quality_score,
            availability_score=best.availability_score,
            final_score=best.final_score,
        )
        
        return best.model, routing_decision
    
    async def execute_request(
        self,
        request: GenerateRequest,
        model: str,
        routing_decision: RoutingDecision,
    ) -> ProviderResponse:
        """
        Execute the request with the selected model
        Handles fallback if primary model fails
        """
        # Get task-specific system prompt
        system_prompt = request.system_prompt or self._get_default_system_prompt(request.task)
        
        # Determine provider
        capabilities = MODEL_CAPABILITIES.get(model, {})
        provider_name = capabilities.get("provider", "mock")
        
        # Execute based on provider
        if provider_name == "mock":
            response = await self.mock_provider.generate(
                prompt=request.text,
                model=model,
                max_tokens=request.max_tokens or 1024,
                temperature=request.temperature or 0.7,
                system_prompt=system_prompt,
                task_type=request.task.value,
            )
        else:
            response = await self.litellm_provider.generate(
                prompt=request.text,
                model=model,
                max_tokens=request.max_tokens or 1024,
                temperature=request.temperature or 0.7,
                system_prompt=system_prompt,
            )
        
        # Handle fallback if failed
        if not response.success and routing_decision.alternatives_considered:
            for fallback_model in routing_decision.alternatives_considered[:2]:
                fallback_caps = MODEL_CAPABILITIES.get(fallback_model, {})
                fallback_provider = fallback_caps.get("provider", "mock")
                
                if fallback_provider == "mock":
                    response = await self.mock_provider.generate(
                        prompt=request.text,
                        model=fallback_model,
                        max_tokens=request.max_tokens or 1024,
                        temperature=request.temperature or 0.7,
                        system_prompt=system_prompt,
                        task_type=request.task.value,
                    )
                else:
                    response = await self.litellm_provider.generate(
                        prompt=request.text,
                        model=fallback_model,
                        max_tokens=request.max_tokens or 1024,
                        temperature=request.temperature or 0.7,
                        system_prompt=system_prompt,
                    )
                
                if response.success:
                    break
        
        return response
    
    def _get_default_system_prompt(self, task: TaskType) -> str:
        """Get default system prompt for task type"""
        prompts = {
            TaskType.SUMMARIZE: "You are a skilled summarizer. Provide clear, concise summaries that capture the key points.",
            TaskType.SENTIMENT: "You are a sentiment analyzer. Analyze the sentiment and return a JSON object with 'sentiment' (positive/negative/neutral), 'confidence' (0-1), and 'aspects' dict.",
            TaskType.REWRITE: "You are a professional editor. Rewrite the given text to improve clarity, flow, and professionalism while preserving the original meaning.",
            TaskType.TOOLS: "You are an AI assistant with tool-use capabilities. Analyze requests and determine appropriate actions.",
            TaskType.CODE: "You are an expert programmer. Provide clean, efficient, well-documented code solutions.",
            TaskType.ANALYSIS: "You are a data analyst. Provide thorough, insightful analysis with clear structure and actionable conclusions.",
            TaskType.CHAT: "You are a helpful AI assistant. Provide clear, accurate, and helpful responses.",
            TaskType.CUSTOM: "You are a versatile AI assistant. Complete the requested task effectively.",
        }
        return prompts.get(task, prompts[TaskType.CHAT])
    
    def update_metrics(self, model: str, success: bool, latency_ms: float, cost_usd: float):
        """Update dynamic metrics for model selection improvement"""
        if model not in self._model_metrics:
            self._model_metrics[model] = {
                "total_requests": 0,
                "successful_requests": 0,
                "total_latency_ms": 0,
                "total_cost_usd": 0,
            }
        
        metrics = self._model_metrics[model]
        metrics["total_requests"] += 1
        metrics["total_latency_ms"] += latency_ms
        metrics["total_cost_usd"] += cost_usd
        if success:
            metrics["successful_requests"] += 1


# Singleton instance
_router: Optional[ModelRouter] = None


def get_router() -> ModelRouter:
    """Get or create router instance"""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router