FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.5 \
    POETRY_VIRTUALENVS_CREATE=false

# build-essential/libffi/libpq cover cffi-based bcrypt 3.2.2 and psycopg builds.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libffi-dev libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install "poetry==${POETRY_VERSION}"

WORKDIR /app

# Dependency layer (cached unless pyproject/lock change)
COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root

# Application code (includes alembic.ini + alembic/ for migrations)
COPY . .

EXPOSE 8150
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8150}"]
