# 🚀 LLM Orchestration Engine

**Enterprise-grade multi-model LLM routing with intelligent cost optimization, observability, and automatic fallbacks.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 Overview

A production-ready AI infrastructure service that intelligently routes LLM requests to the optimal model based on task type, cost constraints, latency requirements, and real-time provider health. Built for enterprise scalability with comprehensive observability.

### Why This Project?

Most LLM applications hardcode a single provider. This engine demonstrates enterprise patterns:

- **Multi-model routing** - Automatically select the best model for each task
- **Cost optimization** - Track spending and route to cheaper models when appropriate
- **Resilience** - Automatic fallbacks when providers fail
- **Observability** - Real-time metrics, dashboards, and alerting
- **Scalability** - Serverless-ready architecture (AWS Lambda + Step Functions)

---

## ✨ Features

### Intelligent Model Routing
- **Task-aware selection**: Different models excel at different tasks (summarization, sentiment, code, etc.)
- **Preference-based routing**: Optimize for `fast`, `cheap`, `best`, or `balanced`
- **Dynamic scoring**: Real-time model scoring based on cost, latency, quality, and availability
- **Constraint support**: Set max cost or max latency limits per request

### Multi-Provider Support
| Provider | Models | Status |
|----------|--------|--------|
| OpenAI | GPT-4o, GPT-4o-mini, GPT-4-turbo | ✅ Ready |
| Anthropic | Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 3 Opus | ✅ Ready |
| Azure OpenAI | GPT-4o, GPT-4o-mini | ✅ Ready |
| AWS Bedrock | Claude, Llama 3 | 🔧 Configured |
| Local ONNX | Sentiment, Classifier | 🔧 Planned |

### Cost Optimization
- Real-time cost tracking per request
- Cost comparison across models
- Savings calculation vs. most expensive alternative
- Budget alerts and limits

### Observability
- Request logging with full context
- P50/P95/P99 latency metrics
- Provider health monitoring
- CloudWatch-compatible metric export
- Real-time dashboard data

### Enterprise Ready
- API key authentication (Cognito-ready)
- Rate limiting support
- Async processing via Step Functions
- Docker + Kubernetes ready
- Terraform infrastructure as code

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway                              │
│                    (FastAPI / Lambda)                            │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Model Router                                │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Task        │  │ Preference   │  │ Constraint             │  │
│  │ Classifier  │──│ Weights      │──│ Validator              │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Model Scorer                            │  │
│  │  Cost Score │ Latency Score │ Quality Score │ Availability │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │  OpenAI  │        │ Anthropic│        │  Azure   │
    │ Provider │        │ Provider │        │ Provider │
    └──────────┘        └──────────┘        └──────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Observability Layer                           │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────┐   │
│  │ Metrics      │  │ Cost          │  │ Request             │   │
│  │ Collector    │  │ Calculator    │  │ Logger              │   │
│  └──────────────┘  └───────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- (Optional) Docker
- (Optional) API keys for OpenAI/Anthropic

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/llm-orchestration-engine.git
cd llm-orchestration-engine/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your API keys (optional - works without for mock mode)

# Run the server
uvicorn app.main:app --reload
```

### Docker

```bash
# Build and run
docker-compose up --build

# Or use pre-built image
docker run -p 8000:8000 -e API_KEYS=your-key llm-orchestration-engine
```

---

## 📖 API Usage

### Generate Text

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/generate",
    headers={"X-API-Key": "dev-key-123"},
    json={
        "task": "summarize",
        "model_preference": "balanced",
        "text": "Your long text to summarize here..."
    }
)

result = response.json()
print(f"Model used: {result['routing']['selected_model']}")
print(f"Cost: ${result['usage']['total_cost_usd']:.6f}")
print(f"Result: {result['result']}")
```

### Available Tasks

| Task | Description | Best For |
|------|-------------|----------|
| `summarize` | Condense text to key points | Articles, documents |
| `sentiment` | Analyze emotional tone (returns JSON) | Reviews, feedback |
| `rewrite` | Improve clarity and style | Editing, polish |
| `chat` | General conversation | Chatbots, Q&A |
| `code` | Generate/analyze code | Development |
| `analysis` | Deep content analysis | Research, reports |
| `tools` | Tool-calling tasks | Agents, automation |

### Model Preferences

| Preference | Behavior |
|------------|----------|
| `fast` | Prioritize low latency (60% weight on speed) |
| `cheap` | Prioritize low cost (60% weight on price) |
| `best` | Prioritize quality (60% weight on capability) |
| `balanced` | Equal consideration of all factors |

### Response Structure

```json
{
  "success": true,
  "result": "Generated text...",
  "request_id": "req_abc123",
  "routing": {
    "selected_model": "gpt-4o-mini",
    "provider": "openai",
    "reason": "Best cost-latency balance for summarization",
    "cost_score": 0.9,
    "latency_score": 0.85,
    "quality_score": 0.8,
    "final_score": 0.87
  },
  "usage": {
    "input_tokens": 150,
    "output_tokens": 50,
    "total_cost_usd": 0.0000525
  },
  "performance": {
    "total_time_ms": 850,
    "routing_time_ms": 5,
    "inference_time_ms": 820
  }
}
```

---

## 📊 Observability

### Metrics Dashboard

Access real-time metrics at `GET /api/v1/metrics/summary`:

```json
{
  "requests": {
    "total": 1000,
    "successful": 985,
    "failed": 15
  },
  "latency_ms": {
    "p50": 450,
    "p95": 1200,
    "p99": 2500
  },
  "costs": {
    "total_usd": 1.25,
    "by_model": {"gpt-4o-mini": 0.75, "claude-3-5-haiku": 0.50}
  }
}
```

### Available Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/metrics/summary` | Aggregated metrics |
| `GET /api/v1/metrics/models/{model}` | Per-model performance |
| `GET /api/v1/metrics/providers` | Provider health status |
| `GET /api/v1/metrics/costs` | Cost breakdown |
| `GET /api/v1/metrics/logs` | Recent request logs |
| `GET /api/v1/metrics/realtime` | Real-time stats |

---

## 🏭 Production Deployment

### AWS Lambda + API Gateway

```bash
# Deploy with Terraform
cd infrastructure/terraform
terraform init
terraform plan -var="environment=prod"
terraform apply
```

### Render (Hybrid Approach)

1. Connect GitHub repository
2. Set environment variables in Render dashboard
3. Deploy with Dockerfile

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `API_KEYS` | Yes | Comma-separated valid API keys |
| `OPENAI_API_KEY` | No | OpenAI API key |
| `ANTHROPIC_API_KEY` | No | Anthropic API key |
| `ENVIRONMENT` | No | `development` or `production` |
| `USE_LOCAL_STORAGE` | No | Use JSON storage vs DynamoDB |

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py -v
```

---

## 📁 Project Structure

```
llm-orchestration-engine/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration & pricing
│   │   ├── models/              # Pydantic schemas
│   │   ├── routers/             # API endpoints
│   │   ├── services/            # Business logic
│   │   │   ├── router.py        # Model routing engine
│   │   │   ├── providers/       # LLM provider adapters
│   │   │   ├── cost_calculator.py
│   │   │   └── metrics_collector.py
│   │   └── db/                  # Storage adapters
│   ├── lambda_handler.py        # AWS Lambda entry point
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── infrastructure/
│   └── terraform/               # AWS IaC
├── tests/
└── docs/
```

---

## 🛣️ Roadmap

- [x] Phase 1: Core routing engine
- [x] Phase 2: Multi-provider support (OpenAI, Anthropic)
- [x] Phase 3: Observability & metrics
- [ ] Phase 4: AWS Lambda deployment
- [ ] Phase 5: Step Functions async processing
- [ ] Phase 6: CloudWatch dashboards
- [ ] Phase 7: Local ONNX models
- [ ] Phase 8: Caching layer

---

## 🤝 Contributing

Contributions welcome! Please read the contributing guidelines first.

---

## 📄 License

MIT License - see LICENSE file for details.

---

## 👤 Author

Built as an enterprise AI infrastructure portfolio project demonstrating:
- Multi-model LLM orchestration
- Cost optimization strategies
- Production-grade observability
- Serverless AWS architecture
- Clean, maintainable Python

---

*Ready to showcase enterprise AI infrastructure skills? This is it.* 🎯