# Relocation Investment Explorer - single-container image.
# Stage 1 builds the React frontend; stage 2 serves API + static bundle
# from FastAPI on $PORT (Render/Fly/HF Spaces/Cloud Run all inject PORT).

FROM node:22-slim AS frontend
WORKDIR /build
COPY app/frontend/package.json app/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY app/frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /srv/app
COPY app/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app/backend/ ./
COPY --from=frontend /build/dist /srv/frontend/dist

# Writable state (SQLite DBs, manual/live listings). Mount a volume here on
# platforms that have one (Fly volumes, HF persistent storage); on Render
# free it is ephemeral and resets on redeploy - see DEPLOY.md.
ENV DATA_DIR=/data
RUN mkdir -p /data

EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
