# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set labels for better identification
LABEL org.opencontainers.image.source="https://github.com/yourusername/hsk-bot"
LABEL org.opencontainers.image.description="HSK Vocabulary Learning Telegram Bot"
LABEL org.opencontainers.image.version="1.0.0"

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create directory for resources
RUN mkdir -p /app/resources

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY resources/*.csv /app/resources/

# Install Python dependencies
RUN pip install --no-cache-dir .

# Command to run the bot
CMD ["python", "-m", "hsk_bot"]
