# D056: single-container deployment (HF Spaces, Docker SDK) -- builds the
# frontend, then serves it + the FastAPI backend from one process on one
# port. See decisions.md D056 for why (checkpoints not in git, fetched from
# a HF Hub model repo at container startup instead -- see backend/app/main.py).

FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY ml/ ./ml/
COPY geospatial/ ./geospatial/
COPY configs/ ./configs/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# HF Spaces (Docker SDK) expects the app on port 7860 and reads
# GEOSR4_CHECKPOINTS_REPO from the Space's own secrets/variables, not from
# here -- never bake a repo id or token into the image itself.
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
