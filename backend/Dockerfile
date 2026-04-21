FROM python:3.12-slim

# --- Environment variables ---
ENV PATH="/scripts:${PATH}:/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# --- Install dependencies ---
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    build-essential \
    gosu \
    cmake \
    v4l-utils \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1 \
    libglib2.0-0 \
    git \
    uwsgi \
    && rm -rf /var/lib/apt/lists/*

# --- Install Python dependencies ---
COPY ./app/requirements.txt /requirements.txt

RUN pip install --upgrade pip && pip install -r /requirements.txt

# --- Create video group + non-root user dynamically ---
ARG VIDEO_GID
RUN if getent group video >/dev/null 2>&1; then \
        groupmod -g ${VIDEO_GID:-44} video; \
    else \
        groupadd -g ${VIDEO_GID:-44} video; \
    fi && \
    useradd -m -U -G video -s /bin/bash user

# --- Create app directories ---
RUN mkdir -p /vol/static /vol/media /var/log/uwsgi && \
    chown -R user:user /vol/static /vol/media /var/log/uwsgi && \
    chmod -R 775 /vol/static /vol/media && \
    chmod -R 777 /var/log/uwsgi

# --- Copy app code and scripts into the image ---
COPY ./app /app
COPY ./scripts/scripts.sh /scripts/scripts.sh
RUN chmod +x /scripts/scripts.sh && chown -R user:user /app /scripts

# --- Working directory ---
WORKDIR /app

# --- Expose Django port ---
EXPOSE 8000

# --- Default command (optional if you use docker-compose command override) ---
CMD ["/scripts/scripts.sh"]
