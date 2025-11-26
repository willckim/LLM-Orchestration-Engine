"""
LLM Orchestration Engine - Configuration
Enterprise-grade settings with environment-based configuration
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    app_name: str = "LLM Orchestration Engine"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    
    # API Security
    api_key_header: str = "X-API-Key"
    api_keys: str = Field(default="dev-key-123,test-key-456", alias="API_KEYS")
    
    # LLM Providers
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    azure_openai_api_key: Optional[str] = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_version: str = Field(default="2024-02-15-preview", alias="AZURE_OPENAI_API_VERSION")
    
    # AWS Configuration
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_access_key_id: Optional[str] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    dynamodb_table_name: str = Field(default="llm-orchestration-logs", alias="DYNAMODB_TABLE_NAME")
    s3_bucket_name: str = Field(default="llm-orchestration-outputs", alias="S3_BUCKET_NAME")
    
    # Storage Mode
    use_local_storage: bool = Field(default=True, alias="USE_LOCAL_STORAGE")
    local_storage_path: str = Field(default="./data/logs.json", alias="LOCAL_STORAGE_PATH")
    
    # Model Routing Defaults
    default_preference: str = Field(default="balanced", alias="DEFAULT_PREFERENCE")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    timeout_seconds: int = Field(default=30, alias="TIMEOUT_SECONDS")
    
    # Cost Thresholds (USD per 1K tokens)
    cost_threshold_cheap: float = 0.001  # Below this = "cheap"
    cost_threshold_moderate: float = 0.01  # Below this = "moderate"
    
    # Performance Thresholds
    latency_threshold_fast_ms: int = 500  # Below this = "fast"
    latency_threshold_moderate_ms: int = 2000
    
    # Local ONNX Model Settings
    enable_local_models: bool = Field(default=True, alias="ENABLE_LOCAL_MODELS")
    local_model_path: str = Field(default="./models", alias="LOCAL_MODEL_PATH")
    
    # Metrics & Observability
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")
    metrics_retention_days: int = Field(default=30, alias="METRICS_RETENTION_DAYS")
    
    @property
    def valid_api_keys(self) -> set:
        """Parse comma-separated API keys into a set"""
        return set(key.strip() for key in self.api_keys.split(",") if key.strip())
    
    @property
    def available_providers(self) -> list:
        """Return list of configured providers"""
        providers = []
        if self.openai_api_key:
            providers.append("openai")
        if self.anthropic_api_key:
            providers.append("anthropic")
        if self.azure_openai_api_key and self.azure_openai_endpoint:
            providers.append("azure")
        if self.enable_local_models:
            providers.append("local")
        # Always include mock for testing
        providers.append("mock")
        return providers
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()


# Model pricing (USD per 1K tokens) - Updated May 2025
MODEL_PRICING = {
    # OpenAI
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    
    # Anthropic
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    
    # Azure OpenAI (same as OpenAI but may vary by region)
    "azure/gpt-4o": {"input": 0.0025, "output": 0.01},
    "azure/gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    
    # AWS Bedrock
    "bedrock/anthropic.claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "bedrock/anthropic.claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "bedrock/meta.llama3-70b-instruct": {"input": 0.00265, "output": 0.0035},
    
    # Local (free!)
    "local/sentiment": {"input": 0.0, "output": 0.0},
    "local/classifier": {"input": 0.0, "output": 0.0},
    
    # Mock (for testing)
    "mock/default": {"input": 0.0, "output": 0.0},
}

# Model capabilities and characteristics
MODEL_CAPABILITIES = {
    "gpt-4o": {
        "tasks": ["summarize", "sentiment", "rewrite", "tools", "chat", "code", "analysis"],
        "max_tokens": 128000,
        "avg_latency_ms": 1500,
        "quality_score": 0.95,
        "provider": "openai",
    },
    "gpt-4o-mini": {
        "tasks": ["summarize", "sentiment", "rewrite", "chat", "code"],
        "max_tokens": 128000,
        "avg_latency_ms": 800,
        "quality_score": 0.85,
        "provider": "openai",
    },
    "claude-3-5-sonnet-20241022": {
        "tasks": ["summarize", "sentiment", "rewrite", "tools", "chat", "code", "analysis"],
        "max_tokens": 200000,
        "avg_latency_ms": 1200,
        "quality_score": 0.95,
        "provider": "anthropic",
    },
    "claude-3-5-haiku-20241022": {
        "tasks": ["summarize", "sentiment", "rewrite", "chat"],
        "max_tokens": 200000,
        "avg_latency_ms": 500,
        "quality_score": 0.80,
        "provider": "anthropic",
    },
    "local/sentiment": {
        "tasks": ["sentiment"],
        "max_tokens": 512,
        "avg_latency_ms": 50,
        "quality_score": 0.75,
        "provider": "local",
    },
    "local/classifier": {
        "tasks": ["classify"],
        "max_tokens": 512,
        "avg_latency_ms": 30,
        "quality_score": 0.70,
        "provider": "local",
    },
    "mock/default": {
        "tasks": ["summarize", "sentiment", "rewrite", "tools", "chat", "code", "analysis"],
        "max_tokens": 4096,
        "avg_latency_ms": 100,
        "quality_score": 0.5,
        "provider": "mock",
    },
}