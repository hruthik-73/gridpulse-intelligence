.PHONY: install sync test lint format typecheck check tree clean \
	kafka-up kafka-init kafka-topics kafka-logs kafka-down kafka-status


# ============================================================
# PYTHON / PROJECT SETUP
# ============================================================

install:
	uv sync

sync:
	uv sync


# ============================================================
# CODE QUALITY
# ============================================================

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src
	uv run pytest


# ============================================================
# PROJECT UTILITIES
# ============================================================

tree:
	tree -a -I '.git|.venv|__pycache__|.pytest_cache|.mypy_cache|.ruff_cache|node_modules|data/raw|data/processed|data/quarantine'

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete


# ============================================================
# KAFKA LOCAL DEVELOPMENT
# ============================================================

kafka-up:
	docker compose -f infrastructure/docker/docker-compose.kafka.yml up -d

kafka-init:
	./scripts/kafka-init.sh

kafka-topics:
	docker exec gridpulse-kafka \
		/opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 \
		--list

kafka-logs:
	docker logs gridpulse-kafka --tail 100

kafka-status:
	docker ps --filter name=gridpulse-kafka

kafka-down:
	docker compose -f infrastructure/docker/docker-compose.kafka.yml down

.PHONY: dbt-debug dbt-build dbt-test dbt-docs analytics

dbt-debug:
	uv run dbt debug --project-dir analytics/dbt --profiles-dir analytics/dbt

dbt-build:
	uv run dbt build --project-dir analytics/dbt --profiles-dir analytics/dbt

dbt-test:
	uv run dbt test --project-dir analytics/dbt --profiles-dir analytics/dbt

dbt-docs:
	uv run dbt docs generate --project-dir analytics/dbt --profiles-dir analytics/dbt

analytics:
	uv run python pipelines/streaming/bronze_to_silver.py
	uv run python pipelines/analytics/build_gold.py
	uv run dbt build --project-dir analytics/dbt --profiles-dir analytics/dbt


.PHONY: observability-up observability-down observability-logs observability-status

observability-up:
	docker compose -f infrastructure/docker/docker-compose.observability.yml up -d

observability-down:
	docker compose -f infrastructure/docker/docker-compose.observability.yml down

observability-logs:
	docker compose -f infrastructure/docker/docker-compose.observability.yml logs --tail 100

observability-status:
	docker compose -f infrastructure/docker/docker-compose.observability.yml ps
