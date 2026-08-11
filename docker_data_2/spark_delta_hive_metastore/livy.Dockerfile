# Stage 1: Build
FROM debian:bullseye-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy zip file
COPY downloads/apache-livy-0.8.0-incubating_2.12-bin.zip /tmp/livy.zip

# Extract Livy
RUN mkdir -p /opt/livy && \
    unzip /tmp/livy.zip -d /opt && \
    mv /opt/apache-livy-0.8.0-incubating_2.12-bin/* /opt/livy/ && \
    rm -rf /opt/apache-livy-0.8.0-incubating_2.12-bin /tmp/livy.zip

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
