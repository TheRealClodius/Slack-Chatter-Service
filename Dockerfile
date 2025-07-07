FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements
COPY pyproject.toml uv.lock ./

# Install uv and dependencies
RUN pip install uv
RUN uv sync --frozen

# Copy application code
COPY . .

# Install the package
RUN uv pip install -e .

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Default command runs ingestion worker
CMD ["python", "main_orchestrator.py", "ingestion"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import asyncio; from lib.config import config; print('Health check passed')" 