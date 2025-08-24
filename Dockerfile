FROM python:3.12-slim

# Set environment variables
ENV PATH="scripts:${PATH}:/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    build-essential \
    gosu \
    sudo \
    cmake \
    v4l-utils \
    ffmpeg \
    libsm6 \
    libxext6 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1 \
    libglib2.0-0 \
    git \
    uwsgi \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /requirements.txt
# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r /requirements.txt

# Create user with sudo privileges (for initial setup only)
RUN adduser --disabled-password --gecos '' user && \
    echo 'user ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/user && \
    chmod 0440 /etc/sudoers.d/user 

# Create directories with correct ownership
RUN mkdir -p /vol/static /vol/media /var/log/uwsgi && \
    chown -R user:user /vol/static /vol/media /var/log/uwsgi && \
    chmod -R 775 /vol/static /vol/media && \
    chmod -R 777 /var/log/uwsgi

# copy application files
COPY ./scripts/scripts.sh /scripts/scripts.sh
RUN chmod +x /scripts/scripts.sh

WORKDIR /app


# start as root (scripts.sh will switch to user)
CMD ["scripts.sh"]
