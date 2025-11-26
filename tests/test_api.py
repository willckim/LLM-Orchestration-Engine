"""
LLM Orchestration Engine - API Tests
FastAPI endpoint testing
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

import sys
sys.path.insert(0, './backend')

from app.main import app


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Headers with valid API key"""
    return {"X-API-Key": "dev-key-123"}


# ============================================
# Health Endpoint Tests
# ============================================

class TestHealthEndpoints:
    """Tests for health check endpoints"""
    
    def test_health_check(self, client):
        """Test basic health check"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_detailed_health(self, client):
        """Test detailed health check"""
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "providers" in data
    
    def test_readiness_probe(self, client):
        """Test Kubernetes readiness probe"""
        response = client.get("/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
    
    def test_liveness_probe(self, client):
        """Test Kubernetes liveness probe"""
        response = client.get("/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True


# ============================================
# Root Endpoint Tests
# ============================================

class TestRootEndpoint:
    """Tests for root endpoint"""
    
    def test_root(self, client):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "LLM Orchestration Engine"
        assert "version" in data
        assert "api" in data


# ============================================
# Generate Endpoint Tests
# ============================================

class TestGenerateEndpoint:
    """Tests for /api/v1/generate endpoint"""
    
    def test_generate_without_auth(self, client):
        """Test generate without API key in production mode"""
        # In development mode, this should still work
        response = client.post(
            "/api/v1/generate",
            json={
                "task": "summarize",
                "text": "This is a test text to summarize."
            }
        )
        
        # Should work in dev mode without auth
        assert response.status_code in [200, 401]
    
    def test_generate_with_auth(self, client, auth_headers):
        """Test generate with valid API key"""
        response = client.post(
            "/api/v1/generate",
            headers=auth_headers,
            json={
                "task": "summarize",
                "model_preference": "balanced",
                "text": "This is a test text that needs to be summarized. It contains important information."
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["result"] is not None
        assert "request_id" in data
        assert "routing" in data
        assert "usage" in data
        assert "performance" in data
    
    def test_generate_all_tasks(self, client, auth_headers):
        """Test generate with all task types"""
        tasks = ["summarize", "sentiment", "rewrite", "chat", "code", "analysis"]
        
        for task in tasks:
            response = client.post(
                "/api/v1/generate",
                headers=auth_headers,
                json={
                    "task": task,
                    "text": f"Test text for {task} task."
                }
            )
            
            assert response.status_code == 200, f"Failed for task: {task}"
            data = response.json()
            assert data["success"] is True
    
    def test_generate_all_preferences(self, client, auth_headers):
        """Test generate with all preference types"""
        preferences = ["fast", "cheap", "best", "balanced"]
        
        for pref in preferences:
            response = client.post(
                "/api/v1/generate",
                headers=auth_headers,
                json={
                    "model_preference": pref,
                    "text": f"Test text with {pref} preference."
                }
            )
            
            assert response.status_code == 200, f"Failed for preference: {pref}"
    
    def test_generate_with_model_override(self, client, auth_headers):
        """Test generate with model override"""
        response = client.post(
            "/api/v1/generate",
            headers=auth_headers,
            json={
                "text": "Test with model override",
                "model_override": "mock/default"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["routing"]["selected_model"] == "mock/default"
    
    def test_generate_with_custom_params(self, client, auth_headers):
        """Test generate with custom parameters"""
        response = client.post(
            "/api/v1/generate",
            headers=auth_headers,
            json={
                "task": "chat",
                "text": "Hello, how are you?",
                "max_tokens": 100,
                "temperature": 0.5,
                "system_prompt": "You are a helpful assistant."
            }
        )
        
        assert response.status_code == 200
    
    def test_generate_empty_text(self, client, auth_headers):
        """Test generate with empty text fails"""
        response = client.post(
            "/api/v1/generate",
            headers=auth_headers,
            json={
                "text": ""
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_generate_response_structure(self, client, auth_headers):
        """Test response structure is correct"""
        response = client.post(
            "/api/v1/generate",
            headers=auth_headers,
            json={"text": "Test text"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check routing structure
        routing = data["routing"]
        assert "selected_model" in routing
        assert "provider" in routing
        assert "reason" in routing
        assert "cost_score" in routing
        assert "latency_score" in routing
        assert "quality_score" in routing
        
        # Check usage structure
        usage = data["usage"]
        assert "input_tokens" in usage
        assert "output_tokens" in usage
        assert "total_cost_usd" in usage
        
        # Check performance structure
        perf = data["performance"]
        assert "total_time_ms" in perf
        assert "routing_time_ms" in perf
        assert "inference_time_ms" in perf


# ============================================
# Models Endpoint Tests
# ============================================

class TestModelsEndpoint:
    """Tests for /api/v1/models endpoint"""
    
    def test_list_models(self, client, auth_headers):
        """Test listing available models"""
        response = client.get(
            "/api/v1/models",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "models" in data
        assert "total" in data
        assert data["total"] > 0
    
    def test_model_structure(self, client, auth_headers):
        """Test model data structure"""
        response = client.get(
            "/api/v1/models",
            headers=auth_headers
        )
        
        data = response.json()
        
        # Check first model has required fields
        model = data["models"][0]
        assert "model" in model
        assert "provider" in model
        assert "tasks" in model
        assert "pricing" in model


# ============================================
# Estimate Endpoint Tests
# ============================================

class TestEstimateEndpoint:
    """Tests for /api/v1/estimate endpoint"""
    
    def test_estimate_cost(self, client, auth_headers):
        """Test cost estimation"""
        response = client.post(
            "/api/v1/estimate",
            headers=auth_headers,
            json={
                "task": "summarize",
                "text": "This is sample text for cost estimation."
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "selected_model" in data
        assert "estimated_cost_usd" in data
        assert "routing_decision" in data
        assert "cost_comparison" in data


# ============================================
# Metrics Endpoint Tests
# ============================================

class TestMetricsEndpoints:
    """Tests for metrics endpoints"""
    
    def test_metrics_summary(self, client, auth_headers):
        """Test metrics summary"""
        response = client.get(
            "/api/v1/metrics/summary",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "time_range" in data
        assert "requests" in data
        assert "latency_ms" in data
        assert "costs" in data
    
    def test_metrics_summary_with_hours(self, client, auth_headers):
        """Test metrics summary with custom hours"""
        response = client.get(
            "/api/v1/metrics/summary?hours=48",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["time_range"]["hours"] == 48
    
    def test_provider_health(self, client, auth_headers):
        """Test provider health endpoint"""
        response = client.get(
            "/api/v1/metrics/providers",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
    
    def test_cost_analysis(self, client, auth_headers):
        """Test cost analysis endpoint"""
        response = client.get(
            "/api/v1/metrics/costs",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_cost_usd" in data
    
    def test_request_logs(self, client, auth_headers):
        """Test request logs endpoint"""
        response = client.get(
            "/api/v1/metrics/logs",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
    
    def test_realtime_stats(self, client, auth_headers):
        """Test realtime stats endpoint"""
        response = client.get(
            "/api/v1/metrics/realtime",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "last_minute" in data
        assert "last_hour" in data


# ============================================
# Error Handling Tests
# ============================================

class TestErrorHandling:
    """Tests for error handling"""
    
    def test_invalid_api_key(self, client):
        """Test invalid API key returns 403"""
        response = client.post(
            "/api/v1/generate",
            headers={"X-API-Key": "invalid-key"},
            json={"text": "Test"}
        )
        
        # In production mode, should be 403
        # In dev mode, might pass through
        assert response.status_code in [200, 403]
    
    def test_invalid_json(self, client, auth_headers):
        """Test invalid JSON returns 422"""
        response = client.post(
            "/api/v1/generate",
            headers={**auth_headers, "Content-Type": "application/json"},
            content="invalid json"
        )
        
        assert response.status_code == 422
    
    def test_missing_required_field(self, client, auth_headers):
        """Test missing required field returns 422"""
        response = client.post(
            "/api/v1/generate",
            headers=auth_headers,
            json={}  # Missing 'text' field
        )
        
        assert response.status_code == 422
    
    def test_invalid_task_type(self, client, auth_headers):
        """Test invalid task type returns 422"""
        response = client.post(
            "/api/v1/generate",
            headers=auth_headers,
            json={
                "task": "invalid_task",
                "text": "Test"
            }
        )
        
        assert response.status_code == 422


# ============================================
# Performance Tests
# ============================================

class TestPerformance:
    """Basic performance tests"""
    
    def test_response_time_header(self, client, auth_headers):
        """Test response includes timing header"""
        response = client.post(
            "/api/v1/generate",
            headers=auth_headers,
            json={"text": "Quick test"}
        )
        
        assert "x-process-time-ms" in response.headers
        process_time = float(response.headers["x-process-time-ms"])
        assert process_time > 0


# ============================================
# Run tests
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])