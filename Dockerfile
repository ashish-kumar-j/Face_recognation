FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app

ARG INSTALL_INSIGHTFACE=false
RUN python -m pip install --upgrade pip && \
    if [ "$INSTALL_INSIGHTFACE" = "true" ]; then \
      python -m pip install '.[insightface]'; \
    else \
      python -m pip install .; \
    fi

RUN mkdir -p /app/data/samples /app/data/snapshots

EXPOSE 8000

ENV FACE_APP_DATABASE_URL=sqlite:////app/data/face_app.db

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
