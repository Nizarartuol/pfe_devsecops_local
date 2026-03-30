# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM --platform=$BUILDPLATFORM python:3.14.2-alpine@sha256:31da4cb527055e4e3d7e9e006dffe9329f84ebea79eaca0a1f1c27ce61e40ca5 AS base

RUN apk upgrade --no-cache libpng

FROM base AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apk update \
    && apk add --no-cache g++ linux-headers \
    && rm -rf /var/cache/apk/*

COPY requirements.txt .

RUN pip install --prefix="/install" -r requirements.txt

FROM base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apk update \
    && apk add --no-cache libstdc++ \
    && rm -rf /var/cache/apk/*

# Create non-root user
RUN addgroup -g 1000 appuser && \
    adduser -u 1000 -G appuser -s /bin/sh -D appuser

WORKDIR /loadgen

COPY --from=builder /install /usr/local

# Add application code.
COPY locustfile.py .

# Change ownership to non-root user
RUN chown -R appuser:appuser /loadgen

# enable gevent support in debugger
ENV GEVENT_SUPPORT=True

# Set protocol to HTTPS by default for security (can be overridden to http for local dev)
ENV PROTOCOL=https

# Run as non-root user
USER 1000

ENTRYPOINT locust --host="${PROTOCOL}://${FRONTEND_ADDR}" --headless -u "${USERS:-10}" -r "${RATE:-1}" 2>&1
