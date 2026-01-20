# Dagster Cloud Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

# Add poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (no dev deps for prod image)
RUN poetry install --without dev --no-root

# Copy project source code
COPY . .

# Install the project itself
RUN poetry install --without dev

# Expose port for Dagster (default 3000)
EXPOSE 3000

# Set entry point for Dagster (used by Serverless)
# The actual command is often overridden by Dagster Cloud agent, but this is a good default
CMD ["poetry", "run", "dagster", "api", "grpc", "-h", "0.0.0.0", "-p", "3000", "-m", "orchestration"]
