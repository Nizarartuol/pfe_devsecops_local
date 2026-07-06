# checkov:skip=CKV_DOCKER_2: Kubernetes manages health probes natively
# Copyright 2021 Google LLC
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

# https://mcr.microsoft.com/product/dotnet/sdk
FROM --platform=$BUILDPLATFORM mcr.microsoft.com/dotnet/sdk:10.0.100-noble@sha256:c7445f141c04f1a6b454181bd098dcfa606c61ba0bd213d0a702489e5bd4cd71 AS builder
ARG TARGETARCH
WORKDIR /app
COPY cartservice.csproj .
RUN dotnet restore cartservice.csproj \
    -a $TARGETARCH
COPY . .
RUN dotnet publish cartservice.csproj \
    -p:PublishSingleFile=true \
    -a $TARGETARCH \
    --self-contained true \
    -p:PublishTrimmed=true \
    -p:TrimMode=full \
    -c release \
    -o /cartservice

# https://mcr.microsoft.com/product/dotnet/runtime-deps
# Non-chiseled "noble" variant (instead of noble-chiseled) is used so the apt package
# index/upgrade below can run — chiseled images ship no shell or package manager, so
# OS-level CVE fixes (e.g. openssl/libssl3t64) could never be applied without re-pinning
# the base digest by hand every time.
FROM mcr.microsoft.com/dotnet/runtime-deps:10.0.0-noble@sha256:69ee6d1a1b7a92cc82a71001342554d4611a509d880114b2d5653ff5e73eb436

# CACHE_BUST forces this layer to re-run even when the Dockerfile is unchanged, so the
# apt package index is re-fetched instead of reusing a stale build cache with old fixes.
ARG CACHE_BUST=unset
RUN echo "cache-bust: ${CACHE_BUST}" \
    && apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /cartservice .
EXPOSE 7070
ENV DOTNET_EnableDiagnostics=0 \
    ASPNETCORE_HTTP_PORTS=7070
USER 1000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:7070/ || exit 1

ENTRYPOINT ["/app/cartservice"]

