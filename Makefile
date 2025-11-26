# LLM Orchestration Engine - Makefile
# Common development commands

.PHONY: help install dev test lint format run docker-build docker-run clean

# Default target
help:
	@echo "LLM Orchestration Engine - Available Commands"
	@echo "=============================================="
	@echo ""
	@echo "Development:"
	@echo "  make install       - Install all dependencies"
	@echo "  make dev           - Run backend dev server"
	@echo "  make dev-frontend  - Run frontend dev server"
	@echo "  make dev-all       - Run both backend and frontend"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linter"
	@echo "  make format        - Format code"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  - Build Docker images"
	@echo "  make docker-run    - Run Docker container"
	@echo "  make docker-up     - Start with docker-compose"
	@echo "  make docker-down   - Stop docker-compose"
	@echo ""
	@echo "Production:"
	@echo "  make deploy-tf     - Deploy with Terraform"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make docs          - Generate API docs"

# ============================================
# Development
# ============================================

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev-all:
	@echo "Starting backend and frontend..."
	@make -j2 dev dev-frontend

test:
	cd backend && pytest ../tests -v --tb=short

test-cov:
	cd backend && pytest ../tests -v --cov=app --cov-report=html --cov-report=term

lint:
	cd backend && ruff check app/

format:
	cd backend && black app/ && ruff check --fix app/

# ============================================
# Docker
# ============================================

docker-build:
	cd backend && docker build -t llm-orchestration-engine .

docker-run:
	docker run -p 8000:8000 \
		-e API_KEYS=dev-key-123 \
		-e ENVIRONMENT=development \
		llm-orchestration-engine

docker-up:
	cd backend && docker-compose up -d

docker-down:
	cd backend && docker-compose down

docker-logs:
	cd backend && docker-compose logs -f

# ============================================
# AWS / Terraform
# ============================================

tf-init:
	cd infrastructure/terraform && terraform init

tf-plan:
	cd infrastructure/terraform && terraform plan

tf-apply:
	cd infrastructure/terraform && terraform apply

tf-destroy:
	cd infrastructure/terraform && terraform destroy

deploy-tf: tf-init tf-apply

# ============================================
# Utilities
# ============================================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf backend/data/*.json 2>/dev/null || true

docs:
	@echo "API docs available at http://localhost:8000/docs"
	@echo "ReDoc available at http://localhost:8000/redoc"

# Quick demo
demo: install
	@echo "Starting demo server..."
	@echo "API will be available at http://localhost:8000"
	@echo "Docs at http://localhost:8000/docs"
	@echo ""
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000