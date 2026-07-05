# checkov:skip=CKV_DOCKER_2: Kubernetes manages health probes natively
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

FROM --platform=$BUILDPLATFORM eclipse-temurin:24.0.2_12-jdk-noble@sha256:dacac8e9a0df0d2bd24e702b4431132875c249930b70555ebd7ca285b5bee684 AS builder

WORKDIR /app

COPY ["build.gradle", "gradlew", "./"]
COPY gradle gradle
RUN chmod +x gradlew
RUN ./gradlew downloadRepos

COPY . .
RUN chmod +x gradlew
RUN ./gradlew installDist

FROM eclipse-temurin:25.0.1_8-jre-alpine@sha256:9c65fe190cb22ba92f50b8d29a749d0f1cfb2437e09fe5fbf9ff927c45fc6e99

# CACHE_BUST forces this layer to re-run even when the Dockerfile is unchanged, so the
# Alpine package index is re-fetched instead of reusing a stale build cache with old fixes.
ARG CACHE_BUST=unset
RUN echo "cache-bust: ${CACHE_BUST}" \
    && apk update && apk upgrade --no-cache && apk add --no-cache curl


# Create non-root user
RUN addgroup -g 1000 appuser && \
    adduser -u 1000 -G appuser -s /bin/sh -D appuser

WORKDIR /app
COPY --from=builder /app .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

EXPOSE 9555

# Run as non-root user
USER 1000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:9555/ || exit 1

ENTRYPOINT ["/app/build/install/hipstershop/bin/AdService"]

