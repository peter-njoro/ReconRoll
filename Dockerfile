# syntax=docker/dockerfile:1

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    liblibglib2.0-0 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create and set the working directory
WORKDIR /app

# Copy the requirements file and install Python dependencies
COPY ./requirements.txt /requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /requirements.txt

# Copy the application code
COPY ./app /app
RUN cmod +x ./scripts/scripts.sh

#port 
EXPOSE 8000

# Default command
CMD ["sh", "./scripts/scripts.sh"]