# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend-build

WORKDIR /src/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM ghcr.io/linuxserver/unrar:latest AS unrar


FROM alpine:3.23

ARG BUILD_DATE
ARG VERSION=custom

LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.title="bazarr-custom"

ENV TZ="Etc/UTC" \
    BAZARR_VERSION="${VERSION}" \
    SZ_USER_AGENT="bazarr-custom" \
    PYTHONPATH="/app/bazarr/custom_libs:/app/bazarr/libs:/app/bazarr/bazarr:/app/bazarr" \
    VIRTUAL_ENV="/opt/venv" \
    PATH="/opt/venv/bin:${PATH}"

RUN \
    apk add --no-cache --virtual=.build-deps \
        build-base \
        cargo \
        libffi-dev \
        libpq-dev \
        libxml2-dev \
        libxslt-dev \
        python3-dev && \
    apk add --no-cache \
        bash \
        ffmpeg \
        git \
        libpq \
        libxml2 \
        libxslt \
        mediainfo \
        p7zip \
        python3 \
        tzdata && \
    python3 -m venv /opt/venv

WORKDIR /app/bazarr

COPY requirements.txt postgres-requirements.txt ./

RUN \
    pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir \
        --find-links https://wheel-index.linuxserver.io/alpine-3.23/ \
        -r requirements.txt \
        -r postgres-requirements.txt && \
    apk del .build-deps && \
    rm -rf /root/.cache /tmp/*

COPY bazarr.py ./
COPY bazarr ./bazarr
COPY custom_libs ./custom_libs
COPY libs ./libs
COPY migrations ./migrations
COPY --from=frontend-build /src/frontend/build ./frontend/build
COPY --from=unrar /usr/bin/unrar-alpine /usr/bin/unrar

EXPOSE 6767
VOLUME ["/config"]

CMD ["python3", "bazarr.py", "--no-update", "--config", "/config"]
