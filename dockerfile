# Multi-stage build: First build React frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app
COPY frontend/ .
RUN npm install
RUN npm run build

# Final stage: Python backend with integrated frontend
FROM python:3.11-slim

# Install system dependencies (Ghostscript is critical!)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ghostscript \
    gcc \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy frontend build from previous stage
COPY --from=frontend-builder /app/build ./frontend_build

# Security: Create non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port for Render
EXPOSE 8000

# Health check for Render
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]