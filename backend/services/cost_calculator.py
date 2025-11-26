"""
LLM Orchestration Engine - Cost Calculator
Calculates and tracks costs for LLM usage
"""

from typing import Optional
from dataclasses import dataclass

from app.config import MODEL_PRICING


@dataclass
class CostBreakdown:
    """Detailed cost breakdown"""
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    estimated_savings_usd: float  # vs most expensive alternative
    cost_per_1k_tokens: float
    model: str


class CostCalculator:
    """
    Calculates and optimizes LLM costs
    """
    
    def __init__(self):
        self.pricing = MODEL_PRICING
        
        # Track cumulative costs
        self._total_cost_usd = 0.0
        self._cost_by_model: dict[str, float] = {}
        self._cost_by_provider: dict[str, float] = {}
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> CostBreakdown:
        """
        Calculate the cost for a request
        """
        pricing = self.pricing.get(model, {"input": 0.01, "output": 0.03})
        
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        # Calculate savings vs most expensive model
        max_pricing = max(
            self.pricing.values(),
            key=lambda p: p["input"] + p["output"]
        )
        max_cost = (
            (input_tokens / 1000) * max_pricing["input"] +
            (output_tokens / 1000) * max_pricing["output"]
        )
        savings = max_cost - total_cost
        
        # Cost per 1k tokens
        total_tokens = input_tokens + output_tokens
        cost_per_1k = (total_cost / total_tokens * 1000) if total_tokens > 0 else 0
        
        return CostBreakdown(
            input_cost_usd=input_cost,
            output_cost_usd=output_cost,
            total_cost_usd=total_cost,
            estimated_savings_usd=max(0, savings),
            cost_per_1k_tokens=cost_per_1k,
            model=model,
        )
    
    def estimate_cost(
        self,
        model: str,
        text: str,
        expected_output_ratio: float = 0.3,
    ) -> float:
        """
        Estimate cost before making a request
        """
        # Rough token estimation (4 chars per token)
        estimated_input_tokens = len(text) // 4
        estimated_output_tokens = int(estimated_input_tokens * expected_output_ratio)
        
        breakdown = self.calculate_cost(model, estimated_input_tokens, estimated_output_tokens)
        return breakdown.total_cost_usd
    
    def record_cost(
        self,
        model: str,
        provider: str,
        cost_usd: float,
    ):
        """Record cost for tracking and analytics"""
        self._total_cost_usd += cost_usd
        
        if model not in self._cost_by_model:
            self._cost_by_model[model] = 0.0
        self._cost_by_model[model] += cost_usd
        
        if provider not in self._cost_by_provider:
            self._cost_by_provider[provider] = 0.0
        self._cost_by_provider[provider] += cost_usd
    
    def get_cheapest_model(
        self,
        models: list[str],
        estimated_tokens: int = 1000,
    ) -> str:
        """Find the cheapest model from a list"""
        costs = []
        for model in models:
            if model in self.pricing:
                pricing = self.pricing[model]
                cost = (estimated_tokens / 1000) * (pricing["input"] * 0.7 + pricing["output"] * 0.3)
                costs.append((model, cost))
        
        if not costs:
            return models[0] if models else "mock/default"
        
        return min(costs, key=lambda x: x[1])[0]
    
    def get_cost_summary(self) -> dict:
        """Get cost summary for dashboard"""
        return {
            "total_cost_usd": self._total_cost_usd,
            "cost_by_model": self._cost_by_model.copy(),
            "cost_by_provider": self._cost_by_provider.copy(),
        }
    
    def compare_models(
        self,
        models: list[str],
        input_tokens: int,
        output_tokens: int,
    ) -> list[dict]:
        """Compare costs across multiple models"""
        comparisons = []
        
        for model in models:
            breakdown = self.calculate_cost(model, input_tokens, output_tokens)
            comparisons.append({
                "model": model,
                "input_cost": breakdown.input_cost_usd,
                "output_cost": breakdown.output_cost_usd,
                "total_cost": breakdown.total_cost_usd,
                "cost_per_1k": breakdown.cost_per_1k_tokens,
            })
        
        # Sort by total cost
        comparisons.sort(key=lambda x: x["total_cost"])
        
        return comparisons


# Singleton
_calculator: Optional[CostCalculator] = None


def get_cost_calculator() -> CostCalculator:
    """Get or create cost calculator instance"""
    global _calculator
    if _calculator is None:
        _calculator = CostCalculator()
    return _calculator