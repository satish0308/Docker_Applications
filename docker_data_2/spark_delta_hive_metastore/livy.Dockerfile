# Stage 1: Build
FROM debian:bullseye-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Copy tarball
COPY downloads/apache-livy-0.8.0-incubating-bin.tar.gz /tmp/livy.tgz

# Extract Livy
RUN mkdir -p /opt/livy && \
    tar -xf /tmp/livy.tgz -C /opt/livy --strip-components=1 && \
    rm /tmp/livy.tgz

# Stage 2: Runtime
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-11-jre-headless \
    && rm -rf /var/lib/apt/lists/*

ENV LIVY_HOME=/opt/livy
ENV PATH=$LIVY_HOME/bin:$PATH

# Copy from builder
COPY --from=builder /opt/livy /opt/livy

EXPOSE 8998

ENTRYPOINT ["/opt/livy/bin/livy-server"]
