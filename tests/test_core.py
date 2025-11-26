"""
LLM Orchestration Engine - Test Suite
Comprehensive tests for all components
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

# Import app components
import sys
sys.path.insert(0, './backend')

from app.config import get_settings, MODEL_PRICING, MODEL_CAPABILITIES
from app.models import (
    TaskType,
    ModelPreference,
    GenerateRequest,
    GenerateResponse,
)
from app.services.providers.base import ProviderResponse
from app.services.providers.mock_provider import MockProvider, get_mock_provider
from app.services.cost_calculator import CostCalculator, get_cost_calculator
from app.services.metrics_collector import MetricsCollector, RequestMetric
from app.db.local_storage import LocalStorage


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def mock_provider():
    """Create a mock provider instance"""
    return MockProvider(min_latency_ms=10, max_latency_ms=50, failure_rate=0.0)


@pytest.fixture
def cost_calculator():
    """Create a cost calculator instance"""
    return CostCalculator()


@pytest.fixture
def metrics_collector():
    """Create a metrics collector instance"""
    return MetricsCollector(retention_hours=1)


@pytest.fixture
def local_storage(tmp_path):
    """Create a temporary local storage instance"""
    storage_path = tmp_path / "test_storage.json"
    return LocalStorage(str(storage_path))


@pytest.fixture
def sample_request():
    """Create a sample generate request"""
    return GenerateRequest(
        task=TaskType.SUMMARIZE,
        model_preference=ModelPreference.BALANCED,
        text="This is a sample text that needs to be summarized. It contains multiple sentences with various information.",
    )


# ============================================
# Configuration Tests
# ============================================

class TestConfiguration:
    """Tests for configuration module"""
    
    def test_settings_loads(self):
        """Test that settings load correctly"""
        settings = get_settings()
        assert settings.app_name == "LLM Orchestration Engine"
        assert settings.app_version == "1.0.0"
    
    def test_valid_api_keys_parsing(self):
        """Test API keys are parsed correctly"""
        settings = get_settings()
        assert "dev-key-123" in settings.valid_api_keys
    
    def test_model_pricing_exists(self):
        """Test model pricing data is available"""
        assert "gpt-4o" in MODEL_PRICING
        assert "input" in MODEL_PRICING["gpt-4o"]
        assert "output" in MODEL_PRICING["gpt-4o"]
    
    def test_model_capabilities_exists(self):
        """Test model capabilities data is available"""
        assert "gpt-4o" in MODEL_CAPABILITIES
        assert "tasks" in MODEL_CAPABILITIES["gpt-4o"]


# ============================================
# Mock Provider Tests
# ============================================

class TestMockProvider:
    """Tests for mock provider"""
    
    @pytest.mark.asyncio
    async def test_generate_success(self, mock_provider):
        """Test successful generation"""
        response = await mock_provider.generate(
            prompt="Test prompt",
            model="mock/default",
            max_tokens=100,
        )
        
        assert response.success is True
        assert response.content is not None
        assert len(response.content) > 0
        assert response.input_tokens > 0
        assert response.output_tokens > 0
    
    @pytest.mark.asyncio
    async def test_generate_with_task_type(self, mock_provider):
        """Test generation with different task types"""
        for task in ["summarize", "sentiment", "chat", "code"]:
            response = await mock_provider.generate(
                prompt="Test prompt",
                model="mock/default",
                task_type=task,
            )
            assert response.success is True
    
    @pytest.mark.asyncio
    async def test_health_check(self, mock_provider):
        """Test health check"""
        health = await mock_provider.check_health()
        
        assert health.available is True
        assert health.latency_ms is not None
        assert health.error is None
    
    def test_available_models(self, mock_provider):
        """Test listing available models"""
        models = mock_provider.get_available_models()
        
        assert len(models) > 0
        assert "mock/default" in models
    
    def test_token_estimation(self, mock_provider):
        """Test token estimation"""
        text = "This is a test sentence with several words."
        tokens = mock_provider.estimate_tokens(text)
        
        assert tokens > 0
        assert tokens < len(text)  # Tokens should be fewer than characters
    
    @pytest.mark.asyncio
    async def test_failure_simulation(self):
        """Test failure rate simulation"""
        failing_provider = MockProvider(failure_rate=1.0)  # 100% failure
        
        response = await failing_provider.generate(
            prompt="Test",
            model="mock/default",
        )
        
        assert response.success is False
        assert response.error is not None


# ============================================
# Cost Calculator Tests
# ============================================

class TestCostCalculator:
    """Tests for cost calculator"""
    
    def test_calculate_cost(self, cost_calculator):
        """Test cost calculation"""
        breakdown = cost_calculator.calculate_cost(
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500,
        )
        
        assert breakdown.total_cost_usd > 0
        assert breakdown.input_cost_usd >= 0
        assert breakdown.output_cost_usd >= 0
        assert breakdown.total_cost_usd == breakdown.input_cost_usd + breakdown.output_cost_usd
    
    def test_estimate_cost(self, cost_calculator):
        """Test cost estimation"""
        estimated = cost_calculator.estimate_cost(
            model="gpt-4o",
            text="This is a test text for estimation.",
        )
        
        assert estimated >= 0
    
    def test_get_cheapest_model(self, cost_calculator):
        """Test finding cheapest model"""
        models = ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet-20241022"]
        cheapest = cost_calculator.get_cheapest_model(models)
        
        assert cheapest in models
        # gpt-4o-mini should be cheapest
        assert cheapest == "gpt-4o-mini"
    
    def test_record_and_summary(self, cost_calculator):
        """Test recording costs and getting summary"""
        cost_calculator.record_cost("gpt-4o", "openai", 0.001)
        cost_calculator.record_cost("gpt-4o", "openai", 0.002)
        cost_calculator.record_cost("claude-3-5-sonnet-20241022", "anthropic", 0.003)
        
        summary = cost_calculator.get_cost_summary()
        
        assert summary["total_cost_usd"] == 0.006
        assert summary["cost_by_model"]["gpt-4o"] == 0.003
        assert summary["cost_by_provider"]["openai"] == 0.003
    
    def test_compare_models(self, cost_calculator):
        """Test model cost comparison"""
        comparisons = cost_calculator.compare_models(
            models=["gpt-4o", "gpt-4o-mini"],
            input_tokens=1000,
            output_tokens=500,
        )
        
        assert len(comparisons) == 2
        # Should be sorted by cost (cheapest first)
        assert comparisons[0]["total_cost"] <= comparisons[1]["total_cost"]


# ============================================
# Metrics Collector Tests
# ============================================

class TestMetricsCollector:
    """Tests for metrics collector"""
    
    def test_record_metric(self, metrics_collector):
        """Test recording a metric"""
        metric = RequestMetric(
            timestamp=datetime.utcnow(),
            request_id="test-123",
            model="gpt-4o",
            provider="openai",
            task="summarize",
            preference="balanced",
            total_time_ms=500,
            routing_time_ms=10,
            inference_time_ms=480,
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            success=True,
            cached=False,
            fallback_used=False,
        )
        
        metrics_collector.record(metric)
        
        assert metrics_collector.total_requests_processed == 1
    
    def test_aggregate_metrics(self, metrics_collector):
        """Test metrics aggregation"""
        # Record multiple metrics
        for i in range(10):
            metric = RequestMetric(
                timestamp=datetime.utcnow(),
                request_id=f"test-{i}",
                model="gpt-4o",
                provider="openai",
                task="summarize",
                preference="balanced",
                total_time_ms=500 + i * 10,
                routing_time_ms=10,
                inference_time_ms=480,
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.001,
                success=i < 9,  # 1 failure
                cached=i == 5,  # 1 cached
                fallback_used=False,
            )
            metrics_collector.record(metric)
        
        agg = metrics_collector.aggregate()
        
        assert agg.total_requests == 10
        assert agg.successful_requests == 9
        assert agg.failed_requests == 1
        assert agg.cached_requests == 1
        assert agg.error_rate_percent == 10.0
    
    def test_model_performance(self, metrics_collector):
        """Test getting model-specific performance"""
        # Record metrics for specific model
        for i in range(5):
            metric = RequestMetric(
                timestamp=datetime.utcnow(),
                request_id=f"test-{i}",
                model="gpt-4o-mini",
                provider="openai",
                task="chat",
                preference="fast",
                total_time_ms=300,
                routing_time_ms=5,
                inference_time_ms=290,
                input_tokens=50,
                output_tokens=100,
                cost_usd=0.0001,
                success=True,
                cached=False,
                fallback_used=False,
            )
            metrics_collector.record(metric)
        
        perf = metrics_collector.get_model_performance("gpt-4o-mini")
        
        assert perf["total_requests"] == 5
        assert perf["success_rate"] == 1.0
        assert perf["avg_latency_ms"] == 300


# ============================================
# Local Storage Tests
# ============================================

class TestLocalStorage:
    """Tests for local storage"""
    
    def test_put_and_get_log(self, local_storage):
        """Test storing and retrieving logs"""
        log_entry = {
            "request_id": "log-123",
            "model": "gpt-4o",
            "success": True,
        }
        
        result = local_storage.put_log(log_entry)
        assert result is True
        
        logs = local_storage.get_logs(limit=10)
        assert len(logs) == 1
        assert logs[0]["request_id"] == "log-123"
    
    def test_put_and_get_job(self, local_storage):
        """Test storing and retrieving jobs"""
        job_data = {
            "status": "pending",
            "request": {"text": "test"},
        }
        
        local_storage.put_job("job-123", job_data)
        
        job = local_storage.get_job("job-123")
        assert job is not None
        assert job["status"] == "pending"
    
    def test_update_job(self, local_storage):
        """Test updating a job"""
        local_storage.put_job("job-456", {"status": "pending"})
        
        result = local_storage.update_job("job-456", {"status": "completed"})
        assert result is True
        
        job = local_storage.get_job("job-456")
        assert job["status"] == "completed"
    
    def test_delete_job(self, local_storage):
        """Test deleting a job"""
        local_storage.put_job("job-789", {"status": "pending"})
        
        result = local_storage.delete_job("job-789")
        assert result is True
        
        job = local_storage.get_job("job-789")
        assert job is None
    
    def test_storage_stats(self, local_storage):
        """Test getting storage statistics"""
        local_storage.put_log({"id": 1})
        local_storage.put_job("job-1", {"status": "pending"})
        
        stats = local_storage.get_stats()
        
        assert stats["total_logs"] == 1
        assert stats["total_jobs"] == 1
    
    def test_clear_storage(self, local_storage):
        """Test clearing storage"""
        local_storage.put_log({"id": 1})
        local_storage.put_job("job-1", {})
        
        local_storage.clear()
        
        stats = local_storage.get_stats()
        assert stats["total_logs"] == 0
        assert stats["total_jobs"] == 0


# ============================================
# Request Model Tests
# ============================================

class TestRequestModels:
    """Tests for request models"""
    
    def test_valid_request(self, sample_request):
        """Test valid request creation"""
        assert sample_request.task == TaskType.SUMMARIZE
        assert sample_request.model_preference == ModelPreference.BALANCED
        assert len(sample_request.text) > 0
    
    def test_request_defaults(self):
        """Test request defaults"""
        request = GenerateRequest(text="Test text")
        
        assert request.task == TaskType.CHAT
        assert request.model_preference == ModelPreference.BALANCED
        assert request.max_tokens is None
        assert request.temperature is None
    
    def test_request_validation(self):
        """Test request validation"""
        # Empty text should fail
        with pytest.raises(ValueError):
            GenerateRequest(text="")
        
        # Whitespace-only text should fail
        with pytest.raises(ValueError):
            GenerateRequest(text="   ")
    
    def test_all_task_types(self):
        """Test all task types are valid"""
        for task in TaskType:
            request = GenerateRequest(task=task, text="Test")
            assert request.task == task
    
    def test_all_preferences(self):
        """Test all preferences are valid"""
        for pref in ModelPreference:
            request = GenerateRequest(model_preference=pref, text="Test")
            assert request.model_preference == pref


# ============================================
# Integration Tests
# ============================================

class TestIntegration:
    """Integration tests combining multiple components"""
    
    @pytest.mark.asyncio
    async def test_full_request_flow(self, mock_provider, cost_calculator, metrics_collector):
        """Test complete request flow"""
        # 1. Generate response
        response = await mock_provider.generate(
            prompt="Summarize this text",
            model="mock/default",
            task_type="summarize",
        )
        
        assert response.success is True
        
        # 2. Calculate cost
        cost = cost_calculator.calculate_cost(
            model="gpt-4o-mini",
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
        
        assert cost.total_cost_usd >= 0
        
        # 3. Record metric
        metric = RequestMetric(
            timestamp=datetime.utcnow(),
            request_id="integration-test",
            model="mock/default",
            provider="mock",
            task="summarize",
            preference="balanced",
            total_time_ms=response.latency_ms,
            routing_time_ms=5,
            inference_time_ms=response.latency_ms - 5,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cost_usd=cost.total_cost_usd,
            success=response.success,
            cached=False,
            fallback_used=False,
        )
        metrics_collector.record(metric)
        
        # 4. Verify metrics
        agg = metrics_collector.aggregate()
        assert agg.total_requests >= 1


# ============================================
# Run tests
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])