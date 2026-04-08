FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/
COPY db/ ./db/
COPY scripts/ ./scripts/
COPY requirements.txt .

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
