FROM python:3.6-slim

ENV PYTHONUNBUFFERED 1

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY requirements-dev.txt /app/requirements-dev.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      libxmlsec1-dev \
      libxml2-dev \
      pkg-config \
      gettext \
      git \
      build-essential \
    && pip install -U pip \
    && pip install --no-cache-dir  -r /app/requirements.txt \
    && pip install --no-cache-dir  -r /app/requirements-dev.txt \
    && pip install --no-cache-dir prequ \
    && apt-get remove -y build-essential pkg-config git \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/archives

COPY . /app
