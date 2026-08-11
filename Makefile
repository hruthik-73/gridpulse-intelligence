.PHONY: help install sync test lint format typecheck check clean tree

help:
	@echo "GridPulse Intelligence"
	@echo ""
	@echo "make install    Install project dependencies"
	@echo "make sync       Sync uv environment"
	@echo "make test       Run tests"
	@echo "make lint       Run Ruff linting"
	@echo "make format     Format Python code"
	@echo "make typecheck  Run mypy"
	@echo "make check      Run all quality checks"
	@echo "make tree       Show project structure"
	@echo "make clean      Remove local caches"

install:
	uv sync --all-groups

sync:
	uv sync --all-groups

test:
	uv run pytest -v

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

tree:
	tree -a -I '.git|.venv|__pycache__|node_modules|.pytest_cache|.mypy_cache|.ruff_cache'

clean:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
