"""
LLM Orchestration Engine - Mock Provider
Mock provider for testing, demos, and development without API keys
"""

import time
import random
import asyncio
from typing import Optional
from datetime import datetime

from .base import BaseProvider, ProviderResponse, ProviderHealth


class MockProvider(BaseProvider):
    """
    Mock LLM provider for testing and demos
    Generates realistic-looking responses without calling external APIs
    """
    
    # Simulated task responses
    MOCK_RESPONSES = {
        "summarize": [
            "This text discusses the key points of {topic}. The main takeaway is that there are multiple factors to consider when evaluating this subject. The author presents a balanced view while emphasizing the importance of evidence-based conclusions.",
            "In summary, the content covers {topic} from several angles. Key insights include the relationship between different elements and their impact on outcomes. The conclusion suggests further analysis may be beneficial.",
            "The document provides an overview of {topic}, highlighting three main aspects: context, implications, and recommendations. Overall, it presents a comprehensive analysis suitable for decision-making."
        ],
        "sentiment": [
            '{"sentiment": "positive", "confidence": 0.87, "aspects": {"tone": "optimistic", "emotion": "hopeful"}}',
            '{"sentiment": "neutral", "confidence": 0.92, "aspects": {"tone": "informative", "emotion": "calm"}}',
            '{"sentiment": "negative", "confidence": 0.78, "aspects": {"tone": "critical", "emotion": "concerned"}}'
        ],
        "rewrite": [
            "Here is a refined version of the text:\n\n{rewritten}\n\nKey improvements include enhanced clarity, better structure, and more precise language.",
            "The rewritten content:\n\n{rewritten}\n\nChanges focus on improved readability and professional tone.",
        ],
        "chat": [
            "I understand your question about {topic}. Based on the context, I can provide several insights. First, it's important to consider the underlying factors. Second, there are multiple approaches to address this. Would you like me to elaborate on any specific aspect?",
            "That's an interesting point about {topic}. Let me share my perspective: the key consideration here is understanding the relationship between cause and effect. There are typically three main factors to consider in situations like this.",
            "Thank you for bringing up {topic}. This is a nuanced subject with several dimensions to explore. The most relevant points include the context, the stakeholders involved, and the potential outcomes."
        ],
        "code": [
            "```python\ndef solution(data):\n    \"\"\"Solves the given problem efficiently.\"\"\"\n    result = []\n    for item in data:\n        processed = process_item(item)\n        result.append(processed)\n    return result\n```\n\nThis solution handles the core requirements with O(n) time complexity.",
            "```python\nclass Handler:\n    def __init__(self):\n        self.cache = {}\n    \n    def process(self, input_data):\n        if input_data in self.cache:\n            return self.cache[input_data]\n        result = self._compute(input_data)\n        self.cache[input_data] = result\n        return result\n```\n\nI've added caching for improved performance.",
        ],
        "analysis": [
            "Analysis Results:\n\n1. **Overview**: The data shows interesting patterns in {topic}.\n\n2. **Key Findings**:\n   - Finding A: Significant correlation observed\n   - Finding B: Trend indicates growth\n   - Finding C: Anomaly detected in subset\n\n3. **Recommendations**: Based on this analysis, I suggest focusing on areas with highest impact potential.",
            "Executive Summary:\n\nThis analysis examines {topic} across multiple dimensions. The primary conclusion is that current metrics indicate positive trajectory. Areas requiring attention include optimization of resources and alignment with strategic goals."
        ],
        "default": [
            "I've processed your request regarding {topic}. Here are my thoughts:\n\nThe subject matter involves several interconnected elements. Based on the information provided, I can offer the following insights and recommendations for your consideration.",
            "Thank you for your inquiry about {topic}. After considering the relevant factors, I believe the most important points to address are: context, approach, and expected outcomes. Each of these contributes to a comprehensive understanding."
        ]
    }
    
    def __init__(
        self,
        min_latency_ms: float = 100,
        max_latency_ms: float = 500,
        failure_rate: float = 0.0,  # 0-1, percentage of requests to fail
        tokens_per_word: float = 1.3,  # Approximate tokens per word
    ):
        super().__init__(name="mock")
        self.min_latency_ms = min_latency_ms
        self.max_latency_ms = max_latency_ms
        self.failure_rate = failure_rate
        self.tokens_per_word = tokens_per_word
    
    async def generate(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        task_type: str = "chat",
        **kwargs
    ) -> ProviderResponse:
        """Generate a mock response"""
        
        start_time = time.perf_counter()
        
        # Simulate network latency
        simulated_latency = random.uniform(self.min_latency_ms, self.max_latency_ms)
        await asyncio.sleep(simulated_latency / 1000)
        
        # Simulate random failures
        if random.random() < self.failure_rate:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self.record_request(success=False, latency_ms=latency_ms)
            
            return ProviderResponse(
                success=False,
                content=None,
                error="Simulated provider failure for testing",
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                model_used=model,
                provider="mock"
            )
        
        # Extract topic from prompt for response personalization
        words = prompt.split()
        topic = " ".join(words[:5]) + "..." if len(words) > 5 else prompt
        
        # Select appropriate response template
        response_templates = self.MOCK_RESPONSES.get(
            task_type, 
            self.MOCK_RESPONSES["default"]
        )
        template = random.choice(response_templates)
        
        # Generate response
        content = template.format(
            topic=topic,
            rewritten=self._rewrite_text(prompt) if task_type == "rewrite" else ""
        )
        
        # Truncate to max_tokens (approximate)
        content_words = content.split()
        max_words = int(max_tokens / self.tokens_per_word)
        if len(content_words) > max_words:
            content = " ".join(content_words[:max_words]) + "..."
        
        # Calculate tokens
        input_tokens = self.estimate_tokens(prompt)
        if system_prompt:
            input_tokens += self.estimate_tokens(system_prompt)
        output_tokens = self.estimate_tokens(content)
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        self.record_request(success=True, latency_ms=latency_ms)
        
        return ProviderResponse(
            success=True,
            content=content,
            error=None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            model_used=model,
            provider="mock"
        )
    
    def _rewrite_text(self, text: str) -> str:
        """Simple text rewriting for mock responses"""
        # Just return a slightly modified version
        sentences = text.replace(".", ".|").replace("!", "!|").replace("?", "?|").split("|")
        rewritten = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                # Simple word substitutions for variety
                sentence = sentence.replace("very", "extremely")
                sentence = sentence.replace("good", "excellent")
                sentence = sentence.replace("bad", "suboptimal")
                sentence = sentence.replace("big", "substantial")
                sentence = sentence.replace("small", "minimal")
                rewritten.append(sentence)
        return " ".join(rewritten)
    
    async def check_health(self) -> ProviderHealth:
        """Mock health check - always healthy"""
        return ProviderHealth(
            available=True,
            latency_ms=random.uniform(10, 50),
            error=None,
            last_checked=datetime.utcnow(),
            success_rate=1.0 - self.failure_rate
        )
    
    def get_available_models(self) -> list[str]:
        """Return available mock models"""
        return [
            "mock/default",
            "mock/fast",
            "mock/quality",
        ]
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count based on word count"""
        word_count = len(text.split())
        return int(word_count * self.tokens_per_word)


# Singleton instance
_mock_provider: Optional[MockProvider] = None


def get_mock_provider() -> MockProvider:
    """Get or create mock provider instance"""
    global _mock_provider
    if _mock_provider is None:
        _mock_provider = MockProvider()
    return _mock_provider