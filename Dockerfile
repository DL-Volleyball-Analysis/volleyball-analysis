# Web app images: `app` (API and worker, one image) and `web` (the built review UI behind nginx).
# docker compose up --build   (docker-compose.yml); model weights are mounted from ./models, never baked in.

FROM node:22-slim AS frontend
WORKDIR /app
COPY webapp/frontend/package.json webapp/frontend/package-lock.json ./
RUN npm ci
COPY webapp/frontend/ ./
RUN npm run build

FROM python:3.14-slim AS app
# ffmpeg: H.264 for rendered videos; libgl/libglib: OpenCV; git: the upstream ball tracker; tesseract: score bugs
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 git tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements/lock.txt requirements/lock.txt
RUN pip install --no-cache-dir -r requirements/lock.txt
# YOLO models (the ml extra); CPU PyTorch keeps the image a few GB smaller than the default CUDA build
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu ultralytics tqdm
# VballNet inference runs from its own repository (MIT), pinned to the commit the results were measured with
RUN git clone https://github.com/asigatchov/fast-volleyball-tracking-inference external/fast-volleyball-tracking-inference \
    && git -C external/fast-volleyball-tracking-inference checkout --quiet 3aad1b98b5b744afb0100418e95892a5b0c23865
COPY pyproject.toml README.md ./
COPY src src
COPY webapp/backend webapp/backend
RUN pip install --no-cache-dir --no-deps -e . -e webapp/backend
ENV VBALL_WEBAPP_DATA=/data VBALL_CORS_ORIGINS=http://localhost:8080
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "vball_app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM nginx:1.27-alpine AS web
COPY --from=frontend /app/dist /usr/share/nginx/html
COPY webapp/deploy/nginx.conf /etc/nginx/conf.d/default.conf
