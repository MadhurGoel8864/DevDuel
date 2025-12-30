# Project settings
PROJECT_NAME=go-pool
APP_MODULE=app.main:app
HOST=127.0.0.1
PORT=8000

# Use tabs, not spaces, in Makefiles!

.PHONY: help install run dev stop test lint format clean

help:
	@echo "Available commands:"
	@echo "  make install     Install dependencies"
	@echo "  make run         Run app (production)"
	@echo "  make dev         Run app with reload"
	@echo "  make test        Run tests"
	@echo "  make lint        Run lint checks"
	@echo "  make format      Format code"
	@echo "  make clean       Remove cache files"


install:
	poetry install

dev:
	poetry run uvicorn $(APP_MODULE) --reload --host $(HOST) --port $(PORT)

.PHONY: run
run:
	poetry run uvicorn $(APP_MODULE) --host $(HOST) --port $(PORT)


migrate:
	poetry run alembic upgrade head

# migration:
# 	poetry run alembic revision --autogenerate -m "auto migration"
.PHONY: migration
migration:
	if [ -z "$(m)" ]; then \
		alembic revision --autogenerate; \
	else \
		alembic revision --autogenerate -m "$(m)"; \
	fi

fmt:
	poetry run black .
# 	poetry run isort .

lint:
	poetry run flake8 .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete


type-check:
	poetry run mypy


.PHONY: rollback
rollback:
	alembic downgrade -$(n)

# Default value for n is 1 if not specified
n ?= 1



.PHONY: run
run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8150
