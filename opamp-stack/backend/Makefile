.PHONY: help install dev test lint format clean build up down migrate create-migration logs

# Variables
DOCKER_COMPOSE = docker compose
BACKEND_SERVICE = opamp-backend
TEST_DB = sqlite:///test.db

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

dev: ## Install development dependencies
	pip install -r requirements.txt
	pre-commit install

test: ## Run tests
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-fast: ## Run tests without coverage
	pytest tests/ -v

lint: ## Run linting
	ruff check app/ tests/
	black --check app/ tests/

format: ## Format code
	black app/ tests/
	ruff --fix app/ tests/

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/

build: ## Build Docker image
	$(DOCKER_COMPOSE) build $(BACKEND_SERVICE)

up: ## Start services with docker-compose
	$(DOCKER_COMPOSE) --env-file .env up -d

down: ## Stop services
	$(DOCKER_COMPOSE) down

logs: ## Show logs
	$(DOCKER_COMPOSE) logs -f $(BACKEND_SERVICE)

migrate: ## Run database migrations
	$(DOCKER_COMPOSE) exec $(BACKEND_SERVICE) alembic upgrade head

create-migration: ## Create a new migration (usage: make create-migration MESSAGE="description")
	$(DOCKER_COMPOSE) exec $(BACKEND_SERVICE) alembic revision --autogenerate -m "$(MESSAGE)"

shell: ## Open a shell in the backend container
	$(DOCKER_COMPOSE) exec $(BACKEND_SERVICE) /bin/bash

# Local development commands (without Docker)
run-local: ## Run the application locally
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

migrate-local: ## Run migrations locally
	alembic upgrade head

create-migration-local: ## Create migration locally (usage: make create-migration-local MESSAGE="description")
	alembic revision --autogenerate -m "$(MESSAGE)"

setup-dev: ## Setup development environment
	@echo "Setting up development environment..."
	cp .env.example .env
	@echo "Please edit .env file with your configuration"
	@echo "Then run: make dev && make migrate-local"