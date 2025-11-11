# 1️⃣ Stage 1: Build React frontend
FROM node:18 AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# 2️⃣ Stage 2: Build FastAPI backend
FROM python:3.11-slim AS backend
WORKDIR /app

# Install system deps (for Ghostscript)
RUN apt-get update && apt-get install -y ghostscript && rm -rf /var/lib/apt/lists/*

# Copy backend and install Python deps
COPY backend/ ./backend/
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r backend/requirements.txt

# 3️⃣ Copy built frontend into backend static folder
COPY --from=frontend-builder /app/frontend/build ./frontend_build

# 4️⃣ Create app entry script
COPY backend/main.py ./main.py

# 5️⃣ Expose port and run FastAPI
EXPOSE 8000

# Serve static React files via FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
