# Dagster Cloud Dockerfile
FROM python:3.11-slim

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
# --frozen: install from lockfile (will fail if lockfile is out of sync)
# --no-dev: exclude dev dependencies
# --no-install-project: install dependencies only, not the project itself yet (cached layer)
RUN uv sync --no-dev --no-install-project

# Copy project source code
COPY . .

# Install the project itself
RUN uv sync --no-dev

# Expose port for Dagster (default 3000)
EXPOSE 3000

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Set entry point for Dagster
CMD ["dagster", "api", "grpc", "-h", "0.0.0.0", "-p", "3000", "-m", "orchestration"]
