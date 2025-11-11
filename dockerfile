# === Stage 1: Build React frontend ===
FROM node:18 AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# === Stage 2: Build FastAPI backend ===
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies (Ghostscript for compression)
RUN apt-get update && apt-get install -y ghostscript && rm -rf /var/lib/apt/lists/*

# Copy backend files
COPY backend/ ./backend/
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy built React frontend into a directory served by FastAPI
COPY --from=frontend-builder /app/frontend/build ./frontend_build

# Copy backend entrypoint
COPY backend/main.py ./main.py

# Expose port for Render
EXPOSE 8000

# Start FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
