"""
LLM Orchestration Engine
Enterprise-grade multi-model LLM routing, observability, and cost optimization

A production-ready AI infrastructure service that:
- Routes requests to optimal models based on task, cost, and latency
- Provides real-time observability and metrics
- Handles fallbacks and retries automatically
- Tracks costs and optimizes spending
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .routers import generate_router, health_router, metrics_router

# Startup/shutdown lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    settings = get_settings()
    
    # Startup
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"📍 Environment: {settings.environment}")
    print(f"🔌 Available providers: {settings.available_providers}")
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")


# Create FastAPI app
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## LLM Orchestration Engine

Enterprise-grade multi-model LLM routing with intelligent cost and latency optimization.

### Features

- **🧠 Intelligent Routing**: Automatically selects the optimal model based on task type, user preferences, and real-time metrics
- **💰 Cost Optimization**: Tracks and minimizes costs while maintaining quality
- **⚡ Low Latency**: Routes to fastest available model when speed is priority
- **🔄 Automatic Fallbacks**: Seamlessly handles provider failures
- **📊 Real-time Observability**: Comprehensive metrics and dashboards
- **🔐 API Key Authentication**: Secure access control

### Quick Start

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/generate",
    headers={"X-API-Key": "dev-key-123"},
    json={
        "task": "summarize",
        "model_preference": "balanced",
        "text": "Your text to summarize here..."
    }
)
print(response.json())
```

### Model Preferences

| Preference | Description |
|------------|-------------|
| `fast` | Prioritize low latency |
| `cheap` | Prioritize low cost |
| `best` | Prioritize quality |
| `balanced` | Balance all factors |
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    """Add server timing headers"""
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time-Ms"] = str(round(process_time, 2))
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "error_code": "INTERNAL_ERROR",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


# Include routers
app.include_router(health_router)
app.include_router(generate_router)
app.include_router(metrics_router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "api": {
            "generate": "POST /api/v1/generate",
            "models": "GET /api/v1/models",
            "metrics": "GET /api/v1/metrics/summary",
        }
    }


# For running directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )