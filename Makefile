# Career Coach AI Makefile

.PHONY: help install run clean test lint format dev

# Default target
help:
	@echo "Available commands:"
	@echo "  install    - Install dependencies with uv"
	@echo "  run        - Run the career coach application"
	@echo "  dev        - Install in development mode and run"
	@echo "  clean      - Clean build artifacts and cache"
	@echo "  test       - Run tests (if any)"
	@echo "  lint       - Run linting checks"
	@echo "  format     - Format code"
	@echo "  sync       - Sync dependencies (update lock file)"

# Install dependencies
install:
	uv sync

# Run the application
run:
	uv run python app.py

# Development setup and run
dev: install run

# Clean build artifacts and cache
clean:
	rm -rf .venv/
	rm -rf __pycache__/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Test the tools functionality
test:
	uv run python tools.py

# Sync dependencies (update lock file)
sync:
	uv sync

# Run linting (if ruff is available)
lint:
	@if uv run python -c "import ruff" 2>/dev/null; then \
		uv run ruff check .; \
	else \
		echo "Ruff not installed, skipping lint"; \
	fi

# Format code (if ruff is available)
format:
	@if uv run python -c "import ruff" 2>/dev/null; then \
		uv run ruff format .; \
	else \
		echo "Ruff not installed, skipping format"; \
	fi

# Fresh install (clean + install)
fresh: clean install

# Show project info
info:
	@echo "Career Coach AI Project"
	@echo "======================"
	@uv --version
	@echo "Python version:"
	@uv run python --version
	@echo "Project dependencies:"
	@uv tree